import pandas as pd


def add_indicators(df: pd.DataFrame, atr_period: int = 14, ema_fast_span: int = 12, ema_slow_span: int = 26) -> pd.DataFrame:
    if df.empty:
        return df

    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["ema_fast"] = close.ewm(span=ema_fast_span, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=ema_slow_span, adjust=False).mean()
    df["ema_20"] = close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))

    ema_macd_fast = close.ewm(span=12, adjust=False).mean()
    ema_macd_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_macd_fast - ema_macd_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd - macd_signal

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr14"] = tr.rolling(window=atr_period).mean()

    df["bb_mid"] = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * bb_std
    df["bb_lower"] = df["bb_mid"] - 2 * bb_std

    df["donchian_high"] = high.rolling(window=20).max()
    df["donchian_low"] = low.rolling(window=20).min()

    returns = close.pct_change()
    df["volatility"] = returns.rolling(window=20).std() * 100

    return df
