from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import joblib

from .features import extract_edge_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "model.joblib"


def predict_image(image_path: str) -> dict:
    model = joblib.load(MODEL_PATH)
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    features = extract_edge_features(img).reshape(1, -1)
    prob = float(model.predict_proba(features)[0][1])
    label = int(prob >= 0.5)
    return {"label": label, "defect_probability": prob}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    result = predict_image(args.image)
    print(result)


if __name__ == "__main__":
    main()
