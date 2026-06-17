import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAssetsByOwner",
            "params": {
                "ownerAddress": wallet_addr,
                "page": 1,
                "limit": 10,
                "displayOptions": {
                    "showFungible": False
                }
            }
        }
        resp = await client.post(url, json=payload)
        res = resp.json().get("result", {})
        items = res.get("items", [])
        
        print(f"Inspecting first {len(items)} NFTs:")
        for idx, item in enumerate(items):
            print(f"NFT {idx+1}:")
            print(f"  ID/Mint: {item.get('id')}")
            print(f"  Interface: {item.get('interface')}")
            print(f"  Content: {item.get('content', {}).get('metadata', {})}")

asyncio.run(check())
