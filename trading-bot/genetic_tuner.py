#!/usr/bin/env python3
"""
Genetic Algorithm Auto-Tuner for Trading Bot.
Optimizes strategy hyperparameters (EMA Fast/Slow, Kalman Filter Q/R, ATR Stop/Take multipliers)
using a high-performance numpy-vectorized genetic selection pipeline.
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
import time
import argparse
import numpy as np
import pandas as pd

from config import TUNED_PARAMS_PATH, WATCHLIST
from indicators import add_indicators
from unified_analyzer import fetch_data_unified
import quant_engine

class GeneticTuner:
    def __init__(self, symbol: str, timeframe: str = "1h", pop_size: int = 40, generations: int = 10):
        self.symbol = symbol.strip().upper()
        self.timeframe = timeframe
        self.pop_size = pop_size
        self.generations = generations
        self.df = pd.DataFrame()

    def load_data(self) -> bool:
        """Load 500 bars of historical data for calibration."""
        print(f"[Genetic Tuner] Loading historical {self.timeframe} data for {self.symbol}...")
        self.df = fetch_data_unified(self.symbol, self.timeframe, 500)
        if self.df.empty or len(self.df) < 100:
            print(f"[Genetic Tuner] Insufficient data ({len(self.df)} bars) for {self.symbol}.")
            return False
        print(f"[Genetic Tuner] Loaded {len(self.df)} bars successfully.")
        return True

    def _vectorized_backtest(self, ema_fast: int, ema_slow: int, q_noise: float, r_noise: float, sl_mult: float, tp_mult: float) -> float:
        """Run rapid, low-level numpy backtest on loaded series to calculate fitness score."""
        close = self.df["close"].values
        high = self.df["high"].values
        low = self.df["low"].values
        
        # 1. EMA indicators
        close_series = pd.Series(close)
        ema_f = close_series.ewm(span=ema_fast, adjust=False).mean().values
        ema_s = close_series.ewm(span=ema_slow, adjust=False).mean().values
        
        # 2. Kalman filter इनोवेशन z-score
        kf_zscores = np.zeros_like(close)
        x_est = close[0]
        p_est = 1.0
        for i in range(1, len(close)):
            # Predict
            p_pred = p_est + q_noise
            # Update
            innov = close[i] - x_est
            s_cov = p_pred + r_noise
            k_gain = p_pred / s_cov
            x_est = x_est + k_gain * innov
            p_est = (1.0 - k_gain) * p_pred
            kf_zscores[i] = innov / np.sqrt(s_cov) if s_cov > 0 else 0.0

        # 3. Simulated signals
        # Buy: EMA Crossover + Kalman Innovation < -1.5 (undervalued)
        # Sell: EMA Crossunder + Kalman Innovation > 1.5 (overvalued)
        signals = np.zeros_like(close)
        for i in range(20, len(close)):
            if ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1] and kf_zscores[i] < -1.0:
                signals[i] = 1 # BUY
            elif ema_f[i] < ema_s[i] and ema_f[i-1] >= ema_s[i-1] and kf_zscores[i] > 1.0:
                signals[i] = -1 # SELL
                
        # 4. Compute performance
        trades = []
        in_pos = False
        pos_side = 0
        entry_price = 0.0
        atr = close_series.rolling(14).std().values # standard dev proxy for atr speedup
        atr[np.isnan(atr)] = atr[~np.isnan(atr)][0] if len(atr[~np.isnan(atr)]) > 0 else 1.0
        
        for i in range(20, len(close)):
            if not in_pos:
                if signals[i] == 1: # BUY
                    in_pos = True
                    pos_side = 1
                    entry_price = close[i]
                elif signals[i] == -1: # SELL
                    in_pos = True
                    pos_side = -1
                    entry_price = close[i]
            else:
                # Calculate pnl
                current_pnl = (close[i] - entry_price) / entry_price if pos_side == 1 else (entry_price - close[i]) / entry_price
                sl_barrier = -(atr[i] * sl_mult) / entry_price
                tp_barrier = (atr[i] * tp_mult) / entry_price
                
                # Check exit
                if current_pnl <= sl_barrier or current_pnl >= tp_barrier:
                    trades.append(current_pnl)
                    in_pos = False
                    pos_side = 0
                elif (pos_side == 1 and signals[i] == -1) or (pos_side == -1 and signals[i] == 1):
                    # Signal reversal exit
                    trades.append(current_pnl)
                    in_pos = False
                    pos_side = 0

        if not trades:
            return -100.0 # Heavy penalty for zero execution

        trades = np.array(trades)
        wins = trades[trades > 0]
        losses = trades[trades <= 0]
        
        win_rate = len(wins) / len(trades) if len(trades) > 0 else 0.0
        gross_profits = np.sum(wins) if len(wins) > 0 else 0.0
        gross_losses = np.abs(np.sum(losses)) if len(losses) > 0 else 0.0
        
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else gross_profits * 50.0
        max_drawdown = np.abs(np.min(trades)) if len(trades) > 0 else 0.0
        
        # Fitness formula: Win Rate * Profit Factor / (1 + Drawdown)
        fitness = (win_rate * 100.0) * profit_factor / (1.0 + max_drawdown)
        return float(fitness)

    def tune(self) -> dict:
        """Run genetic optimizer generations."""
        if not self.load_data():
            return {}

        # Gene bounds: [ema_fast, ema_slow, q_noise, r_noise, sl_mult, tp_mult]
        bounds = [
            (8, 25),      # Fast EMA
            (26, 90),     # Slow EMA
            (1e-5, 1e-2), # Kalman Q
            (1e-3, 0.5),  # Kalman R
            (1.5, 3.5),   # ATR SL Multiplier
            (2.0, 5.0)    # ATR TP Multiplier
        ]

        # Initialize random population
        pop = []
        for _ in range(self.pop_size):
            ind = [
                int(np.random.randint(bounds[0][0], bounds[0][1])),
                int(np.random.randint(bounds[1][0], bounds[1][1])),
                float(np.random.uniform(bounds[2][0], bounds[2][1])),
                float(np.random.uniform(bounds[3][0], bounds[3][1])),
                float(np.random.uniform(bounds[4][0], bounds[4][1])),
                float(np.random.uniform(bounds[5][0], bounds[5][1]))
            ]
            pop.append(ind)

        best_ind = None
        best_fit = -float('inf')

        for gen in range(self.generations):
            scores = []
            for ind in pop:
                score = self._vectorized_backtest(
                    ema_fast=ind[0], ema_slow=ind[1],
                    q_noise=ind[2], r_noise=ind[3],
                    sl_mult=ind[4], tp_mult=ind[5]
                )
                scores.append(score)

            scores = np.array(scores)
            best_idx = np.argmax(scores)
            if scores[best_idx] > best_fit:
                best_fit = scores[best_idx]
                best_ind = pop[best_idx]

            print(f"  Generation {gen+1}/{self.generations} - Best Fitness: {best_fit:.2f}")

            # Selection: Tournament
            next_pop = []
            curr_size = len(pop)
            for _ in range((self.pop_size + 1) // 2):
                # Tournament 1
                t1_idxs = np.random.choice(curr_size, min(3, curr_size), replace=False)
                winner1 = pop[t1_idxs[np.argmax(scores[t1_idxs])]]
                # Tournament 2
                t2_idxs = np.random.choice(curr_size, min(3, curr_size), replace=False)
                winner2 = pop[t2_idxs[np.argmax(scores[t2_idxs])]]

                # Crossover: Single Point Blend
                child1, child2 = list(winner1), list(winner2)
                if np.random.rand() < 0.8:
                    c_point = np.random.randint(1, len(bounds))
                    child1[c_point:], child2[c_point:] = child2[c_point:], child1[c_point:]

                # Mutation
                for child in [child1, child2]:
                    if np.random.rand() < 0.2:
                        m_point = np.random.randint(len(bounds))
                        b = bounds[m_point]
                        if m_point in (0, 1):
                            child[m_point] = int(np.random.randint(b[0], b[1]))
                        else:
                            child[m_point] = float(np.random.uniform(b[0], b[1]))

                next_pop.extend([child1, child2])

            pop = next_pop[:self.pop_size]

        if best_ind is None:
            return {}

        results = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "ema_fast": int(best_ind[0]),
            "ema_slow": int(best_ind[1]),
            "kalman_q": float(best_ind[2]),
            "kalman_r": float(best_ind[3]),
            "atr_multiplier_sl": round(float(best_ind[4]), 4),
            "atr_multiplier_tp": round(float(best_ind[5]), 4),
            "opt_fitness": round(best_fit, 4),
            "optimized_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }

        print(f"\n[Genetic Tuner] Calibrated DNA parameters found:")
        print(json.dumps(results, indent=2))
        return results

def save_tuned_parameters(params: dict):
    """Save calibrated hyperparameter values to dynamic parameters JSON file."""
    try:
        data = {}
        if os.path.exists(TUNED_PARAMS_PATH):
            with open(TUNED_PARAMS_PATH, "r") as f:
                data = json.load(f)
        
        data[params["symbol"]] = params
        with open(TUNED_PARAMS_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Genetic Tuner] Saved optimization results for {params['symbol']} to {TUNED_PARAMS_PATH}")
    except Exception as e:
        print(f"[Genetic Tuner] Failed to write tuned parameters to file: {e}")

def load_tuned_parameters(symbol: str) -> dict | None:
    """Read tuned parameters from JSON, returning None if missing."""
    try:
        symbol_upper = symbol.strip().upper()
        if os.path.exists(TUNED_PARAMS_PATH):
            with open(TUNED_PARAMS_PATH, "r") as f:
                data = json.load(f)
                return data.get(symbol_upper)
    except Exception:
        pass
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Institutional Genetic Auto-Tuner")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Target symbol for genetic calibration")
    parser.add_argument("--timeframe", type=str, default="15m", help="Timeframe to optimize parameters on")
    parser.add_argument("--pop-size", type=int, default=30, help="GA population size")
    parser.add_argument("--generations", type=int, default=5, help="Number of GA generations")
    args = parser.parse_args()

    tuner = GeneticTuner(args.symbol, args.timeframe, args.pop_size, args.generations)
    tuned = tuner.tune()
    if tuned:
        save_tuned_parameters(tuned)
