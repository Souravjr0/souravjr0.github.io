#!/usr/bin/env python3
"""
KOL Wallet Deep-Profile Audit Utility
cook45 & clack // Systems & MEV

Profiles the KOL address AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN:
1. Live SOL balance.
2. Active token holdings (pump.fun and other SPL).
3. Recent transaction signatures and actions.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

async def profile_kol():
    load_dotenv()
    api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    kol_addr = "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN"

    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          KOL TARGET DEEP-PROFILE AUDIT          ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")
    print(f"[+] Target KOL Address: {Fore.YELLOW}{kol_addr}{Style.RESET_ALL}\n")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch SOL Balance
        payload_sol = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getBalance",
            "params": [kol_addr]
        }
        try:
            resp = await client.post(url, json=payload_sol)
            if resp.status_code == 200:
                sol_bal = resp.json().get("result", {}).get("value", 0) / 1e9
                print(f"[+] Live SOL Balance: {Fore.GREEN}{sol_bal:.6f} SOL{Style.RESET_ALL}")
            else:
                print(f"[X] Failed to fetch SOL balance: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Error fetching SOL balance: {e}")

        # 2. Fetch SPL Token Accounts
        payload_tokens = {
            "jsonrpc": "2.0", "id": 2,
            "method": "getTokenAccountsByOwner",
            "params": [
                kol_addr,
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
                
                print("\n--- Active Token Holdings ---")
                if not active_tokens:
                    print("  No active token balances (completely sold or dumped!).")
                else:
                    for mint, amount in active_tokens:
                        mint_label = f"{Fore.LIGHTMAGENTA_EX}(Pump.fun){Style.RESET_ALL}" if mint.endswith("pump") else ""
                        print(f"  Mint: {Fore.CYAN}{mint:<44}{Style.RESET_ALL} | Balance: {Fore.LIGHTCYAN_EX}{amount:,.2f}{Style.RESET_ALL} {mint_label}")
            else:
                print(f"[X] Failed to fetch token accounts: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Error fetching token accounts: {e}")

        # 3. Fetch Recent Signatures
        payload_sigs = {
            "jsonrpc": "2.0", "id": 3,
            "method": "getSignaturesForAddress",
            "params": [kol_addr, {"limit": 5}]
        }
        try:
            resp = await client.post(url, json=payload_sigs)
            if resp.status_code == 200:
                sigs = resp.json().get("result", [])
                print(f"\n--- Last {len(sigs)} Transactions Audit ---")
                for s in sigs:
                    sig = s["signature"]
                    err = s.get("err")
                    slot = s.get("slot")
                    status = f"{Fore.RED}FAILED{Style.RESET_ALL}" if err else f"{Fore.GREEN}SUCCESS{Style.RESET_ALL}"
                    print(f"  Sig:  {sig[:12]}... | Slot: {slot} | Status: {status}")
            else:
                print(f"[X] Failed to fetch recent signatures: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Error fetching signatures: {e}")

if __name__ == "__main__":
    asyncio.run(profile_kol())
