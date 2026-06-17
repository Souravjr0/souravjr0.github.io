"""
ml_engine.py
XGBoost + LightGBM ensemble signal classifier for trading signals.
Trains on labeled OHLCV data and predicts BUY / SELL / HOLD with confidence.
"""

import os
import sys

# Dynamic path resolution to support restructured package layouts and nested submodules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) in ["core", "models", "execution", "discovery", "utils"] else current_dir
for subfolder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, subfolder))
sys.path.append(project_root)

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

try:
    import xgboost as xgb
except ImportError:
    xgb = None  # type: ignore[assignment]

try:
    import lightgbm as lgb
except ImportError:
    lgb = None  # type: ignore[assignment]

from feature_engineering import extract_features, get_feature_columns
from indicators import add_indicators
from config import ATR_PERIOD


# Label mapping: internal int class -> string
_CLASS_MAP = {0: "HOLD", 1: "BUY", 2: "SELL"}
_CLASS_INV = {"HOLD": 0, "BUY": 1, "SELL": -1}

# Min rows needed after NaN cleanup to attempt training
_MIN_TRAIN_ROWS = 60


# ---------------------------------------------------------------------------
# Labelling
# ---------------------------------------------------------------------------

def _create_labels(
    df: pd.DataFrame,
    lookforward: int = 5,
    threshold_pct: float = 1.5,
) -> pd.Series:
    """
    Create categorical target labels from forward returns.

    ATR-adaptive threshold: actual threshold is
        max(threshold_pct / 100, atr14 / close * 0.5)

    Returns a Series with values in {0, 1, 2}:
        1 = BUY  (forward return > threshold)
        2 = SELL (forward return < -threshold)
        0 = HOLD
    """
    close = df["close"].astype(float)
    fwd_ret = close.shift(-lookforward) / close - 1.0

    base_thr = threshold_pct / 100.0

    if "atr14" in df.columns:
        atr = df["atr14"].astype(float)
        adaptive_thr = (atr / close.replace(0, np.nan) * 0.5).fillna(base_thr)
        threshold = adaptive_thr.clip(lower=base_thr)
    else:
        threshold = pd.Series(base_thr, index=df.index)

    labels = pd.Series(0, index=df.index, dtype=int)
    labels[fwd_ret > threshold] = 1   # BUY
    labels[fwd_ret < -threshold] = 2  # SELL
    labels[fwd_ret.isna()] = -99      # sentinel for later drop

    return labels


# ---------------------------------------------------------------------------
# MLSignalEngine
# ---------------------------------------------------------------------------

