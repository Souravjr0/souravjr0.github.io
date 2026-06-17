#!/usr/bin/env python3
"""
Master Hub Wallet Intel & Profiler
cook45 & clack // Systems & MEV

Profiles the master source wallet:
6j1eiB1sFG5pUdwjwbEBx6mtntzDtvoW1vzLQufku7Xm
1. Live SOL balance & SPL tokens
2. Earliest transaction history and funding source
3. Active linkages to other accounts
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
    target_addr = "6j1eiB1sFG5pUdwjwbEBx6mtntzDtvoW1vzLQufku7Xm"

    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          MASTER HUB WALLET PROFILE & AUDIT       ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")
    print(f"[+] Target Master Address: {Fore.YELLOW}{target_addr}{Style.RESET_ALL}\n")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. SOL Balance
        payload_sol = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getBalance",
            "params": [target_addr]
        }
        try:
            resp = await client.post(url, json=payload_sol)
            if resp.status_code == 200:
                sol_bal = resp.json().get("result", {}).get("value", 0) / 1e9
                print(f"[+] Live SOL Balance: {Fore.GREEN}{sol_bal:.6f} SOL{Style.RESET_ALL}")
            else:
                print(f"[X] Failed to fetch SOL balance")
        except Exception as e:
            print(f"[X] Error: {e}")

        # 2. Token holdings
        payload_tokens = {
            "jsonrpc": "2.0", "id": 2,
            "method": "getTokenAccountsByOwner",
            "params": [
                target_addr,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        try:
            resp = await client.post(url, json=payload_tokens)
            if resp.status_code == 200:
                accounts = resp.json().get("result", {}).get("value", [])
                print(f"[+] Total SPL Token Accounts: {len(accounts)}")
                
                active_tokens = []
                for acct in accounts:
                    info = acct["account"]["data"]["parsed"]["info"]
                    mint = info["mint"]
                    amount = float(info["tokenAmount"].get("uiAmount") or 0)
                    if amount > 0:
                        active_tokens.append((mint, amount))
                
                print("\n--- Active Holdings ---")
                if not active_tokens:
                    print("  No active token balances.")
                else:
                    for mint, amount in active_tokens:
                        mint_label = f"{Fore.LIGHTMAGENTA_EX}(Pump.fun){Style.RESET_ALL}" if mint.endswith("pump") else ""
                        print(f"  Mint: {Fore.CYAN}{mint:<44}{Style.RESET_ALL} | Balance: {Fore.LIGHTCYAN_EX}{amount:,.2f}{Style.RESET_ALL} {mint_label}")
        except Exception as e:
            print(f"[X] Error: {e}")

        # 3. History to find funding source
        print("\n[*] Paginating history to find how this wallet was funded...")
        all_sigs = []
        before = None
        for i in range(3):
            payload_sigs = {
                "jsonrpc": "2.0", "id": 3,
                "method": "getSignaturesForAddress",
                "params": [target_addr, {"limit": 1000, "before": before}]
            }
            try:
                resp = await client.post(url, json=payload_sigs)
                if resp.status_code == 200:
                    sigs = resp.json().get("result", [])
                    if not sigs:
                        break
                    all_sigs.extend(sigs)
                    before = sigs[-1]["signature"]
                    if len(sigs) < 1000:
                        break
                else:
                    break
            except Exception as e:
                break
        
        print(f"[+] Fetched {len(all_sigs)} transaction signatures.")
        if all_sigs:
            oldest_sigs = list(reversed(all_sigs))
            print(f"\n[*] Inspecting first 15 transactions to find funding source...")
            print("=" * 80)
            
            funding_wallet = None
            funding_tx = None
            
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
                        continue
                    tx_data = tx_resp.json().get("result")
                    if not tx_data:
                        continue
                    
                    meta = tx_data.get("meta", {})
                    transaction = tx_data.get("transaction", {})
                    message = transaction.get("message", {})
                    account_keys = message.get("accountKeys", [])
                    
                    if isinstance(account_keys[0], dict):
                        signer = [k["pubkey"] for k in account_keys if k.get("signer")][0]
                    else:
                        signer = account_keys[0]
                    
                    pre_balances = meta.get("preBalances", [])
                    post_balances = meta.get("postBalances", [])
                    
                    t_index = -1
                    for key_idx, key_info in enumerate(account_keys):
                        k_addr = key_info["pubkey"] if isinstance(key_info, dict) else key_info
                        if k_addr == target_addr:
                            t_index = key_idx
                            break
                    
                    sol_change = 0.0
                    if t_index != -1 and pre_balances and post_balances:
                        sol_change = (post_balances[t_index] - pre_balances[t_index]) / 1e9
                    
                    print(f"Tx #{idx+1} | Slot: {slot} | Sig: {sig[:16]}... | Signer: {signer[:12]}... | SOL Change: {sol_change:+.4f} SOL")
                    
                    if sol_change > 0.01 and not funding_wallet:
                        for key_idx, key_info in enumerate(account_keys):
                            k_addr = key_info["pubkey"] if isinstance(key_info, dict) else key_info
                            if k_addr != target_addr and pre_balances and post_balances:
                                sender_change = (post_balances[key_idx] - pre_balances[key_idx]) / 1e9
                                if sender_change < -0.01:
                                    funding_wallet = k_addr
                                    funding_tx = sig
                                    print(f"  {Fore.GREEN}[FOUND FUNDING SOURCE]{Style.RESET_ALL} Sent by: {Fore.YELLOW}{funding_wallet}{Style.RESET_ALL} in Tx: {sig}")
                                    break
                except Exception as e:
                    pass

            print("\n" + "=" * 80)
            if funding_wallet:
                print(f"\n{Fore.GREEN}{Style.BRIGHT}[SUCCESS] ANALYSIS FOR MASTER HUB WALLET:")
                print(f"  Master Target:    {Fore.YELLOW}{target_addr}{Style.RESET_ALL}")
                print(f"  Funding Source:   {Fore.CYAN}{funding_wallet}{Style.RESET_ALL}")
                print(f"  Funding Tx:       {Fore.LIGHTCYAN_EX}{funding_tx}{Style.RESET_ALL}")
                
                # Check if it matches exchanges or CEXs
                known_exchanges = {
                    "5VCwJ6G4FvT2kqgVQCCnCL3DL4W5oP5fM3S92YJgA5rw": "Binance Hot Wallet",
                    "9Wz2m7K3wUCjS7tKBwCTK5jHndJPMJw9wukWSSQf3R32": "Binance-Peg",
                    "2AQdGsjntGzFB2E2L7MebXAXGg4cK5Z75Csn6qH86Z3E": "Coinbase Hot Wallet",
                    "ASTyfS8426AuJNHd7PLgz3f9WZK4dfYg96WkXmF5NquS": "Kraken Hot Wallet"
                }
                label = known_exchanges.get(funding_wallet, "PRIVATE WALLET / DEEP NESTED ACCOUNT")
                print(f"  Source Type:      {Fore.LIGHTMAGENTA_EX}{label}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}[X] Could not resolve funding wallet for the master wallet.")

if __name__ == "__main__":
    asyncio.run(main())
