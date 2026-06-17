#!/usr/bin/env python3
"""
PyTorch LSTM Deep Learning Classifier for trading signals.
Performs rolling sequence modeling on time-series technical/quant features.
Provides elegant, zero-crash fallback wrappers when PyTorch is not pre-installed.
"""

import os
import sys

# Dynamic path resolution to support restructured package layouts and nested submodules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) in ["core", "models", "execution", "discovery", "utils"] else current_dir
for subfolder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, subfolder))
sys.path.append(project_root)

import json
import numpy as np
import pandas as pd

# Core configurations
from config import LSTM_EPOCHS, LSTM_BATCH_SIZE, LSTM_LOOKBACK, ML_MODEL_DIR

# Resilient PyTorch import checker
TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    nn = None     # type: ignore
    optim = None  # type: ignore
    TensorDataset = None # type: ignore
    DataLoader = None # type: ignore

class LSTMClassifierModel:
    """Minimal PyTorch LSTM Architecture wrapper. Evaluates sequence data."""
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2, output_dim: int = 3):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.output_dim = output_dim
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if TORCH_AVAILABLE:
            class PyTorchLSTM(nn.Module):
                def __init__(self, in_d, hid_d, num_l, out_d):
                    super().__init__()
                    self.lstm = nn.LSTM(in_d, hid_d, num_l, batch_first=True)
                    self.dropout = nn.Dropout(0.2)
                    self.fc = nn.Linear(hid_d, out_d)
                    
                def forward(self, x):
                    # x shape: [batch_size, seq_len, input_dim]
                    out, (hn, cn) = self.lstm(x)
                    # Use last sequence element output
                    last_out = out[:, -1, :]
                    last_out = self.dropout(last_out)
                    logits = self.fc(last_out)
                    return logits # Raw logits, CrossEntropyLoss does Softmax internally
            
            self.model = PyTorchLSTM(input_dim, hidden_dim, num_layers, output_dim).to(self.device)
        else:
            self.model = None

def prepare_sequences(df: pd.DataFrame, lookback: int = 30) -> tuple[np.ndarray, np.ndarray]:
    """Segment historical feature rows into overlapping sliding sequence matrices."""
    # Columns to use as time-series features
    feature_cols = [
        "feat_ret_1", "feat_vol_5", "feat_obv_slope", 
        "feat_hl_range_ratio", "feat_close_position", 
        "feat_upper_shadow", "feat_lower_shadow", "feat_dist_ema20"
    ]
    
    # Ensure columns exist, fall back to basic close/volume indicators if missing
    existing_cols = [c for c in feature_cols if c in df.columns]
    if len(existing_cols) < 3:
        # Fallback raw features
        df["feat_ret_1"] = df["close"].pct_change()
        df["feat_vol_5"] = df["feat_ret_1"].rolling(5).std()
        df["feat_close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"])
        df.fillna(method="bfill", inplace=True)
        df.fillna(0.0, inplace=True)
        existing_cols = ["feat_ret_1", "feat_vol_5", "feat_close_position"]
        
    X_raw = df[existing_cols].values
    
    # Labeling target: positive forward return = 1 (BUY), negative = -1/2 (SELL), neutral = 0 (HOLD)
    # Target shift (lookforward = 5 bars)
    fwd_ret = (df["close"].shift(-5) / df["close"]) - 1.0
    y_raw = np.zeros(len(df), dtype=int)
    y_raw[fwd_ret > 0.015] = 1 # BUY
    y_raw[fwd_ret < -0.015] = 2 # SELL (CrossEntropy expects index 0,1,2 - map SELL to index 2)
    
    # Generate sliding sequence windows
    X_seq = []
    y_seq = []
    
    for i in range(len(df) - lookback - 5):
        X_seq.append(X_raw[i : i + lookback])
        y_seq.append(y_raw[i + lookback - 1])
        
    return np.array(X_seq), np.array(y_seq)

