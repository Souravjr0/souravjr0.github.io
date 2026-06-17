import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 20}]
        })
        
        result = resp.json().get("result", [])
        print(f"Last 20 transactions for {wallet_addr}:")
        for idx, item in enumerate(result):
            print(f"  [{idx}] Signature: {item['signature']} | Slot: {item['slot']} | Err: {item['err']} | Time: {item['blockTime']}")

asyncio.run(check())
