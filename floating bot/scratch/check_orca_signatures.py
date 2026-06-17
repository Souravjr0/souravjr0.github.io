import httpx

async def get_recent_signatures(rpc_url: str, address: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [address, {"limit": 10}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result")
        return res

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    orca_pool = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
    
    print(f"Pool: {orca_pool} (Orca Whirlpool)")
    sigs = await get_recent_signatures(rpc_url, orca_pool)
    if sigs:
        print(f"  Fetched {len(sigs)} recent signatures:")
        for s in sigs:
            print(f"    Slot: {s.get('slot')}, Err: {s.get('err')}, Memo: {s.get('memo')}")
    else:
        print("  No recent signatures found.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
