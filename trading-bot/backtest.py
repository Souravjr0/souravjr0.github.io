import os
import sys

# Dynamic path resolution to support restructured package layouts and nested submodules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) in ["core", "models", "execution", "discovery", "utils"] else current_dir
for subfolder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, subfolder))
sys.path.append(project_root)

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from exchange_client import get_spot_client
from config import (
    ATR_MULTIPLIER_SL,
    ATR_MULTIPLIER_TP,
    ATR_PERIOD,
    BACKTEST_BARS,
    BACKTEST_FEE_RATE,
    DEFAULT_QUOTE_AMOUNT,
)
from indicators import add_indicators
from market_data import fetch_klines, klines_to_dataframe
from strategies import add_strategy_signals


STRATEGY_MAP = {
    "ema_rsi": "signal_ema_rsi",
    "breakout": "signal_breakout",
    "mean_reversion": "signal_mean_rev",
}


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    side: str
    entry: float
    exit: float
    qty: float
    pnl: float
    reason: str


@dataclass
class BacktestResult:
    strategy: str
    trade_count: int
    total_pnl: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    expectancy: float
    trades: list[Trade]


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


def _atr_levels(close: float, atr: float, side: str) -> tuple[float, float]:
    if side == "LONG":
        return close - atr * ATR_MULTIPLIER_SL, close + atr * ATR_MULTIPLIER_TP
    return close + atr * ATR_MULTIPLIER_SL, close - atr * ATR_MULTIPLIER_TP


def _run_backtest(
    df: pd.DataFrame,
    signal_col: str,
    fee_rate: float,
    position_size: float,
) -> BacktestResult:
    trades: list[Trade] = []
    position = None
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for idx in range(1, len(df)):
        row = df.iloc[idx]
        signal = row.get(signal_col, 0)

        if position is None and signal in {1, -1}:
            atr = row.get("atr14")
            if pd.isna(atr) or atr == 0:
                continue
            side = "LONG" if signal == 1 else "SHORT"
            entry_price = float(row["close"])
            qty = position_size / entry_price
            stop, take = _atr_levels(entry_price, atr, side)
            position = {
                "side": side,
                "entry": entry_price,
                "qty": qty,
                "stop": stop,
                "take": take,
                "entry_time": row["open_time"],
            }
            continue

        if position is None:
            continue

        exit_price = None
        exit_reason = None
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])

        if position["side"] == "LONG":
            stop_hit = low <= position["stop"]
            take_hit = high >= position["take"]
            if stop_hit:
                exit_price = position["stop"]
                exit_reason = "stop"
            elif take_hit:
                exit_price = position["take"]
                exit_reason = "take"
            elif signal == -1:
                exit_price = close
                exit_reason = "signal"
        else:
            stop_hit = high >= position["stop"]
            take_hit = low <= position["take"]
            if stop_hit:
                exit_price = position["stop"]
                exit_reason = "stop"
            elif take_hit:
                exit_price = position["take"]
                exit_reason = "take"
            elif signal == 1:
                exit_price = close
                exit_reason = "signal"

        if exit_price is None:
            continue

        entry = position["entry"]
        qty = position["qty"]
        if position["side"] == "LONG":
            pnl = (exit_price - entry) * qty
        else:
            pnl = (entry - exit_price) * qty

        fees = fee_rate * position_size * 2
        pnl -= fees

        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

        trades.append(
            Trade(
                entry_time=position["entry_time"].strftime("%Y-%m-%d %H:%M"),
                exit_time=row["close_time"].strftime("%Y-%m-%d %H:%M"),
                side=position["side"],
                entry=entry,
                exit=exit_price,
                qty=qty,
                pnl=pnl,
                reason=exit_reason or "exit",
            )
        )
        position = None

    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [trade.pnl for trade in trades if trade.pnl <= 0]

    trade_count = len(trades)
    win_rate = (len(wins) / trade_count * 100) if trade_count else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses else float("inf")
    expectancy = (win_rate / 100) * avg_win + (1 - win_rate / 100) * avg_loss
    max_dd_pct = (max_drawdown / position_size * 100) if position_size else 0.0

    return BacktestResult(
        strategy=signal_col,
        trade_count=trade_count,
        total_pnl=sum(trade.pnl for trade in trades),
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_dd_pct,
        expectancy=expectancy,
        trades=trades,
    )


def _print_summary(label: str, result: BacktestResult) -> None:
    profit_factor = f"{result.profit_factor:.2f}" if result.profit_factor != float("inf") else "inf"
    _print_section(
        f"Backtest Summary: {label}",
        [
            "Trades",
            "Total PnL",
            "Win Rate",
            "Avg Win",
            "Avg Loss",
            "Profit Factor",
            "Max DD",
            "Max DD%",
            "Expectancy",
        ],
        [
            [
                str(result.trade_count),
                f"{result.total_pnl:.2f}",
                f"{result.win_rate:.2f}%",
                f"{result.avg_win:.2f}",
                f"{result.avg_loss:.2f}",
                profit_factor,
                f"{result.max_drawdown:.2f}",
                f"{result.max_drawdown_pct:.2f}%",
                f"{result.expectancy:.2f}",
            ]
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy backtester (Binance data)")
    parser.add_argument("--symbol", required=True, help="Symbol, e.g. BTCUSDT")
    parser.add_argument("--timeframe", default="1h", help="Kline interval (e.g., 15m,1h,4h,1d)")
    parser.add_argument(
        "--strategy",
        default="ema_rsi",
        choices=["ema_rsi", "breakout", "mean_reversion", "all"],
    )
    parser.add_argument("--bars", type=int, default=BACKTEST_BARS, help="Number of bars")
    parser.add_argument("--fee-rate", type=float, default=BACKTEST_FEE_RATE, help="Fee rate per side")
    parser.add_argument("--position-size", type=float, default=DEFAULT_QUOTE_AMOUNT, help="Quote amount")
    parser.add_argument("--show-trades", type=int, default=10, help="Show last N trades")
    args = parser.parse_args()

    client = get_spot_client()

    klines = fetch_klines(client, args.symbol.upper(), args.timeframe, args.bars)
    df = klines_to_dataframe(klines)
    if df.empty or len(df) < 50:
        print("Not enough data for backtest.")
        return

    df = add_indicators(df, atr_period=ATR_PERIOD)
    df = add_strategy_signals(df)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Backtest snapshot: {timestamp} | {args.symbol.upper()} | {args.timeframe}")

    strategies = STRATEGY_MAP if args.strategy == "all" else {args.strategy: STRATEGY_MAP[args.strategy]}

    for strategy_name, signal_col in strategies.items():
        result = _run_backtest(
            df=df,
            signal_col=signal_col,
            fee_rate=args.fee_rate,
            position_size=args.position_size,
        )
        _print_summary(strategy_name, result)
        if result.trades:
            trades = result.trades[-args.show_trades :]
            rows = [
                [
                    trade.entry_time,
                    trade.exit_time,
                    trade.side,
                    f"{trade.entry:.4f}",
                    f"{trade.exit:.4f}",
                    f"{trade.qty:.6f}",
                    f"{trade.pnl:.2f}",
                    trade.reason,
                ]
                for trade in trades
            ]
            _print_section(
                f"Last {len(trades)} Trades ({strategy_name})",
                ["Entry", "Exit", "Side", "EntryPx", "ExitPx", "Qty", "PnL", "Reason"],
                rows,
            )


if __name__ == "__main__":
    main()
