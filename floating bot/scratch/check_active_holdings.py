import os
import asyncio
import base64
import httpx
from dotenv import load_dotenv

async def check_active_holdings():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("HELIUS_API_KEY")
    rpc_http = os.getenv("HELIUS_RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={api_key}")
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    
    if not private_key_str:
        print("[X] Error: SOLANA_PRIVATE_KEY not found in .env!")
        return

    # Load Keypair
    try:
        from solders.keypair import Keypair
        try:
            keypair = Keypair.from_base58_string(private_key_str)
        except Exception:
            # Fallback to byte array parsing
            key_bytes = base64.b64decode(private_key_str) if len(private_key_str) > 64 else bytes.fromhex(private_key_str)
            keypair = Keypair.from_bytes(key_bytes)
            
        pubkey = keypair.pubkey()
        print(f"[OK] Successfully loaded keypair.")
        print(f"     Wallet Address: {pubkey}")
    except Exception as e:
        print(f"[X] Failed to load keypair from SOLANA_PRIVATE_KEY: {e}")
        return

    # Check balances via HTTP JSON-RPC to avoid heavy library dependencies
    async with httpx.AsyncClient(timeout=15.0) as http:
        # 1. Get SOL Balance
        payload_sol = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [str(pubkey)]
        }
        try:
            resp = await http.post(rpc_http, json=payload_sol)
            if resp.status_code == 200:
                val = resp.json().get("result", {}).get("value", 0)
                print(f"[+] SOL Balance: {val / 1e9:.6f} SOL")
            else:
                print(f"[X] Failed to fetch SOL balance: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Error fetching SOL balance: {e}")

        # 2. Get SPL Token Accounts
        payload_token = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getTokenAccountsByOwner",
            "params": [
                str(pubkey),
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        try:
            resp = await http.post(rpc_http, json=payload_token)
            if resp.status_code == 200:
                accounts = resp.json().get("result", {}).get("value", [])
                print(f"\nScanning {len(accounts)} token accounts for active positions...")
                
                pump_tokens = []
                other_tokens = []
                
                for acct in accounts:
                    info = acct["account"]["data"]["parsed"]["info"]
                    mint = info["mint"]
                    amount = float(info["tokenAmount"].get("uiAmount") or 0)
                    
                    if amount <= 0:
                        continue
                        
                    if mint.endswith("pump"):
                        pump_tokens.append((mint, amount))
                    else:
                        other_tokens.append((mint, amount))
                
                print("\n==================================================")
                print("           ACTIVE PUMP.FUN TOKEN HOLDINGS          ")
                print("==================================================")
                if not pump_tokens:
                    print("  No active pump.fun token holdings found in wallet.")
                for mint, amount in pump_tokens:
                    print(f"  [+] Mint: {mint:<44} | Balance: {amount:,.2f}")
                print("==================================================")
                
                if other_tokens:
                    print("\nOther SPL Token Holdings (Non-pump.fun):")
                    for mint, amount in other_tokens:
                        print(f"  [~] Mint: {mint:<44} | Balance: {amount:,.2f}")
            else:
                print(f"[X] Failed to fetch token accounts: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[X] Error fetching token accounts: {e}")

if __name__ == "__main__":
    asyncio.run(check_active_holdings())
