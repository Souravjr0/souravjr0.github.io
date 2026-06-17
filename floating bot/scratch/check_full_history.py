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
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [wallet_addr, {"limit": 40}]
        })
        signatures = resp.json().get("result", [])
        print(f"Total signatures fetched: {len(signatures)}")
        for idx, sig_info in enumerate(signatures):
            sig = sig_info["signature"]
            err = sig_info.get("err")
            slot = sig_info.get("slot")
            block_time = sig_info.get("blockTime")
            time_str = datetime.utcfromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S') if block_time else "Unknown"
            print(f"  {idx+1:2d}. Sig: {sig}")
            print(f"      Slot: {slot} | Time: {time_str} UTC | Err: {err}")

asyncio.run(check())
