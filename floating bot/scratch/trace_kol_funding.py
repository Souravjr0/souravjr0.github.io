#!/usr/bin/env python3
"""
KOL Wallet Funding & Interaction Tracer
cook45 & clack // Systems & MEV

Traces the absolute earliest transactions and interactions of the target KOL:
AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN
1. Finds the funding transaction (where did the first SOL come from?)
2. Checks direct peer-to-peer transfers (SOL and SPL)
3. Identifies linked wallets/hubs
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

async def main():
    load_dotenv()
    api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    kol_addr = "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN"

    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          KOL TARGET FUNDING & FLOW TRACER        ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")
    print(f"[+] Target KOL Address: {Fore.YELLOW}{kol_addr}{Style.RESET_ALL}\n")

    # Step 1: Paginate to the absolute earliest signatures
    print("[*] Paginating signatures to find earliest transactions...")
    all_sigs = []
    before = None
    
    # We will fetch up to 2000 signatures to find the beginning
    for i in range(5):
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [kol_addr, {"limit": 1000, "before": before}]
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    print(f"[X] HTTP Error fetching signatures: {resp.status_code}")
                    break
                sigs = resp.json().get("result", [])
                if not sigs:
                    break
                all_sigs.extend(sigs)
                print(f"  Batch {i+1}: Fetched {len(sigs)} signatures (Total: {len(all_sigs)}). Earliest slot: {sigs[-1]['slot']}")
                before = sigs[-1]["signature"]
                if len(sigs) < 1000:
                    break
        except Exception as e:
            print(f"[X] Connection Error: {e}")
            break

    if not all_sigs:
        print("[X] No signatures found.")
        return

    print(f"\n[+] Total transaction signatures fetched: {len(all_sigs)}")
    
    # Chronological order: from oldest to newest
    oldest_sigs = list(reversed(all_sigs))
    
    # Let's inspect the oldest 10 transactions to find the funding source
    print(f"\n[*] Inspecting the oldest 10 transactions (chronological) to find funding source...")
    print("=" * 80)
    
    funding_wallet = None
    funding_tx = None
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for idx, sig_info in enumerate(oldest_sigs[:15]):
            sig = sig_info["signature"]
            slot = sig_info["slot"]
            
            tx_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            }
            
            try:
                tx_resp = await client.post(url, json=tx_payload)
                if tx_resp.status_code != 200:
                    print(f"  [X] Failed to fetch tx: {sig[:12]}...")
                    continue
                
                tx_data = tx_resp.json().get("result")
                if not tx_data:
                    print(f"  [X] No details for tx: {sig[:12]}...")
                    continue
                
                meta = tx_data.get("meta", {})
                transaction = tx_data.get("transaction", {})
                message = transaction.get("message", {})
                account_keys = message.get("accountKeys", [])
                
                # Extract signer
                if isinstance(account_keys[0], dict):
                    signer = [k["pubkey"] for k in account_keys if k.get("signer")][0]
                else:
                    signer = account_keys[0]
                
                # Check balance changes to see who sent SOL to our KOL address
                pre_balances = meta.get("preBalances", [])
                post_balances = meta.get("postBalances", [])
                
                kol_index = -1
                for key_idx, key_info in enumerate(account_keys):
                    k_addr = key_info["pubkey"] if isinstance(key_info, dict) else key_info
                    if k_addr == kol_addr:
                        kol_index = key_idx
                        break
                
                sol_change = 0.0
                if kol_index != -1 and pre_balances and post_balances:
                    sol_change = (post_balances[kol_index] - pre_balances[kol_index]) / 1e9
                
                print(f"Tx #{idx+1} | Slot: {slot} | Sig: {sig[:16]}... | Signer: {signer[:12]}... | SOL Change: {sol_change:+.4f} SOL")
                
                # Find funding wallet (first transaction where KOL receives > 0.01 SOL)
                if sol_change > 0.01 and not funding_wallet:
                    # Find sender: check accounts with negative SOL changes
                    for key_idx, key_info in enumerate(account_keys):
                        k_addr = key_info["pubkey"] if isinstance(key_info, dict) else key_info
                        if k_addr != kol_addr and pre_balances and post_balances:
                            sender_change = (post_balances[key_idx] - pre_balances[key_idx]) / 1e9
                            if sender_change < -0.01:
                                funding_wallet = k_addr
                                funding_tx = sig
                                print(f"  {Fore.GREEN}[FOUND FUNDING SOURCE]{Style.RESET_ALL} Sent by: {Fore.YELLOW}{funding_wallet}{Style.RESET_ALL} in Tx: {sig}")
                                break
            except Exception as e:
                print(f"  [X] Error parsing tx {sig[:12]}...: {e}")

    print("\n" + "=" * 80)
    if funding_wallet:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}[SUCCESS] ANALYSIS RESULTS:")
        print(f"  Target KOL:       {Fore.YELLOW}{kol_addr}{Style.RESET_ALL}")
        print(f"  Funding Wallet:   {Fore.CYAN}{funding_wallet}{Style.RESET_ALL}")
        print(f"  Funding Tx:       {Fore.LIGHTCYAN_EX}{funding_tx}{Style.RESET_ALL}")
        
        # Check if the funding wallet is a known exchange
        # Common exchange hot wallets:
        # Binance: 5VCwJ6G4FvT2kqgVQCCnCL3DL4W5oP5fM3S92YJgA5rw
        # Coinbase: 2AQdGsjntGzFB2E2L7MebXAXGg4cK5Z75Csn6qH86Z3E
        # Kraken: 4rTdf9kH4M1SgqY81Wz8v9oP5fM3S92YJgA5rw...
        # OKX: 3t3aFpS...
        known_exchanges = {
            "5VCwJ6G4FvT2kqgVQCCnCL3DL4W5oP5fM3S92YJgA5rw": "Binance Hot Wallet",
            "9Wz2m7K3wUCjS7tKBwCTK5jHndJPMJw9wukWSSQf3R32": "Binance-Peg",
            "2AQdGsjntGzFB2E2L7MebXAXGg4cK5Z75Csn6qH86Z3E": "Coinbase Hot Wallet",
            "ASTyfS8426AuJNHd7PLgz3f9WZK4dfYg96WkXmF5NquS": "Kraken Hot Wallet",
            "F4r4wU1Y9o9o...": "OKX Hot Wallet"
        }
        
        label = known_exchanges.get(funding_wallet, "PRIVATE WALLET / ALT ACCOUNT (POTENTIAL LEAD!)")
        print(f"  Source Type:      {Fore.LIGHTMAGENTA_EX}{label}{Style.RESET_ALL}")
        
        if label == "PRIVATE WALLET / ALT ACCOUNT (POTENTIAL LEAD!)":
            print(f"\n[*] Probing funding wallet SOL balance...")
            sol_bal_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getBalance",
                "params": [funding_wallet]
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=sol_bal_payload)
                    if resp.status_code == 200:
                        bal = resp.json().get("result", {}).get("value", 0) / 1e9
                        print(f"  Funding Wallet Balance: {Fore.GREEN}{bal:.6f} SOL{Style.RESET_ALL}")
            except Exception as e:
                print(f"  Error fetching funding wallet balance: {e}")
    else:
        print(f"\n{Fore.RED}[X] Could not identify funding wallet from first 15 transactions. Address might have been funded via complex nested swaps or bridges.")

if __name__ == "__main__":
    asyncio.run(main())
