from __future__ import annotations

import json
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "model.joblib"
LABELS_PATH = PROJECT_ROOT / "artifacts" / "labels.json"


def load_model():
    return joblib.load(MODEL_PATH)


def load_labels():
    return json.loads(LABELS_PATH.read_text())


def predict_topic(text: str) -> dict:
    model = load_model()
    labels = load_labels()
    pred = int(model.predict([text])[0])
    return {"label": labels[pred], "label_id": pred}
