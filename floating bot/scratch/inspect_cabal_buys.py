import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # Get signatures
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 15}]
        })
        signatures = resp.json().get("result", [])
        
        for idx, sig_info in enumerate(signatures):
            sig = sig_info["signature"]
            err = sig_info.get("err")
            slot = sig_info.get("slot")
            
            print(f"\n[{idx+1}] Signature: {sig}")
            print(f"    Slot: {slot} | Err: {err}")
            
            tx_resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            })
            tx_data = tx_resp.json().get("result")
            if not tx_data:
                print("    Failed to fetch transaction details!")
                continue
                
            meta = tx_data.get("meta", {})
            pre_bal = meta.get("preBalances", [])
            post_bal = meta.get("postBalances", [])
            account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
            
            wallet_idx = -1
            for k_idx, acc_key in enumerate(account_keys):
                pub = acc_key.get("pubkey") if isinstance(acc_key, dict) else acc_key
                if pub == wallet_addr:
                    wallet_idx = k_idx
                    break
                    
            if wallet_idx != -1:
                change = (post_bal[wallet_idx] - pre_bal[wallet_idx]) / 1e9
                print(f"    Wallet SOL Change: {change:+.8f} SOL")

asyncio.run(check())
