import httpx

async def main():
    url = "https://api-v3.raydium.io/pools/info/mint"
    params = {
        "mint1": "So11111111111111111111111111111111111111112",
        "mint2": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "poolType": "all",
        "poolSortField": "liquidity",
        "sortType": "desc",
        "pageSize": 10,
        "page": 1
    }
    
    print("[+] Querying Raydium API for top 10 pools by liquidity...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[-] Error: HTTP status {response.status_code}")
                print(response.text)
                return
                
            data = response.json()
            if not data or "data" not in data or not data["data"]:
                print("[-] No pools found.")
                return
                
            pools = data["data"]["data"]
            print(f"[+] Found {len(pools)} pools:")
            for p in pools:
                print(f"Pool ID: {p['id']}")
                print(f"  Program ID: {p.get('programId')}")
                print(f"  TVL: ${p.get('tvl', 0):,.2f}")
                print(f"  24h Volume: ${p.get('day', {}).get('volume', 0):,.2f}")
                print(f"  Mint A: {p.get('mintA', {}).get('symbol')}")
                print(f"  Mint B: {p.get('mintB', {}).get('symbol')}")
                print("-" * 50)
        except Exception as e:
            print(f"[-] Request failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
