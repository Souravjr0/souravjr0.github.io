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
        
        print("Hex dump from offset 32 to 68:")
        chunk = raw[32:68]
        for i in range(0, len(chunk), 8):
            line = chunk[i:i+8]
            hex_str = line.hex(" ")
            print(f"Offset {32 + i:3d}: {hex_str}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
