from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from .config import DATA_PATH


def generate_synthetic_sales(
    periods: int = 365,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=periods, freq="D")
    trend = np.linspace(50, 120, periods)
    weekly = 10 * np.sin(np.arange(periods) * 2 * np.pi / 7)
    noise = rng.normal(0, 5, periods)
    sales = trend + weekly + noise
    sales = np.maximum(sales, 0)
    return pd.DataFrame({"ds": dates, "y": sales})


def ensure_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        df = generate_synthetic_sales()
        df.to_csv(path, index=False)
    return pd.read_csv(path, parse_dates=["ds"])


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    return ensure_dataset(path)