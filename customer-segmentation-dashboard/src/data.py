from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "customers.csv"


def generate_customers(samples: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(18, 70, size=samples)
    income = rng.normal(60000, 15000, size=samples).clip(20000, 150000)
    spend_score = rng.normal(50, 20, size=samples).clip(1, 100)
    visits = rng.poisson(6, size=samples).clip(1, 25)

    df = pd.DataFrame(
        {
            "age": age,
            "income": income,
            "spend_score": spend_score,
            "visits_per_month": visits,
        }
    )
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    return df


def load_customers() -> pd.DataFrame:
    if not DATA_PATH.exists():
        return generate_customers()
    return pd.read_csv(DATA_PATH)