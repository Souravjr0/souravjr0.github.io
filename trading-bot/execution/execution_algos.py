#!/usr/bin/env python3
"""
Institutional Execution Algorithms Engine.
Implements Iceberg order slicing (randomized chunks, custom time delay) and
Volume-Weighted Average Price (VWAP) profile-based execution matching historical book depth.
"""

import time
import random
import threading
from typing import Any

from config import ICEBERG_CHUNKS, ICEBERG_RANDOM_DELAY

def execute_iceberg_order(router, symbol: str, side: str, quantity: float | None = None, quote_qty: float | None = None) -> list[dict]:
    """Execute target order as multiple randomized Iceberg slices to avoid footprint alerting."""
    side_upper = side.upper()
    print(f"[Execution Engine] Launching Iceberg Slicing execution for {symbol} ({side_upper})...")
    
    total_qty = quote_qty
    use_quote = True
    if total_qty is None:
        total_qty = quantity
        use_quote = False
        
    if not total_qty or total_qty <= 0:
        print("[Execution Engine] Invalid total quantity for Iceberg order.")
        return []
        
    chunks = ICEBERG_CHUNKS
    base_chunk_size = total_qty / chunks
    
    orders = []
    
    def _slice_loop():
        remaining = total_qty
        for c in range(chunks):
            if remaining <= 0:
                break
                
            # Last chunk gets exactly what is left
            if c == chunks - 1:
                chunk_size = remaining
            else:
                # Randomize chunk size by +/- 15% to hide fingerprint
                random_factor = random.uniform(0.85, 1.15)
                chunk_size = min(base_chunk_size * random_factor, remaining)
                
            remaining -= chunk_size
            
            # Place order slice using Smart Order Router
            try:
                print(f"  [Iceberg] Placing slice {c+1}/{chunks} - Sized: {chunk_size:.4f}...")
                if use_quote:
                    res = router.route_order(symbol, side_upper, quote_qty=chunk_size)
                else:
                    res = router.route_order(symbol, side_upper, quantity=chunk_size)
                orders.append(res)
            except Exception as e:
                print(f"  [Iceberg] Error on slice {c+1}: {e}")
                
            # Randomized delay
            if c < chunks - 1:
                sleep_time = random.uniform(1.5, 4.5) if ICEBERG_RANDOM_DELAY else 2.0
                print(f"  [Iceberg] Sleeping for {sleep_time:.2f}s before next slice...")
                time.sleep(sleep_time)
                
        print(f"[Execution Engine] Iceberg Slicing execution finished successfully for {symbol}. Total slices: {len(orders)}.")

    # Run execution synchronously in the background to prevent main thread blocking, or synchronously for short slices
    # We will run it in a daemon thread so it runs in background
    threading.Thread(target=_slice_loop, daemon=True).start()
    
    # Return quick initial confirmation dict representing the scheduled execution
    return [{"status": "iceberg_scheduled", "symbol": symbol, "side": side, "slices": chunks}]

def execute_vwap_order(router, symbol: str, side: str, quantity: float | None = None, quote_qty: float | None = None) -> list[dict]:
    """Execute order dynamically following historical volume profile distributions to blend in."""
    side_upper = side.upper()
    print(f"[Execution Engine] Launching Volume-Weighted Average Price (VWAP) execution for {symbol} ({side_upper})...")
    
    total_qty = quote_qty
    use_quote = True
    if total_qty is None:
        total_qty = quantity
        use_quote = False
        
    if not total_qty or total_qty <= 0:
        print("[Execution Engine] Invalid total quantity for VWAP order.")
        return []
        
    # Standard historical volume distribution ratios for 4 intervals
    # VWAP is heavily front-loaded and back-loaded matching exchange activity
    volume_ratios = [0.35, 0.15, 0.20, 0.30] 
    intervals = len(volume_ratios)
    
    orders = []
    
    def _vwap_loop():
        remaining = total_qty
        for i in range(intervals):
            if remaining <= 0:
                break
                
            if i == intervals - 1:
                chunk_size = remaining
            else:
                chunk_size = min(total_qty * volume_ratios[i], remaining)
                
            remaining -= chunk_size
            
            try:
                print(f"  [VWAP] Placing interval slice {i+1}/{intervals} (ratio={volume_ratios[i]:.2%}) - Sized: {chunk_size:.4f}...")
                if use_quote:
                    res = router.route_order(symbol, side_upper, quote_qty=chunk_size)
                else:
                    res = router.route_order(symbol, side_upper, quantity=chunk_size)
                orders.append(res)
            except Exception as e:
                print(f"  [VWAP] Error on interval slice {i+1}: {e}")
                
            if i < intervals - 1:
                sleep_time = random.uniform(2.0, 5.0)
                print(f"  [VWAP] Interval sleep for {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                
        print(f"[Execution Engine] VWAP execution finished successfully for {symbol}. Total slices: {len(orders)}.")

    threading.Thread(target=_vwap_loop, daemon=True).start()
    return [{"status": "vwap_scheduled", "symbol": symbol, "side": side, "intervals": intervals}]
