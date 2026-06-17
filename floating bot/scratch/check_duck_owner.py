import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
duck_mint = "JDh9gvuWP1FmkJ7t37JXrvVLPQtKajKEs8s2D4rspump"

async def check():
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [duck_mint, {"encoding": "jsonParsed"}]
        })
        print(resp.json())

asyncio.run(check())
