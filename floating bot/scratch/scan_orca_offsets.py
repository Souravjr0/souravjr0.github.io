import httpx
import base64

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
            raw = base64.b64decode(res["value"]["data"][0])
            
            print(f"Orca Whirlpool: {orca_pool}")
            for offset in range(0, len(raw) - 15, 2):
                val_u128 = int.from_bytes(raw[offset:offset+16], byteorder="little", signed=False)
                
                # Check what kind of SOL price this represents
                p_sol = (val_u128 / (2**64)) ** 2 * 1000
                p_sol_inv = 1 / ((val_u128 / (2**64)) ** 2 / 1000) if val_u128 > 0 else 0
                
                # We are looking for a price around $85.02 (e.g. 80 to 90)
                if 80.0 < p_sol < 90.0 or 80.0 < p_sol_inv < 90.0:
                    print(f"  Offset {offset}: {val_u128} -> SOL Price: ${p_sol:.4f} or ${p_sol_inv:.4f}")
            print("-" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
