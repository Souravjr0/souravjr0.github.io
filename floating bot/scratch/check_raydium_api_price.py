import httpx

async def main():
    url = "https://api-v3.raydium.io/pools/info/ids"
    # Pool IDs we want to inspect
    ids = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv,CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq,2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv"
    params = {"ids": ids}
    
    print("[+] Querying Raydium API for price and state details...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[-] Error: HTTP status {response.status_code}")
                return
            data = response.json()
            if not data or "data" not in data or not data["data"]:
                print("[-] No pools found.")
                return
            
            pools = data["data"]
            for p in pools:
                print(f"Pool ID: {p['id']}")
                print(f"  Price: {p.get('price')}")
                print(f"  TVL: ${p.get('tvl', 0):,.2f}")
                print(f"  Mint A: {p.get('mintA', {}).get('symbol')} ({p.get('mintA', {}).get('address')})")
                print(f"  Mint B: {p.get('mintB', {}).get('symbol')} ({p.get('mintB', {}).get('address')})")
                print("-" * 50)
        except Exception as e:
            print(f"[-] Request failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
