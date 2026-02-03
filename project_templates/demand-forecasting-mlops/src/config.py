from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "sales.csv"
MODEL_PATH = PROJECT_ROOT / "artifacts" / "model.joblib"
METRICS_PATH = PROJECT_ROOT / "artifacts" / "metrics.json"
DEFAULT_LAGS = 7
