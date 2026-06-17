import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

failed_sigs = [
    "3vdinhRfHJ4MUS7o9ix2BiR7ixC3wzYBSfjzBj1HN27zwHG1BFf65yStfzrBAi4QGtFQMZp1hSWUx31ZbQK6iAcU",
    "3Y9K9tgQrLNBRhLTr23bT7am57t9cCXLsUtDRoJaCaegCQFS2oWWRR3k59ogFPTrnFUxi3NXCh9Drewj9VauXeQH",
    "5QZr4aB2yWuEgVvZbCTH9tJNbHqyxMHVMh33nAXwQCGQzU9wgJwjL3MXKwFU95t5neakoHBQyiVtQJdo8CyDMJRE"
]

async def check():
    async with httpx.AsyncClient() as client:
        for sig in failed_sigs:
            print(f"\n==========================================")
            print(f"Failed Signature: {sig}")
            resp = await client.post(url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    sig,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                ]
            })
            res = resp.json().get("result")
            if not res:
                print("  Not found:", resp.json())
                continue
            meta = res.get("meta", {})
            tx = res.get("transaction", {})
            err = meta.get("err")
            fee = meta.get("fee", 0) / 1e9
            print(f"  Error: {err}")
            print(f"  Tx Fee: {fee:.8f} SOL")
            
            # Print balance changes
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            account_keys = tx.get("message", {}).get("accountKeys", [])
            for i, acc in enumerate(account_keys):
                pk = acc.get("pubkey") if isinstance(acc, dict) else acc
                diff = (post_balances[i] - pre_balances[i]) / 1e9
                if diff != 0:
                    print(f"    {pk}: {diff:+.8f} SOL")
                    
asyncio.run(check())
