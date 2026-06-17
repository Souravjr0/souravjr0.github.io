"""
feature_engineering.py
Extracts 45+ statistical time-series features from OHLCV DataFrames.
All indicators computed with numpy/pandas -- no TA-Lib dependency.
"""

import numpy as np
import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FEATURE_COLUMNS: list[str] = [
    # Price Dynamics (10)
    "feat_ret_1", "feat_ret_3", "feat_ret_5", "feat_ret_10",
    "feat_log_ret_1",
    "feat_momentum_10", "feat_momentum_20",
    "feat_roc_5", "feat_roc_10",
    "feat_acceleration",
    # Volatility (8)
    "feat_vol_5", "feat_vol_10", "feat_vol_20",
    "feat_parkinson_vol", "feat_garman_klass_vol",
    "feat_atr_ratio", "feat_bb_width", "feat_bb_pctb",
    # Volume Profile (6)
    "feat_vol_zscore", "feat_obv_slope", "feat_vpt",
    "feat_rel_volume", "feat_vol_price_corr", "feat_mfi",
    # Microstructure (5)
    "feat_hl_range_ratio", "feat_close_position", "feat_gap",
    "feat_upper_shadow", "feat_lower_shadow",
    # Oscillator Derivatives (5)
    "feat_rsi_slope", "feat_macd_hist_accel", "feat_bb_width_change",
    "feat_rsi_divergence", "feat_stoch_rsi",
    # Statistical (6)
    "feat_skewness_20", "feat_kurtosis_20", "feat_hurst",
    "feat_autocorr_1", "feat_autocorr_5", "feat_entropy",
    # Trend/Pattern (5)
    "feat_consec_up", "feat_consec_down",
    "feat_dist_ema20", "feat_dist_ema50", "feat_trend_strength",
]


