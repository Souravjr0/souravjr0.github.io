import httpx
import base64

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    # Let's list the top 10 pools we found earlier:
    pools = {
        "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv": "Raydium CLMM (massive)",
        "8sLbNZoA1cfnvMJLPfp98ZLAnFSYCFApfJKMbiXNLwxj": "Raydium CLMM #3",
        "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv": "Raydium CLMM #4 (Gecko 0.05%)",
        "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq": "Raydium CLMM #5"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [list(pools.keys()), {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        value = response.json()["result"]["value"]
        
        for idx, val in enumerate(value):
            pool_id = list(pools.keys())[idx]
            name = pools[pool_id]
            if not val:
                print(f"Pool {pool_id} not found!")
                continue
            raw = base64.b64decode(val["data"][0])
            
            # Parse sqrt_price from offset 324
            sqrt_price_bytes = raw[324:324+16]
            sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
            
            p_sol = (sqrt_price / (2**64)) ** 2 * 1000
            p_sol_inv = 1 / ((sqrt_price / (2**64)) ** 2 / 1000) if sqrt_price > 0 else 0
            
            print(f"Pool: {pool_id} ({name})")
            print(f"  sqrt_price: {sqrt_price}")
            print(f"  Price (std): ${p_sol:.4f}")
            print(f"  Price (inv): ${p_sol_inv:.4f}")
            print("-" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
