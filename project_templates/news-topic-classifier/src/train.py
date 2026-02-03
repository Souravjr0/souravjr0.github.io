from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.datasets import fetch_20newsgroups
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = PROJECT_ROOT / "artifacts"
MODEL_PATH = ARTIFACTS / "model.joblib"
LABELS_PATH = ARTIFACTS / "labels.json"
REPORT_PATH = ARTIFACTS / "report.json"


def train_model(random_state: int = 42) -> dict:
    dataset = fetch_20newsgroups(subset="all", remove=("headers", "footers", "quotes"))
    X_train, X_test, y_train, y_test = train_test_split(
        dataset.data,
        dataset.target,
        test_size=0.2,
        random_state=random_state,
        stratify=dataset.target,
    )

    model = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(max_features=50000, ngram_range=(1, 2))),
            ("clf", LinearSVC()),
        ]
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    report = classification_report(y_test, preds, output_dict=True)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    LABELS_PATH.write_text(json.dumps(dataset.target_names, indent=2))
    REPORT_PATH.write_text(json.dumps(report, indent=2))

    return {
        "labels": dataset.target_names,
        "samples": len(dataset.data),
    }


if __name__ == "__main__":
    info = train_model()
    print(info)