class MLSignalEngine:
    """Ensemble XGBoost + LightGBM signal classifier."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        model_dir: str = "models",
    ) -> None:
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.model_dir = model_dir
        self._xgb_model: Optional[object] = None
        self._lgb_model: Optional[object] = None
        self._feature_cols: list[str] = []
        self._meta: dict = {}
        os.makedirs(self.model_dir, exist_ok=True)

    # -- path helpers --
    def _xgb_path(self) -> str:
        return os.path.join(self.model_dir, f"{self.symbol}_{self.timeframe}_xgb.joblib")

    def _lgb_path(self) -> str:
        return os.path.join(self.model_dir, f"{self.symbol}_{self.timeframe}_lgb.joblib")

    def _meta_path(self) -> str:
        return os.path.join(self.model_dir, f"{self.symbol}_{self.timeframe}_meta.joblib")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        df: pd.DataFrame,
        lookforward: int = 5,
        threshold_pct: float = 1.5,
    ) -> dict:
        """
        Full training pipeline.
        Returns a dict with accuracy, f1, classification_report on the validation set.
        """
        if xgb is None:
            raise ImportError("xgboost is not installed -- pip install xgboost")
        if lgb is None:
            raise ImportError("lightgbm is not installed -- pip install lightgbm")

        # 1. Add indicators if missing
        if "atr14" not in df.columns:
            df = add_indicators(df, atr_period=ATR_PERIOD)

        # 2. Feature engineering
        df = extract_features(df)

        # 3. Create labels
        df["_label"] = _create_labels(df, lookforward, threshold_pct)

        # 4. Determine feature columns (only keep those that actually exist)
        all_feats = get_feature_columns()
        feat_cols = [c for c in all_feats if c in df.columns]
        self._feature_cols = feat_cols

        # 5. Drop rows with sentinel label or NaN features
        mask = (df["_label"] != -99) & df[feat_cols].notna().all(axis=1)
        clean = df.loc[mask].copy()

        if len(clean) < _MIN_TRAIN_ROWS:
            return {
                "error": f"Not enough clean rows for training ({len(clean)} < {_MIN_TRAIN_ROWS})"
            }

        X = clean[feat_cols].values.astype(np.float32)
        y = clean["_label"].values.astype(int)

        # 6. Chronological split 80 / 20
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        if len(X_val) < 5:
            return {"error": "Validation set too small after split"}

        # Align classes so that both splits contain exactly {0, 1, 2}
        for split_name in ["train", "val"]:
            if split_name == "train":
                target_X, target_y = X_train, y_train
            else:
                target_X, target_y = X_val, y_val

            unique_classes = set(target_y)
            missing = {0, 1, 2} - unique_classes
            if missing:
                dummy_X = np.zeros((len(missing), target_X.shape[1]), dtype=np.float32)
                dummy_y = np.array(list(missing), dtype=int)
                if split_name == "train":
                    X_train = np.vstack([X_train, dummy_X])
                    y_train = np.concatenate([y_train, dummy_y])
                else:
                    X_val = np.vstack([X_val, dummy_X])
                    y_val = np.concatenate([y_val, dummy_y])

        # 7. Train XGBoost
        xgb_clf = xgb.XGBClassifier(
            max_depth=6,
            n_estimators=200,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multi:softprob",
            num_class=3,
            use_label_encoder=False,
            eval_metric="mlogloss",
            verbosity=0,
            random_state=42,
        )
        xgb_clf.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        # 8. Train LightGBM
        lgb_clf = lgb.LGBMClassifier(
            max_depth=6,
            n_estimators=200,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="multiclass",
            num_class=3,
            verbose=-1,
            random_state=42,
        )
        lgb_clf.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
        )

        # 9. Ensemble predictions on validation
        xgb_probs = xgb_clf.predict_proba(X_val)
        lgb_probs = lgb_clf.predict_proba(X_val)
        avg_probs = (xgb_probs + lgb_probs) / 2.0
        y_pred = avg_probs.argmax(axis=1)

        acc = float(accuracy_score(y_val, y_pred))
        f1 = float(f1_score(y_val, y_pred, average="weighted", zero_division=0))
        report = classification_report(
            y_val, y_pred,
            labels=[0, 1, 2],
            target_names=["HOLD", "BUY", "SELL"],
            zero_division=0,
        )

        # 10. Persist
        self._xgb_model = xgb_clf
        self._lgb_model = lgb_clf
        self._meta = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "feature_cols": feat_cols,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "train_rows": int(len(X_train)),
            "val_rows": int(len(X_val)),
            "accuracy": acc,
            "f1": f1,
        }
        joblib.dump(xgb_clf, self._xgb_path())
        joblib.dump(lgb_clf, self._lgb_path())
        joblib.dump(self._meta, self._meta_path())

        # Trigger PyTorch LSTM Deep Sequence Model training
        from lstm_classifier import train_lstm, TORCH_AVAILABLE
        if TORCH_AVAILABLE:
            try:
                print(f"[ml_engine] PyTorch active - training deep sequence LSTM model for {self.symbol}...")
                train_lstm(self.symbol, df)
            except Exception as e:
                print(f"[ml_engine] Deep sequence model training failed: {e}")

        metrics = {
            "accuracy": acc,
            "f1": f1,
            "classification_report": report,
            "train_rows": int(len(X_train)),
            "val_rows": int(len(X_val)),
            "label_distribution": {
                "HOLD": int((y == 0).sum()),
                "BUY": int((y == 1).sum()),
                "SELL": int((y == 2).sum()),
            },
        }
        return metrics

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, df: pd.DataFrame) -> tuple[str, float]:
        """
        Predict the signal for the most recent bar.
        Returns (signal, confidence) where signal is BUY/SELL/HOLD.
        """
        if self._xgb_model is None or self._lgb_model is None:
            if not self.load_model():
                return ("HOLD", 0.0)

        # Ensure indicators
        if "atr14" not in df.columns:
            df = add_indicators(df, atr_period=ATR_PERIOD)

        df = extract_features(df)

        feat_cols = self._feature_cols or self._meta.get("feature_cols", get_feature_columns())
        available = [c for c in feat_cols if c in df.columns]
        if not available:
            return ("HOLD", 0.0)

        last_row = df[available].iloc[[-1]].values.astype(np.float32)

        # Replace any residual NaN/inf with 0
        last_row = np.nan_to_num(last_row, nan=0.0, posinf=0.0, neginf=0.0)

        xgb_probs = self._xgb_model.predict_proba(last_row)  # type: ignore[union-attr]
        lgb_probs = self._lgb_model.predict_proba(last_row)  # type: ignore[union-attr]
        
        # Query PyTorch LSTM sequence probabilities dynamically
        lstm_probs = None
        from lstm_classifier import predict_lstm, TORCH_AVAILABLE
        if TORCH_AVAILABLE:
            try:
                lstm_pr, lstm_conf = predict_lstm(self.symbol, df)
                if lstm_conf > 0.0:
                    lstm_probs = lstm_pr.reshape(1, 3)
            except Exception as e:
                print(f"[ml_engine] Deep sequence model prediction failed: {e}")
                
        if lstm_probs is not None:
            avg_probs = (xgb_probs + lgb_probs + lstm_probs) / 3.0
        else:
            avg_probs = (xgb_probs + lgb_probs) / 2.0

        class_idx = int(avg_probs[0].argmax())
        confidence = float(avg_probs[0].max())

        signal = _CLASS_MAP.get(class_idx, "HOLD")

        # Low confidence gate
        if confidence < 0.60:
            signal = "HOLD"

        return (signal, round(confidence, 4))

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def load_model(self) -> bool:
        """Load models from disk. Returns False if files not found."""
        xp, lp, mp = self._xgb_path(), self._lgb_path(), self._meta_path()
        if not (os.path.isfile(xp) and os.path.isfile(lp) and os.path.isfile(mp)):
            return False
        try:
            self._xgb_model = joblib.load(xp)
            self._lgb_model = joblib.load(lp)
            self._meta = joblib.load(mp)
            self._feature_cols = self._meta.get("feature_cols", [])
            return True
        except Exception:
            return False

    def is_model_stale(self, max_age_days: int = 7) -> bool:
        """Return True if the saved model is older than *max_age_days*."""
        mp = self._meta_path()
        if not os.path.isfile(mp):
            return True
        try:
            age_sec = time.time() - os.path.getmtime(mp)
            return age_sec > max_age_days * 86400
        except Exception:
            return True

    def get_feature_importance(self) -> dict[str, float]:
        """Return top features ranked by averaged importance from both models."""
        if self._xgb_model is None or self._lgb_model is None:
            if not self.load_model():
                return {}

        feat_cols = self._feature_cols or self._meta.get("feature_cols", [])
        if not feat_cols:
            return {}

        # XGBoost importance
        try:
            xgb_imp = self._xgb_model.feature_importances_  # type: ignore[union-attr]
        except Exception:
            xgb_imp = np.zeros(len(feat_cols))

        # LightGBM importance
        try:
            lgb_imp = self._lgb_model.feature_importances_  # type: ignore[union-attr]
            # Normalize to same scale
            lgb_total = lgb_imp.sum()
            if lgb_total > 0:
                lgb_imp = lgb_imp / lgb_total
        except Exception:
            lgb_imp = np.zeros(len(feat_cols))

        # Normalize XGB
        xgb_total = xgb_imp.sum()
        if xgb_total > 0:
            xgb_imp = xgb_imp / xgb_total

        avg_imp = (xgb_imp + lgb_imp) / 2.0
        importance = {feat_cols[i]: float(avg_imp[i]) for i in range(len(feat_cols))}
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Data fetching helper for CLI
# ---------------------------------------------------------------------------

def _fetch_data_for_cli(symbol: str, timeframe: str, bars: int = 500) -> pd.DataFrame:
    """Fetch OHLCV data using the same pattern as unified_analyzer."""
    try:
        from exchange_client import get_spot_client
        from market_data import fetch_klines, klines_to_dataframe
        client = get_spot_client()
        klines = fetch_klines(client, symbol, timeframe, bars)
        df = klines_to_dataframe(klines)
        return df
    except Exception as e:
        print(f"[ml_engine] Failed to fetch data for {symbol}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ML Signal Engine - Train / Predict")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--predict", action="store_true", help="Get current signal prediction")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--timeframe", type=str, default="1h", help="Candle timeframe")
    parser.add_argument("--bars", type=int, default=500, help="Number of bars to fetch")
    parser.add_argument("--lookforward", type=int, default=5, help="Forward-looking window for labels")
    parser.add_argument("--threshold", type=float, default=1.5, help="Threshold pct for labeling")
    parser.add_argument("--model-dir", type=str, default="models", help="Directory to save models")
    args = parser.parse_args()

    engine = MLSignalEngine(
        symbol=args.symbol,
        timeframe=args.timeframe,
        model_dir=args.model_dir,
    )

    if args.train:
        print(f"[ml_engine] Fetching {args.bars} bars of {args.symbol} @ {args.timeframe} ...")
        df = _fetch_data_for_cli(args.symbol, args.timeframe, args.bars)
        if df.empty:
            print("[ml_engine] No data fetched. Aborting training.")
            sys.exit(1)

        print(f"[ml_engine] Got {len(df)} rows. Starting training ...")
        metrics = engine.train(df, lookforward=args.lookforward, threshold_pct=args.threshold)

        if "error" in metrics:
            print(f"[ml_engine] Training failed: {metrics['error']}")
            sys.exit(1)

        print(f"\n[ml_engine] Training complete for {args.symbol} @ {args.timeframe}")
        print(f"  Accuracy : {metrics['accuracy']:.4f}")
        print(f"  F1 score : {metrics['f1']:.4f}")
        print(f"  Train/Val: {metrics['train_rows']} / {metrics['val_rows']}")
        print(f"  Labels   : {metrics['label_distribution']}")
        print(f"\n{metrics['classification_report']}")

    elif args.predict:
        print(f"[ml_engine] Fetching latest {args.bars} bars of {args.symbol} @ {args.timeframe} ...")
        df = _fetch_data_for_cli(args.symbol, args.timeframe, args.bars)
        if df.empty:
            print("[ml_engine] No data fetched. Aborting prediction.")
            sys.exit(1)

        signal, confidence = engine.predict(df)
        print(f"\n[ml_engine] Signal for {args.symbol} @ {args.timeframe}")
        print(f"  Signal     : {signal}")
        print(f"  Confidence : {confidence:.2%}")

        if engine.is_model_stale():
            print("  [!] Warning: model is stale (>7 days old). Consider re-training.")

        importance = engine.get_feature_importance()
        if importance:
            print("\n  Top features by importance:")
            for i, (feat, imp) in enumerate(list(importance.items())[:10]):
                print(f"    {i+1}. {feat}: {imp:.4f}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
