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
        data = response.json()["result"]["value"]["data"][0]
        raw = base64.b64decode(data)
        
        # Raydium CLMM Layout:
        # token_mint_0: offset 73 (32 bytes)
        # token_mint_1: offset 105 (32 bytes)
        # sqrt_price: offset 324 (16 bytes)
        
        mint0 = raw[73:73+32]
        mint1 = raw[105:105+32]
        sqrt_price_bytes = raw[324:324+16]
        sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
        
        from solders.pubkey import Pubkey
        print(f"Mint 0: {Pubkey(mint0)}")
        print(f"Mint 1: {Pubkey(mint1)}")
        print(f"sqrt_price: {sqrt_price}")
        
        # Let's calculate the price if Mint 0 is USDC and Mint 1 is SOL vs Mint 0 is SOL and Mint 1 is USDC
        # USDC (6 decimals), SOL (9 decimals)
        p1 = (sqrt_price / (2**64)) ** 2 * (10**9 / 10**6)  # if Mint 0 is SOL, Mint 1 is USDC? Wait:
        # standard formula: price of token_0 in terms of token_1:
        # price = (sqrt_price / 2^64)^2 * (10^decimals_0 / 10^decimals_1)
        # if token_0 = SOL (9), token_1 = USDC (6):
        # price = (sqrt_price / 2^64)^2 * 1000
        # if token_0 = USDC (6), token_1 = SOL (9):
        # price = (sqrt_price / 2^64)^2 / 1000
        print(f"Price if token_0 = SOL, token_1 = USDC: {(sqrt_price / 2**64)**2 * 1000}")
        print(f"Price if token_0 = USDC, token_1 = SOL (inverse is SOL price): {1 / ((sqrt_price / 2**64)**2 / 1000)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
