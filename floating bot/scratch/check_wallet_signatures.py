import os
import asyncio
import httpx
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    wallet = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
    
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet, {"limit": 5}]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(rpc_url, json=payload)
        sigs = resp.json().get("result", [])
        print("=== Last 5 Signatures ===")
        for s in sigs:
            print(f"Signature: {s.get('signature')}")
            print(f"  Slot: {s.get('slot')}")
            print(f"  Error: {s.get('err')}")
            print(f"  Memo: {s.get('memo')}")

if __name__ == "__main__":
    asyncio.run(main())
