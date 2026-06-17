"""
model_explainer.py
SHAP-based model explanation module for trading bot signal predictions.
Provides human-readable insights into why the ML engine predicted a specific signal.
"""

import logging
import numpy as np
import pandas as pd
from typing import Any

# Configure logger
logger = logging.getLogger("trading_bot.model_explainer")

# Attempt SHAP import
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP library not found. SHAP explanations will be disabled.")

from ml_engine import MLSignalEngine
from feature_engineering import get_feature_columns

# Human-readable feature descriptions
FEATURE_DESCRIPTIONS = {
    # Price Dynamics
    "feat_ret_1": "1-bar price return",
    "feat_ret_3": "3-bar price return",
    "feat_ret_5": "5-bar price return",
    "feat_ret_10": "10-bar price return",
    "feat_log_ret_1": "1-bar log price return",
    "feat_momentum_10": "10-bar price momentum",
    "feat_momentum_20": "20-bar price momentum",
    "feat_roc_5": "5-bar Rate of Change",
    "feat_roc_10": "10-bar Rate of Change",
    "feat_acceleration": "Price velocity acceleration",

    # Volatility
    "feat_vol_5": "5-bar short-term volatility",
    "feat_vol_10": "10-bar medium-term volatility",
    "feat_vol_20": "20-bar long-term volatility",
    "feat_parkinson_vol": "Parkinson high-low volatility",
    "feat_garman_klass_vol": "Garman-Klass open-close-high-low volatility",
    "feat_atr_ratio": "Normalized ATR ratio",
    "feat_bb_width": "Bollinger Bandwidth width",
    "feat_bb_pctb": "Bollinger Bands %B position",

    # Volume Profile
    "feat_vol_zscore": "Volume standard z-score",
    "feat_obv_slope": "On-Balance Volume (OBV) trend slope",
    "feat_vpt": "Volume-Price Trend metric",
    "feat_rel_volume": "Relative volume spike",
    "feat_vol_price_corr": "Price-Volume trend correlation",
    "feat_mfi": "Money Flow Index (MFI)",

    # Microstructure
    "feat_hl_range_ratio": "High-low spread range ratio",
    "feat_close_position": "Closing price position relative to range",
    "feat_gap": "Overnight price gap percentage",
    "feat_upper_shadow": "Upper candle shadow wick size",
    "feat_lower_shadow": "Lower candle shadow wick size",

    # Oscillator Derivatives
    "feat_rsi_slope": "RSI momentum trend slope",
    "feat_macd_hist_accel": "MACD Histogram divergence acceleration",
    "feat_bb_width_change": "Bollinger Bandwidth expansion speed",
    "feat_rsi_divergence": "Price vs RSI divergence signal",
    "feat_stoch_rsi": "Stochastic RSI value",

    # Statistical
    "feat_skewness_20": "20-bar return skewness asymmetry",
    "feat_kurtosis_20": "20-bar return kurtosis peakedness",
    "feat_hurst": "Hurst exponent trend persistence",
    "feat_autocorr_1": "1-bar return autocorrelation persistence",
    "feat_autocorr_5": "5-bar return autocorrelation persistence",
    "feat_entropy": "Return distribution approximate entropy",

    # Trend/Pattern
    "feat_consec_up": "Consecutive green candles count",
    "feat_consec_down": "Consecutive red candles count",
    "feat_dist_ema20": "Distance from EMA-20 trend line",
    "feat_dist_ema50": "Distance from EMA-50 trend line",
    "feat_trend_strength": "Fast vs Slow EMA trend separation strength"
}

def explain_prediction(engine: MLSignalEngine, df: pd.DataFrame, top_n: int = 3) -> list[dict[str, Any]]:
    """
    Explain the current prediction using SHAP on the trained XGBoost model.
    
    Returns a list of dicts:
        {"feature": str, "value": float, "shap_value": float, "description": str}
    """
    if not SHAP_AVAILABLE:
        return []
        
    if engine._xgb_model is None:
        if not engine.load_model():
            logger.warning("Could not load models to generate explanations.")
            return []

    # Get feature list and last row
    feat_cols = engine._feature_cols or engine._meta.get("feature_cols", get_feature_columns())
    available = [c for c in feat_cols if c in df.columns]
    if not available:
        logger.warning("No matching feature columns found in DataFrame for explanation.")
        return []

    try:
        # Get the feature values of the last row
        last_row_df = df[available].iloc[[-1]]
        last_row_values = last_row_df.values.astype(np.float32)
        # Ensure no NaN
        last_row_values = np.nan_to_num(last_row_values, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Instantiate TreeExplainer on the XGBoost model
        # Note: XGBoost multiclass model returns SHAP values of shape (num_classes, num_samples, num_features)
        explainer = shap.TreeExplainer(engine._xgb_model)
        shap_values = explainer.shap_values(last_row_values)
        
        # Determine predicted class index
        # Predict using the engine
        signal, _ = engine.predict(df)
        class_idx = 0
        if signal == "BUY":
            class_idx = 1
        elif signal == "SELL":
            class_idx = 2
            
        # Get SHAP values for the predicted class
        # Depending on SHAP version and model, shape can vary
        if isinstance(shap_values, list):
            # Old SHAP format: list of arrays per class
            class_shap = shap_values[class_idx][0]
        elif len(shap_values.shape) == 3:
            # Modern SHAP shape: (samples, features, classes) or (classes, samples, features)
            # Typically (samples, features, classes) or (classes, samples, features)
            # Let's inspect shape
            if shap_values.shape[0] == 3: # 3 classes
                class_shap = shap_values[class_idx][0]
            else: # (samples, features, classes)
                class_shap = shap_values[0, :, class_idx]
        else:
            class_shap = shap_values[0]
            
        # Compile explanations
        explanations = []
        for i, col in enumerate(available):
            val = float(last_row_df.iloc[0][col])
            sv = float(class_shap[i])
            desc = FEATURE_DESCRIPTIONS.get(col, f"Technical feature: {col}")
            explanations.append({
                "feature": col,
                "value": val,
                "shap_value": sv,
                "description": desc
            })
            
        # Sort by absolute SHAP value contribution
        explanations.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        return explanations[:top_n]
        
    except Exception as e:
        logger.error(f"Error in generating SHAP explanations: {e}")
        return []

def format_explanation_text(explanations: list[dict[str, Any]]) -> str:
    """
    Format SHAP explanations into a clean string for console or Telegram.
    """
    if not explanations:
        return "No explainer data available."
        
    lines = []
    for i, exp in enumerate(explanations):
        col = exp["feature"]
        val = exp["value"]
        sv = exp["shap_value"]
        desc = exp["description"]
        
        # Indicator of direction
        direction = "📈 positive" if sv > 0 else "📉 negative"
        lines.append(
            f"{i+1}. <b>{desc}</b> ({col}): "
            f"Value=<code>{val:.4f}</code> contributes <b>{direction}</b> (impact = <code>{sv:+.4f}</code>)"
        )
        
    return "\n".join(lines)
