import asyncio
import httpx

mints = {
    "Gw75Y2znwcBYZWGmXsByFCmAEKT7ojNQ7VLTf2BxgHFL": 138679.465273,
    "2eg9bHSdZMWiVwJMBdCiG6G72xhKwiv3sevyAsr5pump": 164861.315545,
    "6fmPRN4YW661XXiaeY4cnaNJpMLgvdF9XW6FLvaprnRX": 139209.631801
}

async def check():
    async with httpx.AsyncClient() as client:
        # Get SOL price in USDC from Jupiter
        sol_price_resp = await client.get("https://api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112")
        sol_price = sol_price_resp.json().get("data", {}).get("So11111111111111111111111111111111111111112", {}).get("price", 82.5)
        print(f"Current SOL Price: ${sol_price:.2f} USDC\n")
        
        for mint, bal in mints.items():
            print(f"Mint: {mint}")
            print(f"  Wallet Balance: {bal:,.2f}")
            
            # Query Jupiter Price API
            price_url = f"https://api.jup.ag/price/v3?ids={mint}"
            resp = await client.get(price_url)
            price_data = resp.json().get("data", {}).get(mint, {})
            price_usd = price_data.get("price")
            
            if price_usd is not None:
                val_usd = bal * price_usd
                val_sol = val_usd / sol_price
                print(f"  Jupiter Price: ${price_usd:.8f} USDC")
                print(f"  Current Value: ${val_usd:.4f} USDC (~{val_sol:.6f} SOL)")
            else:
                print(f"  Jupiter Price: Not found")
                
            # If it is a pump.fun token, check pump.fun price
            if mint.endswith("pump"):
                try:
                    pumpportal_url = f"https://frontend-api.pump.fun/coins/{mint}"
                    p_resp = await client.get(pumpportal_url)
                    p_data = p_resp.json()
                    usd_market_cap = float(p_data.get("usd_market_cap", 0))
                    # Pump.fun total supply is 1,000,000,000
                    p_price = usd_market_cap / 1e9
                    val_usd = bal * p_price
                    val_sol = val_usd / sol_price
                    print(f"  Pump.fun Price: ${p_price:.8f} USDC (Mcap: ${usd_market_cap:,.2f})")
                    print(f"  Pump.fun Value: ${val_usd:.4f} USDC (~{val_sol:.6f} SOL)")
                except Exception as e:
                    print(f"  Error fetching pump.fun data: {e}")

asyncio.run(check())
