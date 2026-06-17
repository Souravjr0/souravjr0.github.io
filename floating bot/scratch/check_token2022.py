import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # Query Token-2022 accounts
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenzQdBNbXtNNfeNETCZ64uu5R75tTqtMZVvob39"},
                {"encoding": "jsonParsed"}
            ]
        })
        
        result = resp.json().get("result", {}).get("value", [])
        print(f"Token-2022 Accounts ({len(result)} found):")
        for item in result:
            info = item["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            print(f"  Mint: {mint} | Balance: {amount}")

asyncio.run(check())
