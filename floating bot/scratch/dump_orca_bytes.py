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
        
        print("Hex dump of Orca Whirlpool from offset 60 to 140:")
        chunk = raw[60:140]
        for i in range(0, len(chunk), 16):
            line = chunk[i:i+16]
            hex_str = line.hex(" ")
            ascii_str = "".join([chr(b) if 32 <= b < 127 else "." for b in line])
            print(f"Offset {60 + i:3d}: {hex_str:<47}  | {ascii_str}")
            
        print("\nHex dump of Orca Whirlpool from offset 340 to 380:")
        chunk2 = raw[340:380]
        for i in range(0, len(chunk2), 16):
            line = chunk2[i:i+16]
            hex_str = line.hex(" ")
            ascii_str = "".join([chr(b) if 32 <= b < 127 else "." for b in line])
            print(f"Offset {340 + i:3d}: {hex_str:<47}  | {ascii_str}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
