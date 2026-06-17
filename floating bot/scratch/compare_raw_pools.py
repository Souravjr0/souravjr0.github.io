import httpx
import base64
import struct

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    pools = {
        "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq": "Raydium CLMM (small)",
        "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv": "Raydium CLMM (massive)",
        "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv": "Raydium CLMM (Gecko 0.05%)"
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
                print(f"Pool: {pool_id} ({name}) not found!")
                continue
            raw = base64.b64decode(val["data"][0])
            
            mint0 = raw[73:73+32]
            mint1 = raw[105:105+32]
            
            liq_bytes = raw[252:252+16]
            liq = int.from_bytes(liq_bytes, byteorder="little", signed=False)
            
            sqrt_price_bytes = raw[324:324+16]
            sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
            
            from solders.pubkey import Pubkey
            print(f"Pool: {pool_id} ({name})")
            print(f"  Mint 0: {Pubkey(mint0)}")
            print(f"  Mint 1: {Pubkey(mint1)}")
            print(f"  Liquidity:  {liq}")
            print(f"  sqrt_price: {sqrt_price}")
            
            p_sol = (sqrt_price / (2**64)) ** 2 * 1000
            print(f"  SOL Price (assuming standard order): ${p_sol:.4f}")
            print("-" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
