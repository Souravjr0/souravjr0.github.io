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
        
        print(f"Analyzing last {len(signatures)} transactions for wallet {wallet_addr}...\n")
        
        for idx, sig_info in enumerate(signatures):
            sig = sig_info["signature"]
            err = sig_info.get("err")
            slot = sig_info.get("slot")
            
            # Fetch full transaction details
            tx_resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [
                    sig,
                    {"encoding": "json", "maxSupportedTransactionVersion": 0}
                ]
            })
            
            tx_data = tx_resp.json().get("result")
            if not tx_data:
                print(f"  [{idx+1}] Sig: {sig} | Could not fetch tx details")
                continue
                
            meta = tx_data.get("meta", {})
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
            
            # Find the index of our wallet
            wallet_idx = -1
            for k_idx, acc_key in enumerate(account_keys):
                if isinstance(acc_key, dict):
                    pub = acc_key.get("pubkey")
                else:
                    pub = acc_key
                if pub == wallet_addr:
                    wallet_idx = k_idx
                    break
            
            net_change = 0
            if wallet_idx != -1 and wallet_idx < len(pre_balances) and wallet_idx < len(post_balances):
                net_change = (post_balances[wallet_idx] - pre_balances[wallet_idx]) / 1e9
                
            err_str = f"| ERR: {err}" if err else "| SUCCESS"
            print(f"  [{idx+1}] Sig: {sig[:10]}...{sig[-10:]} | Slot: {slot} {err_str}")
            print(f"      Net SOL Change for Wallet: {net_change:+.8f} SOL")

asyncio.run(check())
