#!/usr/bin/env python3
"""
Wallet Trade Correlation Analyzer
cook45 & clack // Systems & MEV

Audits trade overlap and timing correlation between:
1. AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN (Putrick)
2. Anubis512ho5t7S6LNSwoxUWdeQmX2kf3RvZ8ApHHF5w (Anubis)

Checks if they trade the same tokens, at what times, and if they are running the exact same script.
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

async def fetch_wallet_trades(client, url, wallet_addr, limit=100):
    """
    Fetches the transaction signatures for a wallet, parses them to extract
    mints and blocktimes of token trading actions (buys/sells on Raydium/Pump.fun).
    """
    print(f"[*] Fetching last {limit} signatures for {wallet_addr[:10]}...")
    payload_sigs = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_addr, {"limit": limit}]
    }
    
    try:
        resp = await client.post(url, json=payload_sigs)
        if resp.status_code != 200:
            print(f"[X] Failed to fetch signatures for {wallet_addr[:10]}")
            return []
        
        sigs = resp.json().get("result", [])
        print(f"  [+] Found {len(sigs)} signatures.")
        return sigs
    except Exception as e:
        print(f"[X] Error fetching signatures for {wallet_addr[:10]}: {e}")
        return []

async def analyze_transactions(client, url, sigs, wallet_addr):
    """
    Takes transaction signatures, fetches full tx details, and parses them to isolate:
    - Mint traded
    - Type of trade (Buy/Sell)
    - Slot / Timestamp
    - Transaction Signature
    """
    trades = []
    # Let's parallelize the transaction fetching in batches of 15 to avoid RPC rate limits
    batch_size = 15
    for i in range(0, len(sigs), batch_size):
        batch = sigs[i:i+batch_size]
        tasks = []
        for sig_info in batch:
            sig = sig_info["signature"]
            block_time = sig_info.get("blockTime")
            slot = sig_info.get("slot")
            
            tx_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            }
            tasks.append(client.post(url, json=tx_payload))
            
        resps = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, resp in enumerate(resps):
            if isinstance(resp, Exception) or resp.status_code != 200:
                continue
            
            tx_data = resp.json().get("result")
            if not tx_data:
                continue
            
            meta = tx_data.get("meta", {})
            if meta.get("err"):
                continue  # Skip failed trades
                
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])
            
            # Identify token mints by examining post-token balances
            post_token_balances = meta.get("postTokenBalances", [])
            pre_token_balances = meta.get("preTokenBalances", [])
            
            # Find the mints traded by this owner
            owner_mints = {}
            for pb in pre_token_balances:
                if pb.get("owner") == wallet_addr:
                    mint = pb.get("mint")
                    amount = float(pb["uiTokenAmount"].get("uiAmount") or 0)
                    owner_mints[mint] = {"pre": amount, "post": 0.0}
                    
            for pb in post_token_balances:
                if pb.get("owner") == wallet_addr:
                    mint = pb.get("mint")
                    amount = float(pb["uiTokenAmount"].get("uiAmount") or 0)
                    if mint not in owner_mints:
                        owner_mints[mint] = {"pre": 0.0, "post": amount}
                    else:
                        owner_mints[mint]["post"] = amount
            
            # Calculate changes
            for mint, amounts in owner_mints.items():
                diff = amounts["post"] - amounts["pre"]
                if diff != 0:
                    trade_type = "BUY" if diff > 0 else "SELL"
                    trades.append({
                        "mint": mint,
                        "type": trade_type,
                        "amount": abs(diff),
                        "slot": batch[idx].get("slot"),
                        "timestamp": batch[idx].get("blockTime"),
                        "signature": batch[idx]["signature"]
                    })
    return trades

async def main():
    load_dotenv()
    api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    
    w1 = "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN"  # Putrick
    w2 = "Anubis512ho5t7S6LNSwoxUWdeQmX2kf3RvZ8ApHHF5w"  # Anubis
    
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          WALLET TRADE CORRELATION DETECTOR        ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fetch sigs
        w1_sigs = await fetch_wallet_trades(client, url, w1, limit=40)
        w2_sigs = await fetch_wallet_trades(client, url, w2, limit=40)
        
        if not w1_sigs or not w2_sigs:
            print("[X] Could not fetch sufficient signature histories to perform correlation audit.")
            return
            
        print("\n[*] Fetching and parsing transactions to extract traded mints... (this takes ~10s)")
        w1_trades = await analyze_transactions(client, url, w1_sigs, w1)
        w2_trades = await analyze_transactions(client, url, w2_sigs, w2)
        
        print(f"[+] Extracted {len(w1_trades)} active trades for Putrick.")
        print(f"[+] Extracted {len(w2_trades)} active trades for Anubis.")
        
        # Cross-reference the trades by mints
        w1_mints = {t["mint"]: t for t in w1_trades}
        w2_mints = {t["mint"]: t for t in w2_trades}
        
        common_mints = set(w1_mints.keys()).intersection(set(w2_mints.keys()))
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}=== CORRELATION AUDIT RESULTS ===")
        if not common_mints:
            print(f"{Fore.RED}[X] No direct token mint overlap found in the recent history batches.")
            print("This means they might not be trading the exact same tokens in this window, or their trade histories have diverged.")
            
            # Let's print out their top recent tokens to compare profiles
            print("\nPutrick's Recent Tokens:")
            for m in list(w1_mints.keys())[:5]:
                t = w1_mints[m]
                print(f"  - Mint: {m[:12]}... | Action: {t['type']} | Time: {datetime.fromtimestamp(t['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\nAnubis's Recent Tokens:")
            for m in list(w2_mints.keys())[:5]:
                t = w2_mints[m]
                print(f"  - Mint: {m[:12]}... | Action: {t['type']} | Time: {datetime.fromtimestamp(t['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"{Fore.GREEN}[FOUND DIRECT OVERLAP] Both wallets traded {len(common_mints)} matching tokens recently!\n")
            
            for idx, mint in enumerate(common_mints):
                p_trades = [t for t in w1_trades if t["mint"] == mint]
                a_trades = [t for t in w2_trades if t["mint"] == mint]
                
                print(f"{idx+1}. Token Mint: {Fore.YELLOW}{mint}{Style.RESET_ALL}")
                
                for pt in p_trades:
                    p_time = pt["timestamp"]
                    p_action = pt["type"]
                    
                    # Find closest trade in timing in Anubis
                    for at in a_trades:
                        a_time = at["timestamp"]
                        a_action = at["type"]
                        time_diff = abs(p_time - a_time)
                        
                        time_str = f"{time_diff}s" if time_diff < 60 else f"{time_diff//60}m {time_diff%60}s"
                        
                        # Flag highly correlated actions (under 30s difference)
                        status_color = Fore.LIGHTGREEN_EX if time_diff <= 30 else Fore.LIGHTRED_EX
                        correlation_level = "CRITICAL CO-EXECUTION!" if time_diff <= 5 else "HIGHLY CORRELATED" if time_diff <= 30 else "STANDALONE ACTION"
                        
                        print(f"  - Putrick: {Fore.CYAN}{p_action:<4}{Style.RESET_ALL} | Slot: {pt['slot']} | Time: {datetime.fromtimestamp(p_time).strftime('%H:%M:%S')}")
                        print(f"  - Anubis : {Fore.CYAN}{a_action:<4}{Style.RESET_ALL} | Slot: {at['slot']} | Time: {datetime.fromtimestamp(a_time).strftime('%H:%M:%S')}")
                        print(f"  - {status_color}Time Delta: {time_str} | Correlation: {correlation_level}{Style.RESET_ALL}\n")
            
            # Summarize the system verdict
            avg_delta = sum(abs(t1["timestamp"] - t2["timestamp"]) for mint in common_mints for t1 in w1_trades if t1["mint"] == mint for t2 in w2_trades if t2["mint"] == mint) / (len(common_mints) or 1)
            print("=" * 80)
            print(f"\n{Fore.GREEN}{Style.BRIGHT}[VERDICT] COLLUSION / COPY-TRADING AUDIT:")
            if avg_delta <= 10:
                print(f"  - Overlap: {len(common_mints)} tokens")
                print(f"  - Avg Delay: {avg_delta:.2f} seconds")
                print(f"  - Status: {Fore.RED}{Style.BRIGHT}100% EXPLICIT BUNDLER / SCRIPT SHARING DETECTED.{Style.RESET_ALL}")
                print("  These wallets are either the same person running a synchronized script or one is perfectly frontrunning the other via block-0 mempool monitoring.")
            else:
                print(f"  - Overlap: {len(common_mints)} tokens")
                print(f"  - Avg Delay: {avg_delta:.2f} seconds")
                print(f"  - Status: {Fore.YELLOW}MANUAL CABAL SYNDICATION.{Style.RESET_ALL}")
                print("  They buy the same token narratives, but execution happens in separate blocks/minutes. Indicates direct chat group/syndicate coordination.")

if __name__ == "__main__":
    asyncio.run(main())
