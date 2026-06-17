import httpx
import base64

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
        raw = base64.b64decode(res["value"]["data"][0])
        
        print("Hex dump from offset 240 to 380:")
        chunk = raw[240:380]
        # Print in 16-byte lines
        for i in range(0, len(chunk), 16):
            line = chunk[i:i+16]
            hex_str = line.hex(" ")
            ascii_str = "".join([chr(b) if 32 <= b < 127 else "." for b in line])
            print(f"Offset {240 + i:3d}: {hex_str:<47}  | {ascii_str}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
