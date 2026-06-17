import httpx
import base64
import struct

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    pool_id = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [pool_id, {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result")
        if not res or not res.get("value"):
            print("Failed to fetch pool info.")
            return
        raw = base64.b64decode(res["value"]["data"][0])
        print(f"Total raw bytes: {len(raw)}")
        
        # We search byte-by-byte for a u128 value that matches our price bounds!
        # Target price: SOL is around $85.02
        # price_ratio = price / 1000 = 0.08502
        # sqrt_price_ratio = sqrt(0.08502) = 0.29158
        # sqrt_price_x64 = 0.29158 * 2^64 = 5378701886196238336 (approx 5.37e18)
        
        # Let's search for a value between 5.0e18 and 5.7e18
        lower_bound = int(5.0e18)
        upper_bound = int(5.7e18)
        
        print("\nScanning for u128 price candidates (byte-by-byte)...")
        found = False
        for offset in range(0, len(raw) - 15):
            val_u128 = int.from_bytes(raw[offset:offset+16], byteorder="little", signed=False)
            if lower_bound <= val_u128 <= upper_bound:
                p = (val_u128 / (2**64)) ** 2 * 1000
                print(f"  [u128] Offset {offset}: {val_u128} -> SOL Price: ${p:.4f}")
                found = True
                
        # What if it's stored as u64? (Unlikely, but let's check)
        for offset in range(0, len(raw) - 7):
            val_u64 = int.from_bytes(raw[offset:offset+8], byteorder="little", signed=False)
            if lower_bound <= val_u64 <= upper_bound:
                p = (val_u64 / (2**64)) ** 2 * 1000
                print(f"  [u64] Offset {offset}: {val_u64} -> SOL Price: ${p:.4f}")
                found = True
                
        if not found:
            print("[-] No candidates found in raw bytes matching standard SOL price range.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
