import asyncio
import httpx
import json

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

async def check():
    async with httpx.AsyncClient() as client:
        sig = "PMKa2QWdaFQ1hqMyYdScAWb4fZn3kLBtkSpf37hfmb9EWSKhFAbK6o7Bnyf93n5GanrBG6pJPcn74a7P8JDmnpM" # VEE3
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        })
        tx_data = resp.json().get("result")
        if not tx_data:
            print("Failed to fetch transaction details!")
            return
            
        print(json.dumps(tx_data, indent=2))

asyncio.run(check())
