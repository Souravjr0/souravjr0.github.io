import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

async def check():
    async with httpx.AsyncClient() as client:
        sigs = [
            "PMKa2QWdaFQ1hqMyYdScAWb4fZn3kLBtkSpf37hfmb9EWSKhFAbK6o7Bnyf93n5GanrBG6pJPcn74a7P8JDmnpM", # Sig [7] (VEE3)
            "QrGbAaL7GBNYUKVwqTFwnqirff3Ps9FBi8HQNb4ouBrT9R6UDHqJGzbdLfELgSoPRiwYFBeQshWkRLXgeripLzb", # Sig [6] (1 riyal)
            "2QMJMfcrCpqw57V2MmoKYfkVQ4sC8AxtG7JicCx4uqvVuUNramDdoRXxZWRqhQY3bMxfZth8K2fi17qDLH4fEaCP"  # Sig [4] (aave)
        ]
        
        for idx, sig in enumerate(sigs):
            print(f"\nAnalyzing Sig [{idx+1}]: {sig[:15]}...")
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            })
            tx_data = resp.json().get("result")
            if not tx_data:
                print("  Failed to fetch transaction details!")
                continue
                
            meta = tx_data.get("meta", {})
            print(f"  Err: {meta.get('err')}")
            
            # Print token balance changes
            pre_token = meta.get("preTokenBalances", [])
            post_token = meta.get("postTokenBalances", [])
            
            print("  Token Balance Changes:")
            if not pre_token and not post_token:
                print("    None detected!")
            else:
                for pt in post_token:
                    owner = pt.get("owner")
                    mint = pt.get("mint")
                    amount = pt.get("uiTokenAmount", {}).get("uiAmount")
                    if owner == "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb":
                        print(f"    Owner: {owner[:10]}... | Mint: {mint} | Post Amount: {amount}")

asyncio.run(check())
