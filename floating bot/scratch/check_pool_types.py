import httpx
import json

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    pools = [
        "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq",
        "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv"
    ]
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [pools, {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result", {})
        value = res.get("value", [])
        
        for idx, val in enumerate(value):
            if val:
                import base64
                data_b64 = val["data"][0]
                raw_bytes = base64.b64decode(data_b64)
                print(f"Pool: {pools[idx]}")
                print(f"  Owner: {val['owner']}")
                print(f"  Data Length: {len(raw_bytes)} bytes")
            else:
                print(f"Pool: {pools[idx]} not found!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
