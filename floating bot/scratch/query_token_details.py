import asyncio
import httpx

mint = "9DUH5VBQdi4nzfTfq4ypFWb1TeAg4WTaDy4wGvDUpump"
url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"

async def check():
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            if not pairs:
                print(f"[~] No active DexScreener pools found for {mint}.")
                # Let's query pump.fun bonding curve or Jupiter API if dexscreener has no pool
                # Let's check pump.fun bonding curve details
                return
            
            pair = pairs[0]
            print("==================================================")
            print("                TOKEN DETAILS                    ")
            print("==================================================")
            print(f"Name: {pair.get('baseToken', {}).get('name')}")
            print(f"Symbol: {pair.get('baseToken', {}).get('symbol')}")
            print(f"Price (USD): ${pair.get('priceUsd')}")
            print(f"Price (Native): {pair.get('priceNative')} SOL")
            print(f"Liquidity (USD): ${pair.get('liquidity', {}).get('usd')}")
            print(f"Market Cap (USD): ${pair.get('fdv')}")
            print(f"Volume (24h): ${pair.get('volume', {}).get('h24')}")
            print("==================================================")
        else:
            print(f"[X] DexScreener API error: HTTP {resp.status_code}")

asyncio.run(check())
