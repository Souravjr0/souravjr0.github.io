import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
sig = "2qXFvnLhNXRyC9FBVxxuHQ2PMDWMNJuGSqWWhmzXTHnrJisbETHXgXiU6MnRr7XxmPf3PJqBkKq3tbhqWu4epBCS"

async def inspect():
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        resp = await client.post(url, json=payload)
        data = resp.json()
        result = data.get("result", {})
        meta = result.get("meta", {})
        
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        account_keys = result.get("transaction", {}).get("message", {}).get("accountKeys", [])
        
        wallet_index = -1
        for idx, acc in enumerate(account_keys):
            pub = acc.get("pubkey") if isinstance(acc, dict) else acc
            if pub == wallet_addr:
                wallet_index = idx
                break
        
        sol_change = (post_balances[wallet_index] - pre_balances[wallet_index]) / 1e9
        print(f"Success: {meta.get('err') is None} | SOL Change: {sol_change:+.6f} SOL | Slot: {result.get('slot')}")
        
        pre_token = meta.get("preTokenBalances", [])
        post_token = meta.get("postTokenBalances", [])
        
        changes = {}
        for item in pre_token:
            owner = item.get("owner")
            mint = item.get("mint")
            amount = float(item.get("uiTokenAmount", {}).get("uiAmount") or 0)
            changes[(owner, mint)] = {"pre": amount, "post": 0, "symbol": item.get("uiTokenAmount", {}).get("symbol")}
            
        for item in post_token:
            owner = item.get("owner")
            mint = item.get("mint")
            amount = float(item.get("uiTokenAmount", {}).get("uiAmount") or 0)
            if (owner, mint) in changes:
                changes[(owner, mint)]["post"] = amount
            else:
                changes[(owner, mint)] = {"pre": 0, "post": amount, "symbol": item.get("uiTokenAmount", {}).get("symbol")}
                
        for (owner, mint), info in changes.items():
            if info["pre"] != info["post"] and owner == wallet_addr:
                print(f"  Owner: WALLET | Mint: {mint} | Change: {info['pre']} -> {info['post']} {info['symbol'] or ''}")

asyncio.run(inspect())
