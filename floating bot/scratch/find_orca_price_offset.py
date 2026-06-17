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
        raw = base64.b64decode(res["value"]["data"][0])
        
        # Target price is around $85.02 (approx 5.37e18)
        lower_bound = int(5.0e18)
        upper_bound = int(5.7e18)
        
        print(f"Scanning Orca bytes (len: {len(raw)})...")
        found = False
        for offset in range(0, len(raw) - 15):
            val_u128 = int.from_bytes(raw[offset:offset+16], byteorder="little", signed=False)
            if lower_bound <= val_u128 <= upper_bound:
                p = (val_u128 / (2**64)) ** 2 * 1000
                print(f"  [u128] Offset {offset}: {val_u128} -> Price: ${p:.4f}")
                found = True
                
        for offset in range(0, len(raw) - 7):
            val_u64 = int.from_bytes(raw[offset:offset+8], byteorder="little", signed=False)
            if lower_bound <= val_u64 <= upper_bound:
                p = (val_u64 / (2**64)) ** 2 * 1000
                print(f"  [u64] Offset {offset}: {val_u64} -> Price: ${p:.4f}")
                found = True
                
        if not found:
            print("[-] No price candidates found in Orca.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
