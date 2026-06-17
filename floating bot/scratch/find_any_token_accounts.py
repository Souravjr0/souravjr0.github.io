import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # 1. Check Standard Token Program
        resp1 = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        })
        res1 = resp1.json().get("result", {}).get("value", [])
        
        # 2. Check Token2022 Program
        resp2 = await client.post(url, json={
            "jsonrpc": "2.0", "id": 2, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXWayc8T7"},
                {"encoding": "jsonParsed"}
            ]
        })
        res2 = resp2.json().get("result", {}).get("value", [])
        
        all_accounts = res1 + res2
        print(f"Total Token Accounts Found: {len(all_accounts)}")
        for acc in all_accounts:
            pubkey = acc["pubkey"]
            info = acc["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            decimals = info["tokenAmount"].get("decimals")
            program = acc["account"]["owner"]
            print(f"  Account: {pubkey} | Program: {program[:12]}... | Mint: {mint} | Balance: {amount:,.6f}")

asyncio.run(check())
