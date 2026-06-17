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
        # 1. Standard Token Program
        resp1 = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        })
        res1 = resp1.json().get("result", {}).get("value", [])
        
        # 2. Token-2022 Program (Correct ID)
        resp2 = await client.post(url, json={
            "jsonrpc": "2.0", "id": 2, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"},
                {"encoding": "jsonParsed"}
            ]
        })
        res2 = resp2.json().get("result", {}).get("value", [])
        
        all_accounts = res1 + res2
        print(f"Total Token Accounts: {len(all_accounts)}")
        non_zero_count = 0
        for acc in all_accounts:
            pubkey = acc["pubkey"]
            info = acc["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            decimals = info["tokenAmount"].get("decimals")
            owner_prog = acc["account"]["owner"]
            if amount > 0:
                non_zero_count += 1
                print(f"  [+] Mint: {mint}")
                print(f"      Account: {pubkey}")
                print(f"      Program: {owner_prog}")
                print(f"      Balance: {amount:,.6f}")
        if non_zero_count == 0:
            print("  No non-zero token balances found.")

asyncio.run(check())
