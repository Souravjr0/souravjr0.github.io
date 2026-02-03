from __future__ import annotations

import joblib

from .config import MODEL_PATH
from .features import build_feature_row


def load_model():
    return joblib.load(MODEL_PATH)


def predict_next(recent_values: list[float]):
    model = load_model()
    features = build_feature_row(recent_values)
    return float(model.predict(features)[0])