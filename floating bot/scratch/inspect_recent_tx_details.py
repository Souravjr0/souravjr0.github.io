import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

signatures = [
    "39oWtJLgfuS8Ha21CKPuudGouPdH5X8Qorq79b64EzqvEmk3utrHR7zTQ6joANvsybkXxMWdbWF2PH26WbU1PonJ",
    "HExwoV8cjczjQZ4AzVDzHZpi3pJqEryUH7x2sohwM144b9E4Rg4dTGxCFgTuijJzJbAoJK3yfDXKGoYLSS6E9rP",
    "3koMNQz4Qsy1vRob6ibEDz7x7PY7apJzabWJo6obzpxHH6VjF5z3szgeay1BYBquzkgtMNAuMCLnrfCDTyoX6jD1",
    "2Gw57qYubRtgqofJJVZCMZVgTxdiafjCcLd5Fc9f3SPRwxGResDa1EDifmJMErpURTfFsR2KNQ7VrtzFwB7EimV1",
    "4QBtpEYXcLwQMhk3KruLNmewrs4uaSp8tHnqYphP2KpUgGC3EvHj9SKWzqsRW5YdZF6d2eZCu2LGQg6CB1o5KjBG"
]

async def check():
    async with httpx.AsyncClient() as client:
        for sig in signatures:
            print(f"\n==========================================")
            print(f"Signature: {sig}")
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
                print("  Not found or error:", resp.json())
                continue
                
            meta = res.get("meta", {})
            tx = res.get("transaction", {})
            err = meta.get("err")
            print(f"  Slot: {res.get('slot')}")
            print(f"  Error: {err}")
            
            # Print balance changes
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            account_keys = tx.get("message", {}).get("accountKeys", [])
            
            # Try to map accounts to names
            accounts = []
            for i, acc in enumerate(account_keys):
                if isinstance(acc, dict):
                    pubkey = acc.get("pubkey")
                else:
                    pubkey = acc
                pre = pre_balances[i] if i < len(pre_balances) else 0
                post = post_balances[i] if i < len(post_balances) else 0
                diff = (post - pre) / 1e9
                accounts.append((pubkey, pre / 1e9, post / 1e9, diff))
                
            print("  Account Balance Changes (SOL):")
            for pubkey, pre, post, diff in accounts:
                if diff != 0:
                    print(f"    {pubkey[:10]}...: {pre:.6f} -> {post:.6f} (diff: {diff:+.6f} SOL)")
            
            # Token changes
            pre_token = meta.get("preTokenBalances", [])
            post_token = meta.get("postTokenBalances", [])
            
            token_changes = {}
            for tb in pre_token:
                owner = tb.get("owner")
                mint = tb.get("mint")
                amount = float(tb.get("uiTokenAmount", {}).get("uiAmount") or 0)
                token_changes[(owner, mint)] = {"pre": amount, "post": 0}
            for tb in post_token:
                owner = tb.get("owner")
                mint = tb.get("mint")
                amount = float(tb.get("uiTokenAmount", {}).get("uiAmount") or 0)
                if (owner, mint) in token_changes:
                    token_changes[(owner, mint)]["post"] = amount
                else:
                    token_changes[(owner, mint)] = {"pre": 0, "post": amount}
                    
            print("  Token Balance Changes:")
            for (owner, mint), balance in token_changes.items():
                diff = balance["post"] - balance["pre"]
                if diff != 0 or balance["pre"] != 0:
                    print(f"    Owner: {owner[:8]}... | Mint: {mint} | {balance['pre']:,} -> {balance['post']:,} (diff: {diff:+,.6f})")

            # Logs snippet
            log_messages = meta.get("logMessages", [])
            print("  Logs (truncated):")
            for log in log_messages[:15]:
                print(f"    {log}")
            if len(log_messages) > 15:
                print(f"    ... and {len(log_messages) - 15} more logs")

asyncio.run(check())
