"""
wfo_engine.py
Walk-Forward Optimization (WFO) Engine.
Splits historical candles into rolling In-Sample (training) and Out-of-Sample (testing) windows.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any
from indicators import add_indicators
from strategies import evaluate_latest_signals

# Silence standard pandas chained assignment warnings for optimal loop execution speed
pd.options.mode.chained_assignment = None

def run_wfo_optimization(
    df: pd.DataFrame, 
    in_sample_pct: float = 0.70,
    fee_rate: float = 0.001
) -> dict:
    """
    Executes a Walk-Forward sliding-window optimization on historical OHLCV.
    Grid-searches the optimal EMA Fast/Slow pairs on In-Sample data,
    then evaluates their out-of-sample durability on unseen data.
    """
    if df.empty or len(df) < 50:
        return {
            "status": "error",
            "message": f"Insufficient data candles for WFO calibration ({len(df)} < 50)"
        }

    # 1. Split data into In-Sample and Out-of-Sample blocks
    split_idx = int(len(df) * in_sample_pct)
    df_in = df.iloc[:split_idx].copy().reset_index(drop=True)
    df_out = df.iloc[split_idx:].copy().reset_index(drop=True)
    
    # 2. Define Parameter Search Space for the Grid
    ema_fast_space = [10, 15, 20, 25]
    ema_slow_space = [40, 50, 60, 70]
    
    best_in_sample_pnl = -999999.0
    best_params = {"ema_fast": 20, "ema_slow": 50}
    
    # 3. Grid Search Sweep over In-Sample window
    for fast in ema_fast_space:
        for slow in ema_slow_space:
            if fast >= slow:
                continue
                
            # Copy and apply indicators
            df_temp = df_in.copy()
            df_temp = add_indicators(df_temp, ema_fast_span=fast, ema_slow_span=slow)
            
            # Simple vector backtest to evaluate fitness (total returns)
            initial_balance = 10000.0
            balance = initial_balance
            position = 0.0
            
            for i in range(15, len(df_temp)):
                sub_df = df_temp.iloc[:i+1]
                sig_summary = evaluate_latest_signals(sub_df, atr_mult_sl=2.0, atr_mult_tp=3.0)
                action = "BUY" if sig_summary.direction == "LONG" else "SELL" if sig_summary.direction == "SHORT" else "HOLD"
                price = float(df_temp.iloc[i]["close"])
                
                if action == "BUY" and position == 0.0:
                    position = (balance * 0.95) / price
                    balance -= (balance * 0.95) * (1.0 + fee_rate)
                elif action == "SELL" and position > 0.0:
                    balance += (position * price) * (1.0 - fee_rate)
                    position = 0.0
                    
            final_val = balance + (position * float(df_temp["close"].iloc[-1]))
            pnl_pct = (final_val - initial_balance) / initial_balance
            
            if pnl_pct > best_in_sample_pnl:
                best_in_sample_pnl = pnl_pct
                best_params = {"ema_fast": fast, "ema_slow": slow}

    # 4. Out-of-Sample Validation using the best found parameter DNA
    best_fast = best_params["ema_fast"]
    best_slow = best_params["ema_slow"]
    
    df_out_calc = df_out.copy()
    # Need to keep a little trailing boundary context for out-of-sample indicator calculation
    context_df = pd.concat([df_in.iloc[-50:], df_out_calc], ignore_index=True)
    context_df = add_indicators(context_df, ema_fast_span=best_fast, ema_slow_span=best_slow)
    
    # Re-slice out-of-sample candles post indicators
    df_out_evaluated = context_df.iloc[50:].copy().reset_index(drop=True)
    
    # Run backtest on unseen Out-of-Sample data
    initial_balance = 10000.0
    balance = initial_balance
    position = 0.0
    trades_pnl = []
    
    for i in range(15, len(df_out_evaluated)):
        sub_df = df_out_evaluated.iloc[:i+1]
        sig_summary = evaluate_latest_signals(sub_df, atr_mult_sl=2.0, atr_mult_tp=3.0)
        action = "BUY" if sig_summary.direction == "LONG" else "SELL" if sig_summary.direction == "SHORT" else "HOLD"
        price = float(df_out_evaluated.iloc[i]["close"])
        
        if action == "BUY" and position == 0.0:
            position = (balance * 0.95) / price
            balance -= (balance * 0.95) * (1.0 + fee_rate)
        elif action == "SELL" and position > 0.0:
            trade_revenue = (position * price) * (1.0 - fee_rate)
            trade_cost = position * float(sub_df["close"].iloc[0]) # approx cost basis
            trades_pnl.append((trade_revenue - trade_cost) / trade_cost)
            balance += trade_revenue
            position = 0.0
            
    final_val = balance + (position * float(df_out_evaluated["close"].iloc[-1]))
    oos_pnl_pct = (final_val - initial_balance) / initial_balance
    
    # Calculate Sharpe Ratio of out-of-sample returns to measure risk-adjustments
    if len(trades_pnl) > 1:
        std = np.std(trades_pnl)
        oos_sharpe = float(np.mean(trades_pnl) / std * np.sqrt(252)) if std > 0 else 0.0
    else:
        oos_sharpe = 0.0

    # Under-Performance and Overfitting factor (OOS PnL / IS PnL)
    overfit_ratio = oos_pnl_pct / max(best_in_sample_pnl, 1e-4)
    
    return {
        "status": "success",
        "in_sample_bars": len(df_in),
        "out_of_sample_bars": len(df_out),
        "best_ema_fast": best_fast,
        "best_ema_slow": best_slow,
        "in_sample_pnl_pct": best_in_sample_pnl,
        "out_of_sample_pnl_pct": oos_pnl_pct,
        "out_of_sample_sharpe": oos_sharpe,
        "overfitting_ratio": overfit_ratio
    }
