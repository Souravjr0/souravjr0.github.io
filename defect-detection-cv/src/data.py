from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _draw_defect(image: np.ndarray, rng: np.random.Generator) -> None:
    h, w = image.shape
    x1, y1 = rng.integers(5, w - 5), rng.integers(5, h - 5)
    x2, y2 = rng.integers(5, w - 5), rng.integers(5, h - 5)
    cv2.line(image, (x1, y1), (x2, y2), color=255, thickness=2)


def _draw_ok(image: np.ndarray) -> None:
    pass


def generate_dataset(samples: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(samples):
        image = np.zeros((64, 64), dtype=np.uint8)
        label = int(rng.random() < 0.5)
        if label == 1:
            _draw_defect(image, rng)
        else:
            _draw_ok(image)

        filename = DATA_DIR / f"sample_{i:04d}.png"
        cv2.imwrite(str(filename), image)
        records.append({"image_path": str(filename), "label": label})

    df = pd.DataFrame(records)
    df.to_csv(DATA_DIR / "labels.csv", index=False)
    return df