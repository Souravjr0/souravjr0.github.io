import numpy as np
import pandas as pd


def _vwap(df: pd.DataFrame) -> pd.Series:
    q = df["volume"]
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * q).cumsum() / q.cumsum()


def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    hl2 = (df["high"] + df["low"]) / 2
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    direction = pd.Series(index=df.index, dtype="int8")
    final_upper = upperband.copy()
    final_lower = lowerband.copy()

    for i in range(1, len(df)):
        if df["close"].iat[i - 1] <= final_upper.iat[i - 1]:
            final_upper.iat[i] = min(upperband.iat[i], final_upper.iat[i - 1])
        if df["close"].iat[i - 1] >= final_lower.iat[i - 1]:
            final_lower.iat[i] = max(lowerband.iat[i], final_lower.iat[i - 1])

        if df["close"].iat[i] > final_upper.iat[i - 1]:
            direction.iat[i] = 1
        elif df["close"].iat[i] < final_lower.iat[i - 1]:
            direction.iat[i] = -1
        else:
            direction.iat[i] = direction.iat[i - 1] if i > 0 else 0

    return direction.fillna(0)


def _ichimoku(df: pd.DataFrame) -> dict:
    high = df["high"]
    low = df["low"]
    conversion = (high.rolling(9).max() + low.rolling(9).min()) / 2
    base = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((conversion + base) / 2).shift(26)
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    return {"conversion": conversion, "base": base, "span_a": span_a, "span_b": span_b}


def _chandelier_exit(df: pd.DataFrame, period: int = 22, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """Calculate Chandelier Exit trailing stops for longs and shorts."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    
    high_max = high.rolling(window=period).max()
    low_min = low.rolling(window=period).min()
    
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    
    long_stop = high_max - atr * multiplier
    short_stop = low_min + atr * multiplier
    return long_stop, short_stop


def _squeeze_momentum(df: pd.DataFrame, bb_period: int = 20, bb_mult: float = 2.0, kc_period: int = 20, kc_mult: float = 1.5) -> tuple[pd.Series, pd.Series]:
    """Calculate Squeeze Momentum Indicator (LazyBear style)."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    prev_close = close.shift(1)
    
    # Bollinger Bands
    bb_mid = close.rolling(window=bb_period).mean()
    bb_std = close.rolling(window=bb_period).std()
    bb_upper = bb_mid + bb_mult * bb_std
    bb_lower = bb_mid - bb_mult * bb_std
    
    # Keltner Channels
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=kc_period, min_periods=1).mean()
    
    kc_mid = close.ewm(span=kc_period, adjust=False).mean()
    kc_upper = kc_mid + kc_mult * atr
    kc_lower = kc_mid - kc_mult * atr
    
    # Squeeze condition (True = squeezing, False = breakout/released)
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    
    # Momentum Value (Linear regression of distance to rolling average midpoint)
    highest = high.rolling(window=bb_period).max()
    lowest = low.rolling(window=bb_period).min()
    midpoint = (highest + lowest) / 2
    avg_mid = (midpoint + bb_mid) / 2
    diff = close - avg_mid
    
    def get_linreg(series):
        if len(series) < bb_period or np.isnan(series).any():
            return 0.0
        x = np.arange(len(series))
        slope, intercept = np.polyfit(x, series, 1)
        return slope * (len(series) - 1) + intercept

    linreg = diff.rolling(window=bb_period).apply(get_linreg, raw=True)
    return squeeze_on, linreg


def market_regime(df: pd.DataFrame) -> str:
    close = df["close"]
    ema200 = close.ewm(span=200, adjust=False).mean()
    slope = ema200.diff().iloc[-1]
    vol = close.pct_change().rolling(window=20).std().iloc[-1]
    if slope > 0 and vol < 0.05:
        return "Bull"
    if slope < 0 and vol > 0.05:
        return "Bear"
    return "Sideways"


def analyze_advanced(df: pd.DataFrame) -> dict:
    """Return a compact advanced analysis summary for the provided dataframe."""
    if df is None or df.empty:
        return {}

    out = {}
    try:
        out["vwap"] = float(_vwap(df).iloc[-1])
    except Exception:
        out["vwap"] = None

    try:
        st = _supertrend(df)
        out["supertrend"] = int(st.iloc[-1])
    except Exception:
        out["supertrend"] = 0

    try:
        ich = _ichimoku(df)
        out["ichi_bull"] = bool(ich["span_a"].iloc[-1] > ich["span_b"].iloc[-1])
    except Exception:
        out["ichi_bull"] = None

    try:
        out["regime"] = market_regime(df)
    except Exception:
        out["regime"] = "n/a"

    # Add Chandelier Exit
    try:
        clong, cshort = _chandelier_exit(df)
        out["chandelier_long"] = float(clong.iloc[-1])
        out["chandelier_short"] = float(cshort.iloc[-1])
    except Exception:
        out["chandelier_long"] = None
        out["chandelier_short"] = None

    # Add Squeeze Momentum
    try:
        sq_on, sq_mom = _squeeze_momentum(df)
        out["squeeze_on"] = bool(sq_on.iloc[-1])
        out["squeeze_mom"] = float(sq_mom.iloc[-1])
        
        # Determine momentum direction (rising/falling, positive/negative)
        prev_mom = float(sq_mom.iloc[-2]) if len(sq_mom) > 1 else 0.0
        curr_mom = out["squeeze_mom"]
        if curr_mom >= 0:
            out["squeeze_dir"] = "UP" if curr_mom > prev_mom else "DOWN"
        else:
            out["squeeze_dir"] = "UP" if curr_mom > prev_mom else "DOWN"
    except Exception:
        out["squeeze_on"] = False
        out["squeeze_mom"] = 0.0
        out["squeeze_dir"] = "NEUTRAL"

    # Simple tactical signal: combine EMA slope, Supertrend and Ichimoku
    try:
        ema20 = df["close"].ewm(span=20, adjust=False).mean()
        ema50 = df["close"].ewm(span=50, adjust=False).mean()
        ema_signal = 1 if ema20.iloc[-1] > ema50.iloc[-1] else -1
        st_sig = out.get("supertrend", 0)
        ichi = out.get("ichi_bull")
        score = 0
        score += 1 if ema_signal == 1 else -1
        score += 1 if st_sig == 1 else -1
        score += 1 if ichi else -1
        out["tactical_signal"] = "BUY" if score >= 1 else "SELL" if score <= -1 else "HOLD"
    except Exception:
        out["tactical_signal"] = "n/a"

    return out
