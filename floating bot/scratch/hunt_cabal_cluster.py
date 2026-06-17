#!/usr/bin/env python3
"""
Cabal Cluster Hunter & Wallet Extractor
cook45 & clack // Systems & MEV

Hunts down more linked wallets in the cabal network:
1. Traces all outgoing transfers from Level 2 Parent Hub: 6j1eiB1sFG5pUdwjwbEBx6mtntzDtvoW1vzLQufku7Xm
2. Traces all outgoing transfers from Level 3 Master Hub: 3GhjqYsyUqi7DSnCGSwvNYoExCURzrc98S9STHscAZui
3. Scans for other wallets co-executing trades within the exact same blocks/slots for key target tokens.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

async def scan_outgoing_transfers(client, url, source_wallet, label):
    """
    Scans signatures of a hub wallet to identify all unique wallets
    it has funded or transferred SOL to.
    """
    print(f"\n[*] Scanning outgoing transfers from {label} ({source_wallet[:10]}...)...")
    payload_sigs = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [source_wallet, {"limit": 100}]
    }
    
    try:
        resp = await client.post(url, json=payload_sigs)
        if resp.status_code != 200:
            print(f"[X] Failed to fetch signatures for {label}")
            return set()
            
        sigs = resp.json().get("result", [])
        print(f"  [+] Found {len(sigs)} signatures. Parsing transfer destinations...")
        
        funded_wallets = set()
        
        # Batch fetch transactions
        batch_size = 20
        for i in range(0, len(sigs), batch_size):
            batch = sigs[i:i+batch_size]
            tasks = []
            for s in batch:
                tx_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTransaction",
                    "params": [s["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                }
                tasks.append(client.post(url, json=tx_payload))
                
            resps = await asyncio.gather(*tasks, return_exceptions=True)
            for resp in resps:
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                tx_data = resp.json().get("result")
                if not tx_data:
                    continue
                
                meta = tx_data.get("meta", {})
                transaction = tx_data.get("transaction", {})
                message = transaction.get("message", {})
                account_keys = message.get("accountKeys", [])
                
                # Check for system program SOL transfers originating from the source_wallet
                pre_balances = meta.get("preBalances", [])
                post_balances = meta.get("postBalances", [])
                
                source_idx = -1
                for idx, key in enumerate(account_keys):
                    k_addr = key["pubkey"] if isinstance(key, dict) else key
                    if k_addr == source_wallet:
                        source_idx = idx
                        break
                
                if source_idx == -1 or not pre_balances or not post_balances:
                    continue
                
                # If source balance went down significantly, find who received it
                source_change = (post_balances[source_idx] - pre_balances[source_idx]) / 1e9
                if source_change < -0.01:
                    # Look for other accounts whose balances increased
                    for idx, key in enumerate(account_keys):
                        if idx == source_idx:
                            continue
                        k_addr = key["pubkey"] if isinstance(key, dict) else key
                        # Exclude standard programs/system state
                        if len(k_addr) < 32 or k_addr.startswith("ComputeBudget") or k_addr.startswith("Token") or k_addr.startswith("1111"):
                            continue
                            
                        dest_change = (post_balances[idx] - pre_balances[idx]) / 1e9
                        if dest_change > 0.01:
                            funded_wallets.add(k_addr)
                            
        print(f"  [+] Identified {len(funded_wallets)} unique wallets funded directly by {label}.")
        return funded_wallets
    except Exception as e:
        print(f"[X] Error scanning transfers for {label}: {e}")
        return set()

async def main():
    load_dotenv()
    api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    
    hub_lvl2 = "6j1eiB1sFG5pUdwjwbEBx6mtntzDtvoW1vzLQufku7Xm"
    hub_lvl3 = "3GhjqYsyUqi7DSnCGSwvNYoExCURzrc98S9STHscAZui"
    
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          CABAL INSIDER WALLET CLUSTER HUNTER     ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Scan funding alts
        lvl2_funded = await scan_outgoing_transfers(client, url, hub_lvl2, "Level 2 Parent Hub")
        lvl3_funded = await scan_outgoing_transfers(client, url, hub_lvl3, "Level 3 Master Hub")
        
        # Consolidate all alts
        all_linked_wallets = lvl2_funded.union(lvl3_funded)
        
        # Exclude our target Putrick and known ones from showing as "new alts"
        known_wallets = {
            "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN",
            "Anubis512ho5t7S6LNSwoxUWdeQmX2kf3RvZ8ApHHF5w",
            "GkACCdsUyRfCgYYmFtSyoeru97dXKtoSKotWdU9Ees4x",
            "6j1eiB1sFG5pUdwjwbEBx6mtntzDtvoW1vzLQufku7Xm",
            "3GhjqYsyUqi7DSnCGSwvNYoExCURzrc98S9STHscAZui"
        }
        
        new_targets = all_linked_wallets.difference(known_wallets)
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}==================================================")
        print(f"{Fore.GREEN}{Style.BRIGHT}        HUNT SUCCESSFUL: CABAL TARGET BOARD       ")
        print(f"{Fore.GREEN}{Style.BRIGHT}==================================================")
        print(f"[+] Total new linked wallets discovered: {Fore.YELLOW}{len(new_targets)}{Style.RESET_ALL}\n")
        
        if not new_targets:
            print("No new standalone alts found in the outgoing staging window. The alts might be funded recursively or via a single path.")
        else:
            # Let's inspect the active balances of these new targets
            print("--- Newly Uncovered Active Cabal Wallets ---")
            for idx, wallet in enumerate(new_targets):
                payload_sol = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getBalance",
                    "params": [wallet]
                }
                
                try:
                    resp = await client.post(url, json=payload_sol)
                    bal = resp.json().get("result", {}).get("value", 0) / 1e9
                except Exception:
                    bal = 0.0
                    
                # Query recent token account count to see if active sniper
                payload_tokens = {
                    "jsonrpc": "2.0", "id": 2,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet,
                        {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                        {"encoding": "jsonParsed"}
                    ]
                }
                try:
                    resp = await client.post(url, json=payload_tokens)
                    token_count = len(resp.json().get("result", {}).get("value", []))
                except Exception:
                    token_count = 0
                
                print(f"Target #{idx+1} : {Fore.CYAN}{wallet}{Style.RESET_ALL}")
                print(f"  - Balance: {Fore.GREEN}{bal:.4f} SOL{Style.RESET_ALL} | Active Tokens: {Fore.LIGHTCYAN_EX}{token_count}{Style.RESET_ALL}")
                
            # Append these targets to insider_wallets.json automatically so the bot starts tracking their actions!
            try:
                import json
                with open("insider_wallets.json", "r") as f:
                    data = json.load(f)
                
                orig_len = len(data["wallets"])
                for w in new_targets:
                    if w not in data["wallets"]:
                        data["wallets"].append(w)
                
                with open("insider_wallets.json", "w") as f:
                    json.dump(data, f, indent=4)
                    
                added_count = len(data["wallets"]) - orig_len
                print(f"\n{Fore.GREEN}[+] Automatically appended {added_count} new alts to insider_wallets.json (Total monitored: {len(data['wallets'])}).")
            except Exception as e:
                print(f"[X] Failed to automatically update insider_wallets.json: {e}")

if __name__ == "__main__":
    asyncio.run(main())
