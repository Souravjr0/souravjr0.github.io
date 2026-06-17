import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

async def main():
    sig = "EtH3pDvhzufvwcXDJiaNNKW23MpUztVyPVmRLNTBrLjhRwgWJFiVnzp3ze2XQmwJHEaJh2CrSxZQbtrL6nP4tms"
    wallet = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
    
    async with httpx.AsyncClient() as client:
        payload_tx = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        tx_resp = await client.post(RPC_HTTP, json=payload_tx, timeout=10.0)
        tx_data = tx_resp.json().get("result")
        if not tx_data:
            print("Failed to get transaction.")
            return
            
        meta = tx_data.get("meta", {})
        err = meta.get("err")
        print(f"Transaction Err: {err}")
        
        # Print token balance changes
        post_balances = meta.get("postTokenBalances", [])
        pre_balances = meta.get("preTokenBalances", [])
        for b in pre_balances:
            if b.get("owner") == wallet:
                print(f"Pre Token Balance -> Mint: {b.get('mint')}, Amount: {b.get('uiTokenAmount', {}).get('uiAmount')}")
        for b in post_balances:
            if b.get("owner") == wallet:
                print(f"Post Token Balance -> Mint: {b.get('mint')}, Amount: {b.get('uiTokenAmount', {}).get('uiAmount')}")

asyncio.run(main())
