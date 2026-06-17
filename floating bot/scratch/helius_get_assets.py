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
        # Call Helius getAssetsByOwner DAS API
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAssetsByOwner",
            "params": {
                "ownerAddress": wallet_addr,
                "page": 1,
                "limit": 100,
                "displayOptions": {
                    "showFungible": True,
                    "showNativeBalance": True
                }
            }
        }
        resp = await client.post(url, json=payload)
        res = resp.json().get("result", {})
        
        print("Helius DAS API getAssetsByOwner response:")
        print("==================================================")
        items = res.get("items", [])
        print(f"Total assets returned: {len(items)}")
        for idx, item in enumerate(items):
            print(f"\nAsset {idx+1}:")
            print(f"  ID/Mint: {item.get('id')}")
            print(f"  Interface: {item.get('interface')}")
            
            # Content / metadata
            content = item.get("content", {})
            metadata = content.get("metadata", {})
            title = metadata.get("title") or item.get("id")
            print(f"  Name/Title: {title}")
            
            # Token info
            token_info = item.get("token_info", {})
            balance = token_info.get("balance")
            decimals = token_info.get("decimals")
            price_info = token_info.get("price_info", {})
            
            if balance is not None:
                ui_bal = float(balance) / (10**decimals) if decimals else float(balance)
                print(f"  Balance: {ui_bal:,.6f}")
                if price_info:
                    print(f"  Price Info: {price_info}")
            else:
                print("  No balance info (likely NFT)")
                
        # Native balance
        native_bal = res.get("nativeBalance")
        if native_bal:
            lamports = float(native_bal.get("lamports", 0))
            print(f"\nNative SOL Balance: {lamports / 1e9:.8f} SOL")

asyncio.run(check())
