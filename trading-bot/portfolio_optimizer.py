"""
Portfolio optimization module using Hierarchical Risk Parity (HRP).
Falls back to equal-weight if pypfopt is unavailable.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from pypfopt import HRPOpt
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    logger.warning("pypfopt not installed -- all allocations will use equal-weight fallback")


def _equal_weights(symbols: list[str]) -> dict[str, float]:
    """1/N allocation."""
    if not symbols:
        return {}
    w = 1.0 / len(symbols)
    return {s: w for s in symbols}


def _cap_weights(weights: dict[str, float], max_weight: float) -> dict[str, float]:
    """
    Iteratively cap any weight above max_weight and redistribute the excess
    proportionally among uncapped assets.  Guarantees sum ~= 1.0.
    """
    if not weights:
        return {}

    capped: dict[str, float] = dict(weights)
    for _ in range(50):  # convergence guard
        excess = 0.0
        uncapped_total = 0.0
        uncapped_keys: list[str] = []

        for k, v in capped.items():
            if v > max_weight:
                excess += v - max_weight
                capped[k] = max_weight
            else:
                uncapped_keys.append(k)
                uncapped_total += v

        if excess == 0.0 or not uncapped_keys:
            break

        for k in uncapped_keys:
            capped[k] += excess * (capped[k] / uncapped_total) if uncapped_total > 0 else excess / len(uncapped_keys)

    # final normalization
    total = sum(capped.values())
    if total > 0:
        capped = {k: v / total for k, v in capped.items()}
    return capped


def get_optimal_weights(
    symbols: list[str],
    returns_dict: dict[str, pd.Series],
    max_weight: float = 0.25,
) -> dict[str, float]:
    """
    Compute HRP-optimal weights for *symbols* given their daily return series.

    Parameters
    ----------
    symbols : list of ticker strings
    returns_dict : {symbol: pd.Series of daily returns}
    max_weight : hard cap per asset (default 25 %)

    Returns
    -------
    {symbol: weight}  weights sum to ~1.0
    """
    # ---- edge: nothing to do ----
    if not symbols:
        return {}

    if len(symbols) == 1:
        return {symbols[0]: 1.0}

    # build aligned returns DataFrame
    valid_symbols: list[str] = []
    series_list: list[pd.Series] = []
    for s in symbols:
        ret = returns_dict.get(s)
        if ret is None or ret.empty:
            continue
        if (ret == 0).all() or ret.isna().all():
            continue
        valid_symbols.append(s)
        series_list.append(ret.rename(s))

    if not valid_symbols:
        logger.warning("All return series are empty/zero -- equal weight fallback")
        return _equal_weights(symbols)

    if len(valid_symbols) == 1:
        # only one usable asset: give it 100 %, rest 0
        out = {s: 0.0 for s in symbols}
        out[valid_symbols[0]] = 1.0
        return out

    returns_df = pd.concat(series_list, axis=1).dropna()

    if returns_df.shape[0] < 2:
        logger.warning("Fewer than 2 overlapping return rows -- equal weight fallback")
        return _equal_weights(symbols)

    if not PYPFOPT_AVAILABLE:
        return _equal_weights(symbols)

    # ---- HRP ----
    try:
        hrp = HRPOpt(returns_df)
        raw_weights: dict[str, float] = hrp.optimize()
    except Exception as exc:
        logger.warning("HRP optimization failed (%s) -- equal weight fallback", exc)
        return _equal_weights(symbols)

    # include symbols that were dropped (zero weight)
    for s in symbols:
        if s not in raw_weights:
            raw_weights[s] = 0.0

    weights = _cap_weights(raw_weights, max_weight)
    return weights


def compute_portfolio_risk_metrics(
    returns_dict: dict[str, pd.Series],
    weights: dict[str, float],
) -> dict:
    """
    Compute portfolio-level risk metrics.

    Returns
    -------
    dict with keys:
        portfolio_volatility   - annualized vol (sqrt-252)
        portfolio_sharpe       - annualized Sharpe assuming Rf=0
        max_correlation_pair   - (sym_a, sym_b, corr) tuple or None
        diversification_ratio  - weighted-avg-vol / portfolio-vol
    """
    result: dict = {
        "portfolio_volatility": 0.0,
        "portfolio_sharpe": 0.0,
        "max_correlation_pair": None,
        "diversification_ratio": 1.0,
    }

    symbols = [s for s, w in weights.items() if w > 0]
    if not symbols:
        return result

    series_list = []
    for s in symbols:
        ret = returns_dict.get(s)
        if ret is None or ret.empty:
            return result
        series_list.append(ret.rename(s))

    df = pd.concat(series_list, axis=1).dropna()
    if df.shape[0] < 2:
        return result

    w_arr = np.array([weights[s] for s in symbols])
    cov_matrix = df.cov().values
    daily_var = float(w_arr @ cov_matrix @ w_arr)
    daily_vol = np.sqrt(max(daily_var, 0.0))
    ann_vol = daily_vol * np.sqrt(252)

    daily_mean = float(w_arr @ df.mean().values)
    ann_return = daily_mean * 252

    sharpe = (ann_return / ann_vol) if ann_vol > 0 else 0.0

    # max correlation pair
    corr = df.corr()
    max_corr_pair = None
    max_corr_val = -2.0
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = corr.iloc[i, j]
            if not np.isnan(c) and c > max_corr_val:
                max_corr_val = c
                max_corr_pair = (cols[i], cols[j], round(float(c), 4))

    # diversification ratio = weighted avg of individual vols / portfolio vol
    individual_vols = df.std().values * np.sqrt(252)
    weighted_avg_vol = float(w_arr @ individual_vols)
    div_ratio = (weighted_avg_vol / ann_vol) if ann_vol > 0 else 1.0

    result["portfolio_volatility"] = round(ann_vol, 6)
    result["portfolio_sharpe"] = round(sharpe, 4)
    result["max_correlation_pair"] = max_corr_pair
    result["diversification_ratio"] = round(div_ratio, 4)
    return result


def get_rebalance_needed(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    threshold: float = 0.05,
) -> dict[str, float]:
    """
    Return {symbol: delta} for every asset whose weight drifted beyond *threshold*.
    Positive delta = need to buy more; negative = need to trim.
    Returns empty dict if everything is within tolerance.
    """
    all_symbols = set(current_weights) | set(target_weights)
    deltas: dict[str, float] = {}
    for s in all_symbols:
        cur = current_weights.get(s, 0.0)
        tgt = target_weights.get(s, 0.0)
        d = tgt - cur
        if abs(d) > threshold:
            deltas[s] = round(d, 6)
    return deltas
