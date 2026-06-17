import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
ivy_mint = "9DUH5VBQdi4nzfTfq4ypFWb1TeAg4WTaDy4wGvDUpump"

async def check():
    async with httpx.AsyncClient() as client:
        # Fetch signatures for wallet
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 20}]
        }
        resp = await client.post(url, json=payload)
        sigs = resp.json().get("result", [])
        print(f"Checking last {len(sigs)} transactions for IVY activity...")
        
        for sig_info in sigs:
            sig = sig_info["signature"]
            tx_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            }
            tx_resp = await client.post(url, json=tx_payload)
            tx_data = tx_resp.json().get("result")
            if not tx_data:
                continue
            
            # Check if IVY mint is in the transaction
            tx_str = str(tx_data)
            if ivy_mint in tx_str:
                print(f"\n[+] Found transaction involving IVY: {sig}")
                meta = tx_data.get("meta", {})
                
                # Try parsing SOL balance changes
                pre_bal = meta.get("preBalances", [])
                post_bal = meta.get("postBalances", [])
                account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
                
                wallet_idx = -1
                for idx, key in enumerate(account_keys):
                    addr = key["pubkey"] if isinstance(key, dict) else key
                    if addr == wallet_addr:
                        wallet_idx = idx
                        break
                
                if wallet_idx != -1:
                    sol_spent = (pre_bal[wallet_idx] - post_bal[wallet_idx]) / 1e9
                    print(f"    SOL Spent (including fees): {sol_spent:.6f} SOL")
                
                # Check token balance change
                post_token_balances = meta.get("postTokenBalances", [])
                for tb in post_token_balances:
                    if tb.get("mint") == ivy_mint and tb.get("owner") == wallet_addr:
                        amt = tb.get("uiTokenAmount", {}).get("uiAmount")
                        print(f"    Token amount received: {amt} IVY")

asyncio.run(check())
