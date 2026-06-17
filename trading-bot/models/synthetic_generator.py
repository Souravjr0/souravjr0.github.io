"""
synthetic_generator.py
Merton Jump-Diffusion Stochastic Candle Generator for Black-Swan Stress Testing.
Combines Geometric Brownian Motion (GBM) with Poisson jump processes.
"""

import numpy as np
import pandas as pd

def generate_synthetic_data(
    df: pd.DataFrame, 
    num_bars: int = 200, 
    crash_probability: float = 0.05
) -> pd.DataFrame:
    """
    Generates synthetic high-stress market continuations using Merton Jump-Diffusion.
    Simulates sudden price gaps, Poisson-distributed negative jumps, and volume panics.
    """
    if df.empty or len(df) < 5:
        return df.copy()

    # Sort and reset index to ensure clean chronology
    df_sorted = df.copy().reset_index(drop=True)
    
    # Calculate historical parameters from close prices
    close_prices = df_sorted["close"].values
    log_returns = np.log(close_prices[1:] / close_prices[:-1])
    
    # Estimate historical drift (mu) and volatility (sigma)
    mu = float(np.mean(log_returns)) if len(log_returns) > 0 else 0.0
    sigma = float(np.std(log_returns)) if len(log_returns) > 0 else 0.02
    sigma = max(sigma, 0.005) # Prevent zero volatility

    # Initialize synthetic arrays starting from the last close
    last_close = float(close_prices[-1])
    last_volume = float(df_sorted["volume"].iloc[-1]) if "volume" in df_sorted.columns else 1000.0
    avg_volume = float(df_sorted["volume"].mean()) if "volume" in df_sorted.columns else 1000.0
    
    synth_closes = []
    current_price = last_close
    
    # Merton Jump-Diffusion parameters:
    # Lambda = expected number of jumps per unit step
    jump_lambda = crash_probability 
    # Mean of log jump size (negative for crashes)
    jump_mu = -0.08 
    # Volatility of log jump size
    jump_sigma = 0.03 

    np.random.seed(42) # Safe deterministic seed for testing repeatability
    
    for _ in range(num_bars):
        # 1. Standard Brownian Motion component (GBM)
        dz = np.random.normal(0, 1)
        gbm_part = (mu - 0.5 * (sigma ** 2)) + sigma * dz
        
        # 2. Poisson Jump component
        num_jumps = np.random.poisson(jump_lambda)
        jump_part = 0.0
        if num_jumps > 0:
            # Sum of normal jumps
            jump_part = np.sum(np.random.normal(jump_mu, jump_sigma, num_jumps))
            
        # Update current price using the combined exponential returns
        current_price = current_price * np.exp(gbm_part + jump_part)
        current_price = max(current_price, 1e-4) # Bounded above zero
        
        synth_closes.append((current_price, num_jumps > 0))

    # 3. Reconstruct realistic OHLCV candle structures
    synth_records = []
    prev_close = last_close
    
    for i, (close_val, did_crash) in enumerate(synth_closes):
        # Open price has a small random gap from previous close
        open_val = prev_close * (1.0 + np.random.normal(0, 0.001))
        
        # Determine body range
        body_min = min(open_val, close_val)
        body_max = max(open_val, close_val)
        
        # Generate realistic shadows (wicks)
        wick_up_mean = 0.002 if not did_crash else 0.001
        wick_down_mean = 0.002 if not did_crash else 0.015  # Heavy downside wick in crashes
        
        high_val = body_max * (1.0 + abs(np.random.normal(0, wick_up_mean)))
        low_val = body_min * (1.0 - abs(np.random.normal(0, wick_down_mean)))
        
        # Double check bounds compliance
        high_val = max(high_val, open_val, close_val)
        low_val = min(low_val, open_val, close_val)
        
        # Volume profile matching: crash bars have massive volume spikes (panic selling)
        if did_crash:
            volume_val = avg_volume * np.random.uniform(3.5, 6.0)
        else:
            volume_val = avg_volume * np.random.uniform(0.6, 1.4)
            
        synth_records.append({
            "open": float(open_val),
            "high": float(high_val),
            "low": float(low_val),
            "close": float(close_val),
            "volume": float(volume_val)
        })
        prev_close = close_val
        
    synth_df = pd.DataFrame(synth_records)
    
    # 4. Handle timeframes and timestamps safely
    if "timestamp" in df_sorted.columns:
        last_time = df_sorted["timestamp"].iloc[-1]
        # Auto-detect average time delta to project future timestamps
        if len(df_sorted) > 1:
            try:
                time_delta = df_sorted["timestamp"].iloc[1] - df_sorted["timestamp"].iloc[0]
            except Exception:
                time_delta = pd.Timedelta(hours=1)
        else:
            time_delta = pd.Timedelta(hours=1)
            
        future_times = [last_time + (i + 1) * time_delta for i in range(num_bars)]
        synth_df["timestamp"] = future_times

    # Maintain existing non-OHLCV metadata columns by copying them forward
    for col in df_sorted.columns:
        if col not in ["open", "high", "low", "close", "volume", "timestamp"]:
            synth_df[col] = df_sorted[col].iloc[-1]
            
    # Concatenate the original historical dataset with the synthetic high-stress dataset
    final_df = pd.concat([df_sorted, synth_df], ignore_index=True)
    return final_df
