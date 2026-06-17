import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # Get SOL balance
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getBalance",
            "params": [wallet_addr]
        })
        sol_bal = resp.json().get("result", {}).get("value", 0) / 1e9
        print(f"SOL Balance: {sol_bal:.8f} SOL")

        # Get legacy token accounts
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        })
        result = resp.json().get("result", {}).get("value", [])
        print(f"Total Legacy Token Accounts: {len(result)}")
        for item in result:
            info = item["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            print(f"  Account: {item['pubkey']} | Mint: {mint} | Balance: {amount:,.8f}")

asyncio.run(check())
