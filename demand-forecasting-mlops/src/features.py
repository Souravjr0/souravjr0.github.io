from __future__ import annotations

import pandas as pd

from .config import DEFAULT_LAGS


def make_features(df: pd.DataFrame, lags: int = DEFAULT_LAGS) -> pd.DataFrame:
    df = df.sort_values("ds").reset_index(drop=True)
    for lag in range(1, lags + 1):
        df[f"lag_{lag}"] = df["y"].shift(lag)
    df = df.dropna().reset_index(drop=True)
    return df


def build_feature_row(recent_values: list[float], lags: int = DEFAULT_LAGS) -> pd.DataFrame:
    if len(recent_values) < lags:
        raise ValueError(f"Need at least {lags} recent values")
    row = {f"lag_{i}": recent_values[-i] for i in range(1, lags + 1)}
    return pd.DataFrame([row])