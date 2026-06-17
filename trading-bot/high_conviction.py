import time
from typing import Optional

import pandas as pd

from market_data import fetch_klines, klines_to_dataframe
from indicators import add_indicators
from advanced_skills import _vwap, _supertrend, market_regime


class HCConfig:
    TIMEFRAME = "15m"
    FAST_EMA = 9
    SLOW_EMA = 21
    RSI_PERIOD = 14
    MIN_RSI_OVERSOLD = 30
    MAX_RSI_OVERBOUGHT = 70
    MIN_EMA_GAP_PCT = 2.0
    RISK_PER_TRADE_PCT = 1.0
    SL_PCT = 2.0
    TP_PCT = 5.0
    INITIAL_CASH = 10000.0


def add_hc_indicators(df: pd.DataFrame, cfg: HCConfig = HCConfig()) -> pd.DataFrame:
    if df.empty:
        return df
    close = df["close"]
    df["ema_fast"] = close.ewm(span=cfg.FAST_EMA, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=cfg.SLOW_EMA, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=cfg.RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(span=cfg.RSI_PERIOD, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["ema_gap_pct"] = (df["ema_fast"] - df["ema_slow"]) / df["ema_slow"] * 100
    df["momentum_strong"] = df["ema_gap_pct"].abs() > cfg.MIN_EMA_GAP_PCT
    df["trend_slope"] = df["close"] - df["close"].shift(5)

    # Inject premium skills metrics
    try:
        df["vwap"] = _vwap(df)
    except Exception:
        df["vwap"] = df["close"]

    try:
        df["supertrend"] = _supertrend(df)
    except Exception:
        df["supertrend"] = 0

    return df


def is_bold_buy(df: pd.DataFrame, cfg: HCConfig = HCConfig()) -> bool:
    if df.empty or len(df) < 5:
        return False
    latest = df.iloc[-1]
    conditions = [
        latest["ema_fast"] > latest["ema_slow"],          # Bullish trend alignment
        latest["close"] > latest["vwap"],                # Trading above VWAP volume anchor
        latest["supertrend"] == 1,                        # Supertrend buy trigger
        latest["rsi"] > 45 and latest["rsi"] < 70,        # Bullish momentum breakout (not overbought)
        latest["trend_slope"] > 0,                        # Upward price velocity
    ]
    # Requires at least 4 out of 5 indicators to agree for a premium high-conviction signal
    return sum(1 for c in conditions if c) >= 4


def is_bold_sell(df: pd.DataFrame, cfg: HCConfig = HCConfig()) -> bool:
    if df.empty or len(df) < 5:
        return False
    latest = df.iloc[-1]
    conditions = [
        latest["ema_fast"] < latest["ema_slow"],          # Bearish trend alignment
        latest["close"] < latest["vwap"],                # Trading below VWAP volume anchor
        latest["supertrend"] == -1,                       # Supertrend sell trigger
        latest["rsi"] < 55 and latest["rsi"] > 30,        # Bearish breakdown momentum (not oversold yet)
        latest["trend_slope"] < 0,                        # Downward price velocity
    ]
    # Requires at least 4 out of 5 indicators to agree for a premium high-conviction exit
    return sum(1 for c in conditions if c) >= 4


class SimplePortfolio:
    def __init__(self, cash: float):
        self.cash = cash
        self.position = 0
        self.buy_price = 0.0
        self.history: list[float] = []

    def update_value(self, price: float) -> float:
        value = self.cash + self.position * price
        self.history.append(value)
        return value

    def compute_position_size(self, price: float, equity: float, risk_pct: float, sl_pct: float) -> int:
        risk_usd = equity * risk_pct / 100.0
        sl_price = price * (1 - sl_pct / 100)
        sl_distance = price - sl_price
        if sl_distance <= 0:
            return 0
        qty = int(risk_usd / sl_distance)
        return max(0, qty)

    def enter_long(self, price: float, qty: int, sl_pct: float, tp_pct: float):
        cost = qty * price
        if cost > self.cash or qty <= 0:
            return None
        self.cash -= cost
        self.position += qty
        self.buy_price = price
        sl = price * (1 - sl_pct / 100)
        tp = price * (1 + tp_pct / 100)
        return {"type": "long", "qty": qty, "price": price, "sl": sl, "tp": tp}

    def exit_position(self, price: float):
        if self.position == 0:
            return None
        revenue = self.position * price
        profit = revenue - self.position * self.buy_price
        self.cash += revenue
        self.position = 0
        self.buy_price = 0.0
        return {"type": "exit", "price": price, "profit": profit}


def run_demo(symbol: str = "BTCUSDT", bars: int = 500, cfg: HCConfig = HCConfig()) -> None:
    client = None
    try:
        # reuse exchange client function lazily to avoid circular imports
        from exchange_client import get_spot_client

        client = get_spot_client()
    except Exception:
        client = None

    if client is None:
        print("No exchange client available; demo requires the exchange client to fetch data.")
        return

    klines = fetch_klines(client, symbol, cfg.TIMEFRAME, bars)
    df = klines_to_dataframe(klines)
    if df.empty or len(df) < 50:
        print("Not enough data for demo")
        return

    df = add_hc_indicators(df, cfg)

    portfolio = SimplePortfolio(cfg.INITIAL_CASH)
    in_trade = False
    current_trade: Optional[dict] = None

    print(f"Running high‑conviction demo on {symbol} ({cfg.TIMEFRAME}) — bars={len(df)}")

    for i in range(50, len(df)):
        window = df.iloc[: i + 1].copy()
        latest_price = float(window.iloc[-1]["close"])
        equity = portfolio.update_value(latest_price)

        # manage open trade
        if in_trade and current_trade:
            if latest_price <= current_trade["sl"]:
                portfolio.exit_position(latest_price)
                print(f"⛔ STOP‑LOSS hit at {latest_price:.4f}")
                in_trade = False
                current_trade = None
            elif latest_price >= current_trade["tp"]:
                portfolio.exit_position(latest_price)
                print(f"✅ TAKE‑PROFIT hit at {latest_price:.4f}")
                in_trade = False
                current_trade = None

        if not in_trade and is_bold_buy(window, cfg):
            qty = portfolio.compute_position_size(latest_price, equity, cfg.RISK_PER_TRADE_PCT, cfg.SL_PCT)
            if qty > 0:
                current_trade = portfolio.enter_long(latest_price, qty, cfg.SL_PCT, cfg.TP_PCT)
                in_trade = True
                print(f"🔥 BOLD MOVE: BUY {qty} {symbol} @ {latest_price:.4f}")

        if in_trade and is_bold_sell(window, cfg):
            res = portfolio.exit_position(latest_price)
            if res:
                print(f"⚠️ BOLD EXIT: SELL {symbol} @ {latest_price:.4f} | Profit {res['profit']:.2f}")
            in_trade = False
            current_trade = None

        # sleep omitted for demo speed

    if portfolio.history:
        print(f"Demo complete — final equity: {portfolio.history[-1]:.2f}")

    return


if __name__ == "__main__":
    run_demo()

def analyze_symbol(symbol: str, bars: int = 200, cfg: HCConfig = HCConfig()) -> dict:
    """Fetch recent data for symbol and return a compact analysis dict."""
    try:
        from exchange_client import get_spot_client

        client = get_spot_client()
    except Exception:
        client = None

    if client is None:
        return {"error": "no_client"}

    klines = fetch_klines(client, symbol, cfg.TIMEFRAME, bars)
    df = klines_to_dataframe(klines)
    if df.empty or len(df) < 30:
        return {"error": "insufficient_data"}

    df = add_hc_indicators(df, cfg)
    tactical = "HOLD"
    if is_bold_buy(df, cfg):
        tactical = "BUY"
    elif is_bold_sell(df, cfg):
        tactical = "SELL"

    return {
        "symbol": symbol,
        "tactical": tactical,
        "rsi": float(df["rsi"].iloc[-1]),
        "ema_gap_pct": float(df["ema_gap_pct"].iloc[-1]),
        "price": float(df["close"].iloc[-1]),
    }


def run_watchlist_demo(symbols: list[str], bars: int = 300, cfg: HCConfig = HCConfig()) -> dict:
    """Run analysis across a list of symbols and return results."""
    results: dict[str, dict] = {}
    for s in symbols:
        try:
            res = analyze_symbol(s, bars=bars, cfg=cfg)
            results[s] = res
        except Exception as e:
            results[s] = {"error": str(e)}
    return results


def execute_paper_order(symbol: str, side: str, quote_amount: float | None = None, quantity: float | None = None) -> dict:
    """Place a market order using configured exchange adapter (respects testnet flags)."""
    try:
        from exchange_client import get_spot_client

        client = get_spot_client()
        return client.place_order(symbol=symbol, side=side, order_type="MARKET", quantity=quantity, quote_qty=quote_amount)
    except Exception as e:
        return {"error": str(e)}