def get_feature_columns() -> list[str]:
    """Return the canonical list of all feature column names."""
    return list(_FEATURE_COLUMNS)


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Append 45+ engineered feature columns to *df* in-place and return it.

    Expects at minimum: open, high, low, close, volume.
    Optionally uses indicator columns produced by ``add_indicators``:
        rsi14, macd, macd_hist, atr14, ema_fast, ema_slow,
        bb_upper, bb_lower, bb_mid, ema_20, ema_50.

    Works on DataFrames as small as 30 rows.  Never calls ``dropna()``.
    """
    if df.empty:
        for col in _FEATURE_COLUMNS:
            df[col] = np.nan
        return df

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    opn = df["open"].astype(float)
    volume = df["volume"].astype(float)

    returns = close.pct_change()

    # ------------------------------------------------------------------
    # 1. Price Dynamics (10)
    # ------------------------------------------------------------------
    df["feat_ret_1"] = returns
    df["feat_ret_3"] = close.pct_change(3)
    df["feat_ret_5"] = close.pct_change(5)
    df["feat_ret_10"] = close.pct_change(10)
    df["feat_log_ret_1"] = np.log(close / close.shift(1))
    df["feat_momentum_10"] = close / close.shift(10) - 1.0
    df["feat_momentum_20"] = close / close.shift(20) - 1.0
    df["feat_roc_5"] = (close - close.shift(5)) / close.shift(5).replace(0, np.nan)
    df["feat_roc_10"] = (close - close.shift(10)) / close.shift(10).replace(0, np.nan)
    mom10 = close / close.shift(10) - 1.0
    df["feat_acceleration"] = mom10 - mom10.shift(1)

    # ------------------------------------------------------------------
    # 2. Volatility (8)
    # ------------------------------------------------------------------
    df["feat_vol_5"] = returns.rolling(window=5, min_periods=1).std()
    df["feat_vol_10"] = returns.rolling(window=10, min_periods=1).std()
    df["feat_vol_20"] = returns.rolling(window=20, min_periods=1).std()

    # Parkinson volatility: sqrt( (1/4*ln2) * rolling_mean(ln(H/L)^2) )
    hl_log = np.log(high / low.replace(0, np.nan))
    df["feat_parkinson_vol"] = np.sqrt(
        (hl_log ** 2).rolling(window=20, min_periods=1).mean() / (4.0 * np.log(2))
    )

    # Garman-Klass volatility
    co_log = np.log(close / opn.replace(0, np.nan))
    gk = 0.5 * (hl_log ** 2) - (2.0 * np.log(2) - 1.0) * (co_log ** 2)
    df["feat_garman_klass_vol"] = np.sqrt(gk.rolling(window=20, min_periods=1).mean().clip(lower=0))

    # ATR ratio (needs atr14)
    if "atr14" in df.columns:
        atr = df["atr14"].astype(float)
        df["feat_atr_ratio"] = atr / close.replace(0, np.nan)
    else:
        df["feat_atr_ratio"] = np.nan

    # Bollinger bandwidth & %B
    if {"bb_upper", "bb_lower", "bb_mid"}.issubset(df.columns):
        bb_u = df["bb_upper"].astype(float)
        bb_l = df["bb_lower"].astype(float)
        bb_m = df["bb_mid"].astype(float)
        df["feat_bb_width"] = (bb_u - bb_l) / bb_m.replace(0, np.nan)
        bb_range = (bb_u - bb_l).replace(0, np.nan)
        df["feat_bb_pctb"] = (close - bb_l) / bb_range
    else:
        df["feat_bb_width"] = np.nan
        df["feat_bb_pctb"] = np.nan

    # ------------------------------------------------------------------
    # 3. Volume Profile (6)
    # ------------------------------------------------------------------
    vol_mean = volume.rolling(window=20, min_periods=1).mean()
    vol_std = volume.rolling(window=20, min_periods=1).std().replace(0, np.nan)
    df["feat_vol_zscore"] = ((volume - vol_mean) / vol_std).fillna(0.0)

    # OBV slope (10-bar linear regression slope of OBV)
    obv = (np.sign(returns).fillna(0) * volume).cumsum()
    df["feat_obv_slope"] = _rolling_slope(obv, window=10).fillna(0.0)

    # Volume-Price Trend (cumulative)
    df["feat_vpt"] = (returns.fillna(0) * volume).cumsum().fillna(0.0)

    # Relative volume
    df["feat_rel_volume"] = (volume / vol_mean.replace(0, np.nan)).fillna(1.0)

    # Rolling correlation: volume vs close returns (20 bar)
    df["feat_vol_price_corr"] = volume.rolling(window=20, min_periods=5).corr(returns).fillna(0.0)

    # Money Flow Index (14 period)
    df["feat_mfi"] = _money_flow_index(high, low, close, volume, period=14).fillna(50.0)

    # ------------------------------------------------------------------
    # 4. Microstructure (5)
    # ------------------------------------------------------------------
    hl_range = (high - low).replace(0, np.nan)
    df["feat_hl_range_ratio"] = hl_range / close.replace(0, np.nan)
    df["feat_close_position"] = (close - low) / hl_range
    df["feat_gap"] = opn / close.shift(1).replace(0, np.nan) - 1.0
    bar_body_top = pd.concat([opn, close], axis=1).max(axis=1)
    bar_body_bot = pd.concat([opn, close], axis=1).min(axis=1)
    df["feat_upper_shadow"] = (high - bar_body_top) / hl_range
    df["feat_lower_shadow"] = (bar_body_bot - low) / hl_range

    # ------------------------------------------------------------------
    # 5. Oscillator Derivatives (5)
    # ------------------------------------------------------------------
    if "rsi14" in df.columns:
        rsi = df["rsi14"].astype(float)
        df["feat_rsi_slope"] = rsi - rsi.shift(3)
    else:
        df["feat_rsi_slope"] = np.nan

    if "macd_hist" in df.columns:
        mh = df["macd_hist"].astype(float)
        mh_d1 = mh.diff()
        df["feat_macd_hist_accel"] = mh_d1.diff()
    else:
        df["feat_macd_hist_accel"] = np.nan

    if "feat_bb_width" in df.columns:
        df["feat_bb_width_change"] = df["feat_bb_width"] - df["feat_bb_width"].shift(1)
    else:
        df["feat_bb_width_change"] = np.nan

    # RSI divergence: price ROC(10) vs RSI ROC(10)
    if "rsi14" in df.columns:
        rsi = df["rsi14"].astype(float)
        price_roc = close.pct_change(10)
        rsi_roc = (rsi - rsi.shift(10)) / rsi.shift(10).replace(0, np.nan)
        df["feat_rsi_divergence"] = price_roc - rsi_roc
    else:
        df["feat_rsi_divergence"] = np.nan

    # Stochastic RSI (14, 14)
    if "rsi14" in df.columns:
        rsi = df["rsi14"].astype(float)
        rsi_min = rsi.rolling(window=14, min_periods=1).min()
        rsi_max = rsi.rolling(window=14, min_periods=1).max()
        rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
        df["feat_stoch_rsi"] = (rsi - rsi_min) / rsi_range
    else:
        df["feat_stoch_rsi"] = np.nan

    # ------------------------------------------------------------------
    # 6. Statistical (6)
    # ------------------------------------------------------------------
    df["feat_skewness_20"] = returns.rolling(window=20, min_periods=5).skew()
    df["feat_kurtosis_20"] = returns.rolling(window=20, min_periods=5).kurt()

    df["feat_hurst"] = _rolling_hurst(returns, window=50)

    df["feat_autocorr_1"] = returns.rolling(window=20, min_periods=5).apply(
        lambda x: x.autocorr(lag=1) if len(x) > 1 else 0.0, raw=False
    )
    df["feat_autocorr_5"] = returns.rolling(window=20, min_periods=5).apply(
        lambda x: x.autocorr(lag=5) if len(x) > 5 else 0.0, raw=False
    )

    df["feat_entropy"] = _rolling_approx_entropy(returns, window=20)

    # ------------------------------------------------------------------
    # 7. Trend / Pattern (5)
    # ------------------------------------------------------------------
    up = (close > close.shift(1)).astype(int)
    down = (close < close.shift(1)).astype(int)
    df["feat_consec_up"] = _consecutive_count(up)
    df["feat_consec_down"] = _consecutive_count(down)

    if "ema_20" in df.columns and "atr14" in df.columns:
        atr_safe = df["atr14"].astype(float).replace(0, np.nan)
        df["feat_dist_ema20"] = (close - df["ema_20"].astype(float)) / atr_safe
    else:
        df["feat_dist_ema20"] = np.nan

    if "ema_50" in df.columns and "atr14" in df.columns:
        atr_safe = df["atr14"].astype(float).replace(0, np.nan)
        df["feat_dist_ema50"] = (close - df["ema_50"].astype(float)) / atr_safe
    else:
        df["feat_dist_ema50"] = np.nan

    if {"ema_fast", "ema_slow"}.issubset(df.columns) and "atr14" in df.columns:
        atr_safe = df["atr14"].astype(float).replace(0, np.nan)
        df["feat_trend_strength"] = (
            (df["ema_fast"].astype(float) - df["ema_slow"].astype(float)).abs() / atr_safe
        )
    else:
        df["feat_trend_strength"] = np.nan

    # ------------------------------------------------------------------
    # Final NaN handling: forward-fill then back-fill (never drop rows)
    # ------------------------------------------------------------------
    feat_cols = [c for c in _FEATURE_COLUMNS if c in df.columns]
    df[feat_cols] = df[feat_cols].ffill().bfill()

    # Replace any leftover inf/-inf with 0
    df[feat_cols] = df[feat_cols].replace([np.inf, -np.inf], 0.0)

    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling linear-regression slope over *window* bars using fast vectorization."""
    y = series.values
    n = len(y)
    out = np.zeros(n)
    if n < window:
        return pd.Series(out, index=series.index)

    # Precompute standard linear regression parameters for fixed window
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0:
        return pd.Series(out, index=series.index)

    from numpy.lib.stride_tricks import sliding_window_view
    try:
        y_windows = sliding_window_view(y, window_shape=window)
        y_means = y_windows.mean(axis=1, keepdims=True)
        slopes = np.sum((x - x_mean) * (y_windows - y_means), axis=1) / denom
        out[window - 1:] = slopes
        out[:window - 1] = slopes[0]
    except Exception:
        # Robust fallback
        def _slope(val):
            return np.sum((x - x_mean) * (val - np.mean(val))) / denom
        return series.rolling(window=window, min_periods=2).apply(_slope, raw=True)

    return pd.Series(out, index=series.index).ffill().bfill()


