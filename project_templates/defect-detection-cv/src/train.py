from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import cv2
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.svm import SVC

from .features import extract_edge_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS / "model.joblib"
REPORT_PATH = ARTIFACTS / "report.json"


def _load_dataset() -> pd.DataFrame:
    labels_path = DATA_DIR / "labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError("Run scripts/generate_dataset.py first")
    return pd.read_csv(labels_path)


def train_model(random_state: int = 42):
    df = _load_dataset()
    features = []
    for _, row in df.iterrows():
        img = cv2.imread(row["image_path"], cv2.IMREAD_GRAYSCALE)
        features.append(extract_edge_features(img))

    X = np.vstack(features)
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    model = SVC(kernel="rbf", probability=True, random_state=random_state)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    report = classification_report(y_test, preds, output_dict=True)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    REPORT_PATH.write_text(pd.Series(report).to_json())

    return report


if __name__ == "__main__":
    metrics = train_model()
    print(metrics)
