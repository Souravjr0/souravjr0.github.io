#!/usr/bin/env python3
"""
Dynamic Priority Fee Estimator
cook45 & clack // Systems & MEV

Queries getRecentPrioritizationFees from Helius and QuickNode to calculate
the optimal micro-lamport fee for block frontrunning.
"""

import os
import httpx
import asyncio
from dotenv import load_dotenv

async def get_adaptive_priority_fee():
    load_dotenv()
    url = os.getenv("HELIUS_RPC_URL", "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
    
    # We query the priority fees for pump.fun program or generally
    # Pump.fun program ID: 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getRecentPrioritizationFees",
        "params": [["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json().get("result", [])
                if not result:
                    print("[!] No priority fees returned. Returning default fee.")
                    return 0.0002
                
                # Extract fees (micro-lamports per compute unit)
                fees = [r["prioritizationFee"] for r in result]
                fees.sort()
                
                # Calculate percentiles
                p50 = fees[len(fees) // 2]
                p75 = fees[int(len(fees) * 0.75)]
                p90 = fees[int(len(fees) * 0.90)]
                
                # Convert micro-lamports per CU to total SOL fee (assuming 100k CU for a standard swap)
                # Formula: (micro_lamports * 100,000 / 1e6) / 1e9
                # i.e. micro_lamports / 1e10
                sol_p50 = p50 / 1e10
                sol_p75 = p75 / 1e10
                sol_p90 = p90 / 1e10
                
                print("--- Live Prioritization Fee Estimate (Pump.fun) ---")
                print(f"  - 50th Percentile (Median): {p50} micro-lamports (~{sol_p50:.6f} SOL)")
                print(f"  - 75th Percentile (Active): {p75} micro-lamports (~{sol_p75:.6f} SOL)")
                print(f"  - 90th Percentile (Extreme):{p90} micro-lamports (~{sol_p90:.6f} SOL)")
                
                # Recommended fee: 75th percentile with a hard minimum of 0.0001 SOL
                recommended = max(sol_p75, 0.0001)
                print(f"\n[+] Recommended Adaptive Priority Fee: {Fore.GREEN if recommended < 0.001 else Fore.YELLOW}{recommended:.6f} SOL{Style.RESET_ALL}")
                return recommended
            else:
                print(f"[X] RPC error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[X] Error fetching priority fees: {e}")
    
    return 0.0002

if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)
    asyncio.run(get_adaptive_priority_fee())