def _money_flow_index(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Money Flow Index without TA-Lib."""
    tp = (high + low + close) / 3.0
    raw_mf = tp * volume
    pos_flow = pd.Series(0.0, index=close.index, dtype=float)
    neg_flow = pd.Series(0.0, index=close.index, dtype=float)

    tp_diff = tp.diff()
    pos_flow = raw_mf.where(tp_diff > 0, 0.0)
    neg_flow = raw_mf.where(tp_diff < 0, 0.0)

    pos_sum = pos_flow.rolling(window=period, min_periods=1).sum()
    neg_sum = neg_flow.rolling(window=period, min_periods=1).sum().replace(0, np.nan)

    mf_ratio = pos_sum / neg_sum
    mfi = 100.0 - (100.0 / (1.0 + mf_ratio))
    return mfi


def _rolling_hurst(returns: pd.Series, window: int = 50) -> pd.Series:
    """Vectorized Hurst exponent estimate using rescaled-range (R/S) analysis."""
    y = returns.values
    n = len(y)
    out = np.full(n, 0.5)
    if n < 10:
        return pd.Series(out, index=returns.index)

    from numpy.lib.stride_tricks import sliding_window_view
    try:
        y_windows = sliding_window_view(y, window_shape=window)
        means = y_windows.mean(axis=1, keepdims=True)
        diffs = y_windows - means
        cumsums = np.cumsum(diffs, axis=1)
        r = np.max(cumsums, axis=1) - np.min(cumsums, axis=1)
        s = np.std(y_windows, axis=1, ddof=1)
        
        valid = (s > 1e-12) & (r > 1e-12)
        rs = np.where(valid, r / np.maximum(s, 1e-12), 1.0)
        h = np.where(valid & (rs > 0), np.log(rs) / np.log(window), 0.5)
        h = np.clip(h, 0.0, 1.0)
        
        out[window - 1:] = h
        out[:window - 1] = h[0]
    except Exception:
        # Fallback
        def _hurst_rs(x: np.ndarray) -> float:
            n_val = len(x)
            if n_val < 10:
                return 0.5
            mean_x = np.mean(x)
            y_val = np.cumsum(x - mean_x)
            r_val = float(np.max(y_val) - np.min(y_val))
            s_val = float(np.std(x, ddof=1))
            if s_val < 1e-12 or r_val < 1e-12:
                return 0.5
            rs_val = r_val / s_val
            if rs_val <= 0:
                return 0.5
            return np.clip(float(np.log(rs_val) / np.log(n_val)), 0.0, 1.0)
        return returns.rolling(window=window, min_periods=10).apply(_hurst_rs, raw=True)

    return pd.Series(out, index=returns.index).ffill().bfill()


def _rolling_approx_entropy(series: pd.Series, window: int = 20) -> pd.Series:
    """
    Vectorized approximate entropy proxy.
    Uses binned distribution entropy as a fast proxy, calculated via numpy matrix operations.
    """
    y = series.values
    n = len(y)
    out = np.zeros(n)
    if n < 5:
        return pd.Series(out, index=series.index)

    from numpy.lib.stride_tricks import sliding_window_view
    try:
        y_windows = sliding_window_view(y, window_shape=window)
        mins = y_windows.min(axis=1)
        maxs = y_windows.max(axis=1)
        stds = y_windows.std(axis=1)
        
        # Avoid pandas overhead by doing a fast list/array sweep over the pre-built view
        for idx in range(len(y_windows)):
            win = y_windows[idx]
            std = stds[idx]
            if std < 1e-12:
                out[window - 1 + idx] = 0.0
                continue
            mn, mx = mins[idx], maxs[idx]
            bins = np.linspace(mn - 1e-10, mx + 1e-10, 6)
            counts, _ = np.histogram(win, bins=bins)
            probs = counts / counts.sum()
            probs = probs[probs > 0]
            out[window - 1 + idx] = float(-np.sum(probs * np.log(probs)))
            
        out[:window - 1] = out[window - 1]
    except Exception:
        # Fallback
        def _entropy(x: np.ndarray) -> float:
            n_val = len(x)
            if n_val < 5:
                return 0.0
            x = x[~np.isnan(x)]
            if len(x) < 5:
                return 0.0
            std = np.std(x)
            if std < 1e-12:
                return 0.0
            bins = np.linspace(np.min(x) - 1e-10, np.max(x) + 1e-10, 6)
            counts, _ = np.histogram(x, bins=bins)
            probs = counts / counts.sum()
            probs = probs[probs > 0]
            return float(-np.sum(probs * np.log(probs)))
        return series.rolling(window=window, min_periods=5).apply(_entropy, raw=True)

    return pd.Series(out, index=series.index).ffill().bfill()


def _consecutive_count(mask: pd.Series) -> pd.Series:
    """Count consecutive True (1) streaks; resets to 0 on False."""
    groups = mask.ne(mask.shift()).cumsum()
    counts = mask.groupby(groups).cumsum()
    return counts.astype(float)
