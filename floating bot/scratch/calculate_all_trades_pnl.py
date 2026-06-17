import asyncio
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # Fetch 40 transactions
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 40}]
        })
        signatures = resp.json().get("result", [])
        
        # We process them in chronological order (oldest first)
        signatures.reverse()
        
        print("Chronological Transaction Log & Balance Impact (SOL):")
        print("=" * 110)
        print(f"{'Time (UTC)':<20} | {'Signature':<44} | {'Err':<8} | {'Wallet Change (SOL)':<20}")
        print("=" * 110)
        
        current_balance = None
        
        for sig_info in signatures:
            sig = sig_info["signature"]
            err = sig_info.get("err")
            block_time = sig_info.get("blockTime")
            time_str = datetime.utcfromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S') if block_time else "Unknown"
            
            # Fetch tx details
            resp_tx = await client.post(url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    sig,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                ]
            })
            tx_res = resp_tx.json().get("result")
            if not tx_res:
                continue
                
            meta = tx_res.get("meta", {})
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            account_keys = tx_res.get("transaction", {}).get("message", {}).get("accountKeys", [])
            
            wallet_idx = -1
            for idx, acc in enumerate(account_keys):
                pk = acc.get("pubkey") if isinstance(acc, dict) else acc
                if pk == wallet_addr:
                    wallet_idx = idx
                    break
                    
            if wallet_idx != -1:
                pre = pre_balances[wallet_idx] / 1e9
                post = post_balances[wallet_idx] / 1e9
                diff = post - pre
                err_str = "SUCCESS" if err is None else "FAILED"
                print(f"{time_str:<20} | {sig:<44} | {err_str:<8} | {diff:+.8f} SOL")
                
asyncio.run(check())
