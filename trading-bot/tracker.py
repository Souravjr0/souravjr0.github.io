import argparse
from datetime import datetime, timezone

import pandas as pd
import requests

from external_frameworks import get_framework_statuses
from exchange_client import get_spot_client
from config import (
    ATR_MULTIPLIER_SL,
    ATR_MULTIPLIER_TP,
    ATR_PERIOD,
    QUOTE_ASSET,
    TRACKER_BARS,
    TRACKER_TIMEFRAMES,
    TRACKER_TOP_N,
    WATCHLIST,
)
from indicators import add_indicators
from market_data import fetch_klines, klines_to_dataframe
from strategies import evaluate_latest_signals


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_value(value: float | None, precision: int = 4) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.{precision}f}"


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    lines = [
        "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)),
        "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))))
    return "\n".join(lines)


def _print_section(title: str, headers: list[str], rows: list[list[str]]) -> None:
    print(f"\n{title}")
    print(_format_table(headers, rows))


def _print_framework_statuses() -> None:
    statuses = get_framework_statuses()
    rows: list[list[str]] = []
    for status in statuses:
        if status["path_exists"] and status["entry_exists"]:
            state = "READY"
        elif status["path_exists"]:
            state = "MISSING_ENTRYPOINT"
        else:
            state = "MISSING_PATH"
        rows.append([status["name"], state, status["entrypoint"] or "-"])
    _print_section("External Frameworks", ["Framework", "Status", "Entrypoint"], rows)


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _parse_timeframes(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def analyze_market_symbols(
    watchlist: list[str] | None = None,
    timeframes: list[str] | None = None,
    bars: int = TRACKER_BARS,
) -> dict[str, dict]:
    watchlist = watchlist or WATCHLIST
    timeframes = timeframes or TRACKER_TIMEFRAMES

    client = get_spot_client()

    results: dict[str, dict] = {}

    for symbol in watchlist:
        symbol_data: dict[str, dict] = {"signals": {}}
        current_price: float | None = None
        best_pick: dict[str, object] | None = None

        for idx, timeframe in enumerate(timeframes):
            try:
                klines = fetch_klines(client, symbol, timeframe, bars)
            except requests.RequestException:
                continue

            df = klines_to_dataframe(klines)
            if df.empty or len(df) < 50:
                continue

            df = add_indicators(df, atr_period=ATR_PERIOD)
            summary = evaluate_latest_signals(df, ATR_MULTIPLIER_SL, ATR_MULTIPLIER_TP)
            last = df.iloc[-1]

            if current_price is None and not pd.isna(last.get("close")):
                current_price = float(last["close"])

            long_count = sum(1 for value in summary.per_strategy.values() if value == "LONG")
            short_count = sum(1 for value in summary.per_strategy.values() if value == "SHORT")
            strength = (long_count - short_count) / 3
            vote_count = max(long_count, short_count)
            action = "BUY" if long_count > short_count else "SELL" if short_count > long_count else "WAIT"
            action_source = "CONSENSUS" if summary.direction in {"LONG", "SHORT"} else "MAJORITY"
            stop = summary.stop
            take = summary.take
            atr = last.get("atr14")
            if action != "WAIT" and (stop is None or take is None) and not pd.isna(atr):
                if action == "BUY":
                    stop = float(last["close"]) - float(atr) * ATR_MULTIPLIER_SL
                    take = float(last["close"]) + float(atr) * ATR_MULTIPLIER_TP
                elif action == "SELL":
                    stop = float(last["close"]) + float(atr) * ATR_MULTIPLIER_SL
                    take = float(last["close"]) - float(atr) * ATR_MULTIPLIER_TP
            symbol_data["signals"][timeframe] = {
                "signal": summary.direction,
                "score": summary.score,
                "action": action,
                "action_source": action_source,
                "long_count": long_count,
                "short_count": short_count,
                "strength": strength,
                "stop": stop,
                "take": take,
                "per_strategy": summary.per_strategy,
            }

            candidate = {
                "idx": idx,
                "timeframe": timeframe,
                "summary": summary,
                "action": action,
                "strength": strength,
                "vote_count": vote_count,
                "entry": float(last["close"]),
            }
            if best_pick is None:
                best_pick = candidate
            else:
                best_strength = abs(float(best_pick["strength"]))
                cand_strength = abs(strength)
                best_votes = int(best_pick["vote_count"])
                if cand_strength > best_strength:
                    best_pick = candidate
                elif cand_strength == best_strength and vote_count > best_votes:
                    best_pick = candidate
                elif cand_strength == best_strength and vote_count == best_votes:
                    if idx < int(best_pick["idx"]):
                        best_pick = candidate

        if symbol_data["signals"]:
            symbol_data["current_price"] = current_price if current_price is not None else "n/a"
            if best_pick is not None:
                summary = best_pick["summary"]
                per_strategy = summary.per_strategy
                latest_signals = {
                    key: ("BUY" if value == "LONG" else "SELL" if value == "SHORT" else "HOLD")
                    for key, value in per_strategy.items()
                }
                symbol_data["latest_signals"] = latest_signals
                symbol_data["signal_strength"] = float(best_pick["strength"])
                symbol_data["action"] = best_pick["action"]
                symbol_data["action_source"] = symbol_data["signals"][best_pick["timeframe"]]["action_source"]
                symbol_data["signal_score"] = summary.score
                symbol_data["signal_timeframe"] = best_pick["timeframe"]
                symbol_data["stop"] = symbol_data["signals"][best_pick["timeframe"]]["stop"]
                symbol_data["take"] = symbol_data["signals"][best_pick["timeframe"]]["take"]
                symbol_data["entry"] = best_pick["entry"]
            results[symbol] = symbol_data

    return results


def _track_market(args: argparse.Namespace) -> None:
    watchlist = _parse_symbols(args.watchlist)
    timeframes = _parse_timeframes(args.timeframes)

    client = get_spot_client()

    tickers = [
        ticker
        for ticker in client.get_ticker_24h()
        if ticker.get("symbol", "").endswith(QUOTE_ASSET)
    ]
    if not tickers:
        print("No tickers returned from Binance.")
        return

    top_n = max(args.top, 1)
    gainers = sorted(
        tickers,
        key=lambda t: _to_float(t.get("priceChangePercent")),
        reverse=True,
    )[:top_n]
    losers = sorted(
        tickers,
        key=lambda t: _to_float(t.get("priceChangePercent")),
    )[:top_n]
    volume_leaders = sorted(
        tickers,
        key=lambda t: _to_float(t.get("quoteVolume")),
        reverse=True,
    )[:top_n]
    volatility = sorted(
        tickers,
        key=lambda t: _to_float(t.get("highPrice")) - _to_float(t.get("lowPrice")),
        reverse=True,
    )[:top_n]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Snapshot: {timestamp} | Quote asset: {QUOTE_ASSET}")

    _print_section(
        "Top Gainers (24h)",
        ["Symbol", "Change%", "Last", "Quote Vol"],
        [
            [
                t["symbol"],
                f"{_to_float(t.get('priceChangePercent')):.2f}",
                f"{_to_float(t.get('lastPrice')):.6f}",
                f"{_to_float(t.get('quoteVolume')):.0f}",
            ]
            for t in gainers
        ],
    )
    _print_section(
        "Top Losers (24h)",
        ["Symbol", "Change%", "Last", "Quote Vol"],
        [
            [
                t["symbol"],
                f"{_to_float(t.get('priceChangePercent')):.2f}",
                f"{_to_float(t.get('lastPrice')):.6f}",
                f"{_to_float(t.get('quoteVolume')):.0f}",
            ]
            for t in losers
        ],
    )
    _print_section(
        "Volume Leaders (24h)",
        ["Symbol", "Quote Vol", "Change%", "Last"],
        [
            [
                t["symbol"],
                f"{_to_float(t.get('quoteVolume')):.0f}",
                f"{_to_float(t.get('priceChangePercent')):.2f}",
                f"{_to_float(t.get('lastPrice')):.6f}",
            ]
            for t in volume_leaders
        ],
    )
    volatility_rows = []
    for ticker in volatility:
        last_price = _to_float(ticker.get("lastPrice"))
        range_pct = (
            ((_to_float(ticker.get("highPrice")) - _to_float(ticker.get("lowPrice"))) / last_price * 100)
            if last_price
            else 0
        )
        volatility_rows.append(
            [
                ticker["symbol"],
                f"{range_pct:.2f}",
                f"{_to_float(ticker.get('priceChangePercent')):.2f}",
                f"{last_price:.6f}",
            ]
        )
    _print_section(
        "Volatility Leaders (24h)",
        ["Symbol", "High-Low%", "Change%", "Last"],
        volatility_rows,
    )

    action_counts: dict[str, dict[str, int]] = {
        symbol: {"buy": 0, "sell": 0} for symbol in watchlist
    }
    last_prices: dict[str, float] = {}

    for timeframe in timeframes:
        rows: list[list[str]] = []
        detail_rows: list[list[str]] = []
        for symbol in watchlist:
            try:
                klines = fetch_klines(client, symbol, timeframe, args.bars)
            except requests.RequestException as exc:
                print(f"Request error for {symbol} ({timeframe}): {exc}")
                continue

            df = klines_to_dataframe(klines)
            if df.empty or len(df) < 50:
                continue
            df = add_indicators(df, atr_period=ATR_PERIOD)

            summary = evaluate_latest_signals(df, ATR_MULTIPLIER_SL, ATR_MULTIPLIER_TP)
            last = df.iloc[-1]
            trend = "n/a"
            if not pd.isna(last.get("ema_20")) and not pd.isna(last.get("ema_50")):
                trend = "UP" if last["ema_20"] > last["ema_50"] else "DOWN"
            action = "BUY" if summary.direction == "LONG" else "SELL" if summary.direction == "SHORT" else "WAIT"
            if action == "BUY":
                action_counts[symbol]["buy"] += 1
            elif action == "SELL":
                action_counts[symbol]["sell"] += 1
            if symbol not in last_prices and not pd.isna(last.get("close")):
                last_prices[symbol] = float(last["close"])

            rows.append(
                [
                    symbol,
                    timeframe,
                    f"{last['close']:.6f}",
                    trend,
                    _format_value(last.get("rsi14"), 2),
                    _format_value(last.get("macd_hist"), 4),
                    _format_value(last.get("atr14"), 4),
                    _format_value(last.get("volatility"), 2),
                    f"{action} ({summary.direction} {summary.score})",
                    _format_value(summary.stop, 6),
                    _format_value(summary.take, 6),
                ]
            )

            if args.detailed:
                detail_rows.append(
                    [
                        symbol,
                        timeframe,
                        summary.per_strategy.get("EMA_RSI", "n/a"),
                        summary.per_strategy.get("BREAKOUT", "n/a"),
                        summary.per_strategy.get("MEAN_REV", "n/a"),
                    ]
                )

        if rows:
            _print_section(
                f"Watchlist Signals ({timeframe})",
                ["Symbol", "TF", "Last", "Trend", "RSI", "MACD", "ATR", "Vol%", "Signal", "Stop", "Take"],
                rows,
            )
        if args.detailed and detail_rows:
            _print_section(
                f"Strategy Breakdown ({timeframe})",
                ["Symbol", "TF", "EMA+RSI", "Breakout", "MeanRev"],
                detail_rows,
            )

    buy_rows: list[list[str]] = []
    sell_rows: list[list[str]] = []
    wait_rows: list[list[str]] = []

    for symbol in watchlist:
        counts = action_counts.get(symbol, {"buy": 0, "sell": 0})
        buy_count = counts["buy"]
        sell_count = counts["sell"]
        if buy_count + sell_count == 0:
            continue
        price = _format_value(last_prices.get(symbol), 6)
        row = [symbol, price, str(buy_count), str(sell_count)]

        if buy_count > sell_count:
            buy_rows.append(row)
        elif sell_count > buy_count:
            sell_rows.append(row)
        else:
            wait_rows.append(row)

    buy_rows.sort(key=lambda r: (int(r[2]) - int(r[3]), r[0]), reverse=True)
    sell_rows.sort(key=lambda r: (int(r[3]) - int(r[2]), r[0]), reverse=True)
    wait_rows.sort(key=lambda r: r[0])

    if buy_rows:
        _print_section("Quick Buy List", ["Symbol", "Last", "BUY", "SELL"], buy_rows)
    else:
        print("\nQuick Buy List\nNone")

    if sell_rows:
        _print_section("Quick Sell List", ["Symbol", "Last", "BUY", "SELL"], sell_rows)
    else:
        print("\nQuick Sell List\nNone")

    if wait_rows:
        _print_section("Quick Wait List", ["Symbol", "Last", "BUY", "SELL"], wait_rows)

    _print_framework_statuses()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto market tracker")
    parser.add_argument("--top", type=int, default=TRACKER_TOP_N, help="Top N movers")
    parser.add_argument(
        "--watchlist",
        type=str,
        default=",".join(WATCHLIST),
        help="Comma-separated symbols",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default=",".join(TRACKER_TIMEFRAMES),
        help="Comma-separated timeframes (e.g., 15m,1h,4h,1d)",
    )
    parser.add_argument("--bars", type=int, default=TRACKER_BARS, help="Bars per timeframe")
    parser.add_argument("--detailed", action="store_true", help="Show per-strategy signals")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full unified analysis (tracker + backtest + portfolio + frameworks)"
    )

    args = parser.parse_args()
    
    if args.full:
        import subprocess
        import sys
        
        # Split watchlist into crypto, stocks, and forex to invoke unified_analyzer.py properly
        try:
            from unified_analyzer import is_stock
        except ImportError:
            def is_stock(symbol: str) -> bool:
                symbol_upper = symbol.strip().upper()
                if symbol_upper.endswith("USDT") or symbol_upper.endswith("BTC") or symbol_upper.endswith("ETH"):
                    return False
                return True
                
        watchlist_symbols = [s.strip().upper() for s in args.watchlist.split(",") if s.strip()]
        crypto_list = []
        stock_list = []
        forex_list = []
        
        forex_currencies = {
            "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", 
            "SGD", "HKD", "CNY", "INR", "MXN", "ZAR", "SEK", "NOK", 
            "TRY", "RUB", "BRL", "TWD", "KRW"
        }
        
        for s in watchlist_symbols:
            if len(s) == 6 and s[:3] in forex_currencies and s[3:] in forex_currencies:
                forex_list.append(s)
            elif is_stock(s):
                stock_list.append(s)
            else:
                crypto_list.append(s)
                
        cmd = [sys.executable, "unified_analyzer.py"]
        if crypto_list:
            cmd += ["--crypto", ",".join(crypto_list)]
        if stock_list:
            cmd += ["--stocks", ",".join(stock_list)]
        if forex_list:
            cmd += ["--forex", ",".join(forex_list)]
            
        subprocess.run(cmd, check=False)
    else:
        _track_market(args)


if __name__ == "__main__":
    main()
