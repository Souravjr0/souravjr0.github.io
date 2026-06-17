import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

async def main():
    sig = "3WhmfPymyWfRzv6ZJpP2B8ydTGNg1f2HSnujRpBeN5bVkp2fAQ4E2MQb3u92S2h1CYdZug5oDFCXMkdi9f5Qz1Rz"
    async with httpx.AsyncClient() as client:
        payload_tx = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        tx_resp = await client.post(RPC_HTTP, json=payload_tx, timeout=10.0)
        tx_data = tx_resp.json().get("result")
        
        with open("scratch/tx_example.json", "w") as f:
            json.dump(tx_data, f, indent=2)
            
    print("Wrote transaction data to scratch/tx_example.json")

asyncio.run(main())
