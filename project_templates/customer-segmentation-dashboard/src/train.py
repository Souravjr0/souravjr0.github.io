from __future__ import annotations

from pathlib import Path

import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .data import load_customers

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS / "model.joblib"
SCALER_PATH = ARTIFACTS / "scaler.joblib"


def train_model(n_clusters: int = 4, random_state: int = 42) -> dict:
    df = load_customers()
    scaler = StandardScaler()
    X = scaler.fit_transform(df)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    model.fit(X)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    return {
        "clusters": n_clusters,
        "samples": len(df),
    }


if __name__ == "__main__":
    info = train_model()
    print(info)