def train_lstm(symbol: str, df: pd.DataFrame) -> dict:
    """Train sequential LSTM classifier model using PyTorch."""
    if not TORCH_AVAILABLE:
        print("[LSTM Engine] PyTorch (torch) is not installed. Skipping deep learning training.")
        return {"error": "PyTorch not installed"}
        
    try:
        os.makedirs(ML_MODEL_DIR, exist_ok=True)
        X, y = prepare_sequences(df, lookback=LSTM_LOOKBACK)
        if len(X) < 40:
            return {"error": f"Insufficient sequences ({len(X)}) for deep learning"}
            
        input_dim = X.shape[2]
        classifier = LSTMClassifierModel(input_dim)
        
        # Convert to tensor loaders
        X_tensor = torch.tensor(X, dtype=torch.float32).to(classifier.device)
        y_tensor = torch.tensor(y, dtype=torch.long).to(classifier.device)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=LSTM_BATCH_SIZE, shuffle=True)
        
        # Loss and Optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(classifier.model.parameters(), lr=0.005)
        
        print(f"[LSTM Engine] Training deep sequence model for {symbol} ({LSTM_EPOCHS} epochs, sequence_dim={input_dim})...")
        classifier.model.train()
        
        for epoch in range(LSTM_EPOCHS):
            running_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                out = classifier.model(batch_x)
                loss = criterion(out, batch_y)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()
                
        # Save model state dictionary
        model_path = os.path.join(ML_MODEL_DIR, f"{symbol.upper()}_lstm.pt")
        torch.save(classifier.model.state_dict(), model_path)
        print(f"[LSTM Engine] Model state saved successfully to {model_path}")
        
        return {"status": "trained", "input_dim": input_dim, "loss": running_loss / len(loader)}
    except Exception as e:
        print(f"[LSTM Engine] Training exception: {e}")
        return {"error": str(e)}

def predict_lstm(symbol: str, df: pd.DataFrame) -> tuple[np.ndarray, float]:
    """Generate probabilistic deep sequence predictions using loaded PyTorch LSTM model weights."""
    symbol_upper = symbol.strip().upper()
    fallback_probs = np.array([0.0, 1.0, 0.0]) # fallback standard HOLD index 1
    
    if not TORCH_AVAILABLE:
        return fallback_probs, 0.0
        
    model_path = os.path.join(ML_MODEL_DIR, f"{symbol_upper}_lstm.pt")
    if not os.path.exists(model_path):
        return fallback_probs, 0.0
        
    try:
        X, _ = prepare_sequences(df, lookback=LSTM_LOOKBACK)
        if len(X) == 0:
            return fallback_probs, 0.0
            
        # Select latest sequence
        last_seq = X[-1:]
        input_dim = last_seq.shape[2]
        
        classifier = LSTMClassifierModel(input_dim)
        classifier.model.load_state_dict(torch.load(model_path, map_location=classifier.device))
        classifier.model.eval()
        
        with torch.no_grad():
            x_tensor = torch.tensor(last_seq, dtype=torch.float32).to(classifier.device)
            logits = classifier.model(x_tensor)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            
        # Probabilities layout: [0 -> HOLD, 1 -> BUY, 2 -> SELL]
        # Our return array: [0 (HOLD), 1 (BUY), 2 (SELL)]
        formatted_probs = np.array([probs[0], probs[1], probs[2]])
        best_idx = np.argmax(formatted_probs)
        confidence = float(formatted_probs[best_idx])
        
        return formatted_probs, confidence
    except Exception as e:
        print(f"[LSTM Engine] Prediction exception for {symbol_upper}: {e}")
        return fallback_probs, 0.0

if __name__ == '__main__':
    # Dry run model initialization and sequences parsing
    print(f"PyTorch LSTM Neural Network Module. PyTorch Active: {TORCH_AVAILABLE}")
    dummy_data = []
    for i in range(100):
        dummy_data.append({
            "close": 100.0 + np.sin(i / 5.0) + np.random.normal(0, 0.5),
            "high": 101.0, "low": 99.0, "open": 100.0, "volume": 1000.0
        })
    df = pd.DataFrame(dummy_data)
    print("Testing sequence prep on dummy data...")
    X, y = prepare_sequences(df, lookback=10)
    print(f"Prepared sequence shape: {X.shape} | Targets: {y.shape}")
    if TORCH_AVAILABLE:
        print("Running PyTorch compile dry-run test...")
        results = train_lstm("TEST", df)
        print("Train result:", results)
        probs, conf = predict_lstm("TEST", df)
        print("Prediction result:", probs, "Confidence:", conf)
