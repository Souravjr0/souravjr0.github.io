import httpx

async def main():
    url = "https://api-v3.raydium.io/pools/info/ids"
    # Pool IDs we want to inspect
    ids = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv,CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq"
    params = {"ids": ids}
    
    print("[+] Querying Raydium API for pool details...")
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
                print(f"  Program ID: {p.get('programId')}")
                print(f"  Fee Rate: {p.get('feeRate')}")
                print(f"  Fee Category: {p.get('feeCategory')}")
                print(f"  TVL: ${p.get('tvl', 0):,.2f}")
                print(f"  24h Volume: ${p.get('day', {}).get('volume', 0):,.2f}")
                print(f"  Config: {p.get('config')}")
                print("-" * 50)
        except Exception as e:
            print(f"[-] Request failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
