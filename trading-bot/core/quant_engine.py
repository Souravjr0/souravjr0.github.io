"""
quant_engine.py
Hedge Fund Quantitative Analysis Engine.
Implements Kalman Filters, EWMA Volatility, Fractional Kelly Sizing, and Quant Market Regimes.
"""

import numpy as np
import pandas as pd
from typing import Tuple # or just use builtin tuple directly


class KalmanFilter1D:
    """
    Adaptive 1D Kalman Filter for dynamic price trend tracking and mean-reversion analysis.
    Estimates the hidden "true" price of an asset from noisy close price measurements.
    """

    def __init__(self, Q_ratio: float = 1e-4, R_ratio: float = 1e-2) -> None:
        """
        Q_ratio: process noise ratio relative to initial price variance
        R_ratio: measurement noise ratio relative to initial price variance
        """
        self.Q_ratio = Q_ratio
        self.R_ratio = R_ratio

    def run_filter(self, prices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Runs the Kalman Filter over an array of prices.
        Returns (filtered_prices, residuals, z_scores).
        """
        n = len(prices)
        filtered = np.zeros(n)
        residuals = np.zeros(n)
        z_scores = np.zeros(n)

        if n == 0:
            return filtered, residuals, z_scores

        # Adaptive noise initialization based on initial sample variance
        initial_vol = np.std(prices[:min(n, 20)])
        initial_vol = max(initial_vol, 1e-6)
        
        Q = (initial_vol ** 2) * self.Q_ratio
        R = (initial_vol ** 2) * self.R_ratio

        # Initial states
        x = prices[0]
        P = R

        filtered[0] = x
        residuals[0] = 0.0
        z_scores[0] = 0.0

        for t in range(1, n):
            # 1. Prediction step
            x_pred = x
            P_pred = P + Q

            # 2. Update step
            measurement = prices[t]
            residual = measurement - x_pred
            S = P_pred + R  # Innovation covariance
            K = P_pred / S  # Kalman gain

            x = x_pred + K * residual
            P = (1.0 - K) * P_pred

            filtered[t] = x
            residuals[t] = residual
            z_scores[t] = residual / np.sqrt(S) if S > 0 else 0.0

        return filtered, residuals, z_scores


def compute_ewma_volatility(returns: pd.Series, decay: float = 0.94) -> pd.Series:
    """
    Computes Exponentially Weighted Moving Average (EWMA) Volatility (RiskMetrics standard).
    More responsive to dynamic volatility shifts than raw standard deviation.
    """
    ret_vals = returns.fillna(0.0).values
    n = len(ret_vals)
    ewma_var = np.zeros(n)
    
    if n > 0:
        # Initialize with simple variance of first sample
        ewma_var[0] = np.var(ret_vals[:min(n, 10)]) if n >= 2 else 0.0
        
    for t in range(1, n):
        ewma_var[t] = decay * ewma_var[t - 1] + (1 - decay) * (ret_vals[t] ** 2)
        
    # Scale to annualized volatility (assuming daily returns, or leave as-is for timeframe context)
    vol = np.sqrt(ewma_var)
    return pd.Series(vol, index=returns.index)


def calculate_kelly_fraction(
    ml_confidence: float,
    win_loss_ratio: float = 1.5,
    fraction: float = 0.2,
) -> float:
    """
    Computes optimal allocation scale using Fractional Kelly Criterion.
    p = win probability (derived from ML confidence)
    q = 1 - p (loss probability)
    b = win_loss_ratio (ratio of average profit to average loss, e.g. TP/SL ratio)
    
    f* = (p * b - q) / b = p - (1 - p) / b
    """
    # Clamp confidence to probability range [0.3, 0.95] to prevent over-leverage
    p = np.clip(ml_confidence, 0.3, 0.95)
    q = 1.0 - p
    b = max(win_loss_ratio, 0.1)
    
    kelly_f = p - (q / b)
    # Apply fractional multiplier for safety and clip to [0, 1.0]
    scaled_kelly = np.clip(kelly_f * fraction, 0.0, 1.0)
    return float(scaled_kelly)


def classify_quant_regime(
    df: pd.DataFrame,
    kf_zscore: float,
    hurst_exp: float,
    ewma_vol: float,
) -> str:
    """
    Classifies the market regime using quantitative statistical indicators:
    - BULL_TREND: Hurst > 0.52 (trending), positive slope (price > 50 EMA)
    - BEAR_TREND: Hurst > 0.52 (trending), negative slope (price < 50 EMA)
    - MEAN_REVERSION: Hurst < 0.48 (anti-persistent), Z-score bound returning
    - HIGH_VOLATILITY: EWMA Volatility exceeds historic 70th percentile
    - SIDEWAYS_CHAOTIC: Otherwise
    """
    # Hurst Exponent regimes:
    # H > 0.5: Persistent (trending)
    # H < 0.5: Anti-persistent (mean-reverting)
    # H = 0.5: Random walk
    
    close = float(df["close"].iloc[-1])
    
    # Simple moving average for trend direction
    ma50 = float(df["ema_50"].iloc[-1]) if "ema_50" in df.columns else float(df["close"].rolling(50).mean().iloc[-1])
    
    is_bull = close > ma50
    is_trending = hurst_exp > 0.52
    is_mean_reverting = hurst_exp < 0.48
    
    # Calculate relative volatility percentile
    vol_series = df["close"].pct_change().rolling(20).std()
    recent_vols = vol_series.dropna().values
    
    if len(recent_vols) > 5:
        vol_threshold = np.percentile(recent_vols, 75)
        is_high_vol = ewma_vol > vol_threshold
    else:
        is_high_vol = False

    if is_high_vol:
        return "HIGH_VOLATILITY"
    elif is_trending:
        return "BULL_TREND" if is_bull else "BEAR_TREND"
    elif is_mean_reverting:
        return "MEAN_REVERSION"
    else:
        return "SIDEWAYS_CHAOTIC"
