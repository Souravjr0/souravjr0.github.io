import time
import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

PUBLIC_RPC = "https://api.mainnet-beta.solana.com"
HELIUS_RPC = os.getenv("HELIUS_RPC_URL", "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
QUICKNODE_RPC = "https://intensive-tame-sailboat.solana-mainnet.quiknode.pro/38e6fb2dff8cb28d082502d75e31a86b19203b61/"

async def test_rpc_latency(name: str, url: str, runs: int = 5):
    print(f"Testing {name} ({url[:45]}...)...")
    latencies = []
    success = 0
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSlot" # getSlot is a lightweight, indexer-backed method (good for speed check)
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for idx in range(runs):
            start = time.perf_counter()
            try:
                resp = await client.post(url, json=payload, headers=headers)
                end = time.perf_counter()
                if resp.status_code == 200:
                    rtt = (end - start) * 1000 # ms
                    latencies.append(rtt)
                    success += 1
                    print(f"  Run {idx+1}: {rtt:.2f} ms")
                else:
                    print(f"  Run {idx+1}: FAILED (HTTP {resp.status_code})")
            except Exception as e:
                print(f"  Run {idx+1}: FAILED ({e})")
            await asyncio.sleep(0.5)
            
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
    else:
        avg_lat = 0
        min_lat = 0
        max_lat = 0
        
    return {
        "name": name,
        "avg": avg_lat,
        "min": min_lat,
        "max": max_lat,
        "success_rate": (success / runs) * 100
    }

async def run_benchmark():
    print("========================================================================")
    print("                SOLANA RPC SPEED BENCHMARK ENGINE                      ")
    print("                 cook45 & clack // Systems & MEV                        ")
    print("========================================================================\n")
    
    public_res = await test_rpc_latency("Solana Public RPC", PUBLIC_RPC)
    print()
    helius_res = await test_rpc_latency("Your Helius RPC", HELIUS_RPC)
    print()
    quicknode_res = await test_rpc_latency("New QuickNode RPC", QUICKNODE_RPC)
    
    print("\n" + "="*80)
    print("                        RPC SPEED COMPARISON REPORT                     ")
    print("="*80)
    print(f"{'RPC Name':<25} | {'Avg Latency':<12} | {'Min Latency':<12} | {'Max Latency':<12} | {'Success Rate':<12}")
    print("-"*80)
    
    for res in [public_res, helius_res, quicknode_res]:
        avg_str = f"{res['avg']:.2f} ms" if res['avg'] > 0 else "N/A"
        min_str = f"{res['min']:.2f} ms" if res['min'] > 0 else "N/A"
        max_str = f"{res['max']:.2f} ms" if res['max'] > 0 else "N/A"
        print(f"{res['name']:<25} | {avg_str:<12} | {min_str:<12} | {max_str:<12} | {res['success_rate']:.1f}%")
        
    print("="*80)
    
    # Determine the fastest RPC
    results = [
        ("Your Helius RPC", helius_res['avg']),
        ("New QuickNode RPC", quicknode_res['avg']),
        ("Solana Public RPC", public_res['avg'])
    ]
    valid_results = [r for r in results if r[1] > 0]
    if valid_results:
        fastest_name, fastest_lat = min(valid_results, key=lambda x: x[1])
        print(f"\n[ANALYSIS] Fastest RPC is: {fastest_name} with an average of {fastest_lat:.2f} ms!")
        
    print("\nMEV SNIPING RECOMMENDATION:")
    best_lat = min([r['avg'] for r in [helius_res, quicknode_res] if r['avg'] > 0])
    if best_lat > 150.0:
        print("[WARNING] Your best private latency is > 150ms! Snipe slippage or placement failure risk is elevated.")
    else:
        print("[OK] Private RPC speed is highly optimal (< 150ms) for high-speed sniping. Primed to land.")
    print("="*80 + "\n")

if __name__ == '__main__':
    asyncio.run(run_benchmark())
