import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
mints = [
    "6fmPRN4YW661XXiaeY4cnaNJpMLgvdF9XW6FLvaprnRX",
    "2eg9bHSdZMWiVwJMBdCiG6G72xhKwiv3sevyAsr5pump",
    "Gw75Y2znwcBYZWGmXsByFCmAEKT7ojNQ7VLTf2BxgHFL"
]

async def check():
    async with httpx.AsyncClient() as client:
        for mint in mints:
            # Query token accounts by owner and mint
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_addr,
                    {"mint": mint},
                    {"encoding": "jsonParsed"}
                ]
            })
            
            result = resp.json().get("result", {}).get("value", [])
            print(f"Mint: {mint} | Accounts found: {len(result)}")
            for item in result:
                pubkey = item["pubkey"]
                info = item["account"]["data"]["parsed"]["info"]
                amount = info["tokenAmount"].get("uiAmountString")
                print(f"  Account Pubkey: {pubkey} | Balance: {amount}")

asyncio.run(check())
