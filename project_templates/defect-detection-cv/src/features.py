from __future__ import annotations

import cv2
import numpy as np


def extract_edge_features(image: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(image, 50, 150)
    edge_density = edges.mean() / 255.0
    return np.array([edge_density], dtype=np.float32)
