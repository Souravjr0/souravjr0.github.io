import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
sig = "2UmpuJD7bPYy3GADRhqDFM2zdzKqL2Q9VFByPLJYBHqrTf1tdFBtQxxAbQf8dyvc5g32VMhKwGtVDBBUTv28SKQM"

async def check():
    async with httpx.AsyncClient() as client:
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
            print("Not found:", resp.json())
            return
        meta = res.get("meta", {})
        tx = res.get("transaction", {})
        print("Meta:", meta.get("err"))
        print("Pre Token Balances:", meta.get("preTokenBalances"))
        print("Post Token Balances:", meta.get("postTokenBalances"))
        
        # Account balance changes
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        account_keys = tx.get("message", {}).get("accountKeys", [])
        for i, acc in enumerate(account_keys):
            pk = acc.get("pubkey") if isinstance(acc, dict) else acc
            diff = (post_balances[i] - pre_balances[i]) / 1e9
            if diff != 0:
                print(f"  {pk}: {diff:+.6f} SOL")

asyncio.run(check())
