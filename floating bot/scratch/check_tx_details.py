import os
import asyncio
import httpx
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    
    sig = "4bVVgeXMCh4K6oRS3wcxeCiR1PT5z6KTdZcWnLHgqdEUA2Rp5Z57FmfrcuP8nW1kgzVjcntY2WKKvf8sA1pVnoq6"
    
    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        }
        resp = await client.post(rpc_url, json=payload)
        print("=== Transaction Details ===")
        data = resp.json().get("result", {})
        if data:
            meta = data.get("meta", {})
            print("Fee:", meta.get("fee"), "lamports")
            print("Pre Balances:", meta.get("preBalances"))
            print("Post Balances:", meta.get("postBalances"))
            print("Pre Token Balances:", meta.get("preTokenBalances"))
            print("Post Token Balances:", meta.get("postTokenBalances"))
            # Print log messages
            print("Logs:")
            for log in meta.get("logMessages", []):
                print("  ", log)
        else:
            print("Transaction data not found!")

if __name__ == "__main__":
    asyncio.run(main())
