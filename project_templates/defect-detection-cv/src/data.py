from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _draw_base_image(size: int = 128) -> np.ndarray:
    img = np.full((size, size), 180, dtype=np.uint8)
    cv2.circle(img, (size // 2, size // 2), size // 3, 200, -1)
    return img


def _add_defect(img: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x1, y1 = rng.integers(10, 118, size=2)
    x2, y2 = rng.integers(10, 118, size=2)
    defected = img.copy()
    cv2.line(defected, (int(x1), int(y1)), (int(x2), int(y2)), 50, 2)
    return defected


def generate_dataset(samples: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx in range(samples):
        label = int(idx % 2 == 1)
        img = _draw_base_image()
        if label == 1:
            img = _add_defect(img, seed=int(rng.integers(1, 10000)))
        image_path = DATA_DIR / f"sample_{idx:04d}.png"
        cv2.imwrite(str(image_path), img)
        rows.append({"image_path": str(image_path), "label": label})

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "labels.csv", index=False)
    return df
