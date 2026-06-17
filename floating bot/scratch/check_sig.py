import os
import asyncio
import httpx
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    
    buy_sig = "3rbRvHEhzrvVsQvXVJyedYWzCJ6DzhghVVtiR53WtXTdjCMfZ2gNbHLynKo3s6HMNmW9VXkWeU71uXB8fFUPtc7C"
    sell_sig = "6mro1bXuhp44T1RRNAin7iwwKXzudm7qGMHQf7ZgFqr793RjCXMXy7jPcvpQo1beRaSqrYce4iRj7rsKDNgCrJ4"
    
    async with httpx.AsyncClient() as client:
        for name, sig in [("Buy", buy_sig), ("Sell", sell_sig)]:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignatureStatuses",
                "params": [[sig]]
            }
            resp = await client.post(rpc_url, json=payload)
            print(f"=== {name} Status ===")
            print(resp.json())

if __name__ == "__main__":
    asyncio.run(main())
