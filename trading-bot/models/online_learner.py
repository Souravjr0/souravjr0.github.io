"""
online_learner.py
Adaptive Online Model Controller using native Multi-Class Softmax SGD Regression.
Learns incrementally from real-time data streams to combat market concept drift.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Optional, Tuple

class OnlineLearner:
    def __init__(self, symbol: str, timeframe: str, learning_rate: float = 0.02, model_dir: str = "models"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.lr_base = learning_rate
        self.lr = learning_rate
        self.model_dir = model_dir
        
        # We target 3 classes: 0 -> HOLD, 1 -> BUY (LONG), 2 -> SELL (SHORT)
        self.num_classes = 3
        
        # Loaded features list
        from feature_engineering import get_feature_columns
        self.feature_cols = get_feature_columns()
        self.num_features = len(self.feature_cols)
        
        # Initialize weights and biases
        self.weights = np.zeros((self.num_classes, self.num_features))
        self.biases = np.zeros(self.num_classes)
        
        # Feature scaling parameters (online rolling mean and std proxy)
        self.feat_mean = np.zeros(self.num_features)
        self.feat_var = np.ones(self.num_features)
        self.count = 0
        
        # Drift detection tracking
        self.accuracy_window = []
        self.window_size = 30
        self.drift_detected = False
        
        self.model_path = os.path.join(self.model_dir, f"{self.symbol}_{self.timeframe}_online.json")
        self.load_model()

    def _update_scaling(self, x: np.ndarray):
        """Welford's algorithm for online updates of mean and variance."""
        self.count += 1
        delta = x - self.feat_mean
        self.feat_mean += delta / self.count
        delta2 = x - self.feat_mean
        self.feat_var += delta * delta2

    def _scale(self, x: np.ndarray) -> np.ndarray:
        """Standardize feature vector using online parameters."""
        std = np.sqrt(self.feat_var / max(self.count, 1))
        std[std < 1e-8] = 1.0  # Prevent division by zero
        return (x - self.feat_mean) / std

    def _softmax(self, z: np.ndarray) -> np.ndarray:
        """Stable softmax calculation."""
        exp_z = np.exp(z - np.max(z))
        return exp_z / np.sum(exp_z)

    def predict_online(self, features_dict: dict) -> Tuple[str, float]:
        """Generate prediction ('BUY'/'SELL'/'HOLD') and confidence score."""
        x = np.array([float(features_dict.get(col, 0.0)) for col in self.feature_cols])
        x_scaled = self._scale(x)
        
        # Compute activations
        z = np.dot(self.weights, x_scaled) + self.biases
        probs = self._softmax(z)
        
        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])
        
        mapping = {0: "HOLD", 1: "BUY", 2: "SELL"}
        return mapping[pred_class], confidence

    def update_online(self, features_dict: dict, label: int):
        """
        Incrementally update the Softmax Logistic Regression weights using SGD.
        label: 0 -> HOLD, 1 -> BUY (LONG), -1/2 -> SELL (SHORT)
        """
        # Map label to internal classes
        if label == -1:
            y = 2  # SELL
        elif label in {0, 1, 2}:
            y = int(label)
        else:
            return  # Invalid label
            
        x = np.array([float(features_dict.get(col, 0.0)) for col in self.feature_cols])
        
        # Update feature scaling statistics
        self._update_scaling(x)
        x_scaled = self._scale(x)
        
        # Forward pass
        z = np.dot(self.weights, x_scaled) + self.biases
        probs = self._softmax(z)
        
        # Compute predicted class and track accuracy for drift detection
        pred_class = int(np.argmax(probs))
        is_correct = (pred_class == y)
        self.accuracy_window.append(float(is_correct))
        if len(self.accuracy_window) > self.window_size:
            self.accuracy_window.pop(0)
            
        # Detect concept drift (accuracy below 50% over rolling window)
        if len(self.accuracy_window) >= 15:
            avg_acc = np.mean(self.accuracy_window)
            if avg_acc < 0.50:
                if not self.drift_detected:
                    print(f"[Online Learner] [WARNING] Concept Drift detected for {self.symbol} (Accuracy: {avg_acc:.2%}). Boosting learning rate.")
                    self.drift_detected = True
                self.lr = self.lr_base * 2.5  # Increase adaptation rate
            else:
                self.drift_detected = False
                self.lr = self.lr_base
                
        # SGD Weight Update: gradient = (probs - target) * x
        target = np.zeros(self.num_classes)
        target[y] = 1.0
        
        error = probs - target
        
        # Update weights and biases
        self.weights -= self.lr * np.outer(error, x_scaled)
        self.biases -= self.lr * error
        
        # Periodically save model weights
        if self.count % 10 == 0:
            self.save_model()

    def save_model(self):
        """Save standard JSON weights structure to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        model_data = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "weights": self.weights.tolist(),
            "biases": self.biases.tolist(),
            "feat_mean": self.feat_mean.tolist(),
            "feat_var": self.feat_var.tolist(),
            "count": self.count
        }
        try:
            with open(self.model_path, "w") as f:
                json.dump(model_data, f)
        except Exception:
            pass

    def load_model(self) -> bool:
        """Load weights structure from disk."""
        if not os.path.exists(self.model_path):
            return False
        try:
            with open(self.model_path, "r") as f:
                data = json.load(f)
            self.weights = np.array(data["weights"])
            self.biases = np.array(data["biases"])
            self.feat_mean = np.array(data["feat_mean"])
            self.feat_var = np.array(data["feat_var"])
            self.count = int(data["count"])
            return True
        except Exception:
            return False
