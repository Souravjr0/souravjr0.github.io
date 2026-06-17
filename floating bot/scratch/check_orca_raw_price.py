import httpx
import base64
from solders.pubkey import Pubkey

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    orca_pool = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [orca_pool, {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result")
        if res and res.get("value"):
            data_b64 = res["value"]["data"][0]
            raw = base64.b64decode(data_b64)
            
            # Orca Whirlpool Layout:
            # sqrt_price: offset 357 (16 bytes)
            sqrt_price_bytes = raw[357:357+16]
            sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
            
            p_sol = (sqrt_price / (2**64)) ** 2 * 1000
            print(f"Orca Pool: {orca_pool}")
            print(f"  Raw length: {len(raw)} bytes")
            print(f"  sqrt_price: {sqrt_price}")
            print(f"  SOL Price: ${p_sol:.4f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
