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
        page = 1
        all_fungible = []
        all_nfts = 0
        
        while True:
            payload = {
                "jsonrpc": "2.0",
                "id": page,
                "method": "getAssetsByOwner",
                "params": {
                    "ownerAddress": wallet_addr,
                    "page": page,
                    "limit": 1000,
                    "displayOptions": {
                        "showFungible": True,
                        "showNativeBalance": True
                    }
                }
            }
            resp = await client.post(url, json=payload)
            res = resp.json().get("result", {})
            items = res.get("items", [])
            if not items:
                break
                
            for item in items:
                token_info = item.get("token_info", {})
                interface = item.get("interface", "")
                
                # Check if it has token_info (balance/fungible)
                if token_info or interface in ["FungibleToken", "FungibleAsset"]:
                    balance = token_info.get("balance", "0")
                    decimals = token_info.get("decimals", 0)
                    ui_bal = float(balance) / (10**decimals) if decimals else float(balance)
                    
                    if ui_bal > 0:
                        all_fungible.append((item.get("id"), ui_bal, item.get("content", {}).get("metadata", {}).get("title") or item.get("id")))
                else:
                    all_nfts += 1
                    
            if len(items) < 1000:
                break
            page += 1
            
        print("Fungible tokens with balance > 0:")
        print("=" * 60)
        if not all_fungible:
            print("No fungible tokens with positive balance found.")
        for mint, bal, title in all_fungible:
            print(f"Mint: {mint}")
            print(f"Name: {title}")
            print(f"Balance: {bal:,.6f}")
            print("-" * 60)
            
        print(f"\nTotal NFTs found (balance = 0 / collectible): {all_nfts}")
        
        # Get native SOL balance
        native_bal = res.get("nativeBalance")
        if native_bal:
            lamports = float(native_bal.get("lamports", 0))
            print(f"Native SOL Balance: {lamports / 1e9:.8f} SOL")

asyncio.run(check())
