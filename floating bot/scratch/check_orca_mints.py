import httpx
import base64
import struct

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    pool_id = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [pool_id, {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        data = response.json()["result"]["value"]["data"][0]
        raw = base64.b64decode(data)
        
        # Orca Layout:
        # token_mint_a: offset 101 (32 bytes)
        # token_mint_b: offset 181 (32 bytes)
        # sqrt_price: offset 357 (16 bytes)
        
        mint0 = raw[101:101+32]
        mint1 = raw[181:181+32]
        sqrt_price_bytes = raw[357:357+16]
        sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
        
        from solders.pubkey import Pubkey
        print(f"Orca Mint 0: {Pubkey(mint0)}")
        print(f"Orca Mint 1: {Pubkey(mint1)}")
        print(f"Orca sqrt_price: {sqrt_price}")
        
        # Calculate SOL Price
        print(f"Price if token_0 = SOL, token_1 = USDC: {(sqrt_price / 2**64)**2 * 1000}")
        print(f"Price if token_0 = USDC, token_1 = SOL (inverse is SOL price): {1 / ((sqrt_price / 2**64)**2 / 1000)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
