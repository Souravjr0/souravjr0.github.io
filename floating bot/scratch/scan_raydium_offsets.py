import httpx
import base64
import struct

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    pools = {
        "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq": "Raydium CLMM (small)",
        "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv": "Raydium CLMM (massive)",
        "2QdhepnKRTLjjSqPL1PtKNwqrUkoLee5Gqs8bvZhRdMv": "Raydium CLMM (Gecko 0.05%)"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [list(pools.keys()), {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        value = response.json()["result"]["value"]
        
        for idx, val in enumerate(value):
            pool_id = list(pools.keys())[idx]
            name = pools[pool_id]
            if not val:
                print(f"Pool: {pool_id} ({name}) not found!")
                continue
            raw = base64.b64decode(val["data"][0])
            
            # Let's inspect the first 200 bytes or structure
            # token_mint_0 is at offset 73 (32 bytes)
            # token_mint_1 is at offset 105 (32 bytes)
            
            # What is at offset 324?
            # Let's extract the u128 fields at various offsets to see if there is another sqrt_price field,
            # or if the offsets are different.
            # Common Raydium CLMM PoolState offsets:
            # - bump: u8 (1)
            # - creator: Pubkey (32)
            # - token_mint_0: Pubkey (32) -> 1 + 32 = 33? Wait, Anchor discriminator is 8 bytes!
            # If Anchor discriminator is 8 bytes:
            # - bump: offset 8
            # - creator: offset 9 -> 9+32 = 41
            # - token_mint_0: offset 41? Wait! Let's check where the mint public keys are actually located.
            # In our previous print, we printed raw[73:73+32] and got WSOL, and raw[105:105+32] and got USDC.
            # 73 is 8 (discriminator) + 1 (bump) + 32 (ammConfig) + 32 (creator)? No:
            # 8 + 1 + 32 (ammConfig) + 32 (creator) = 73! Yes, this matches perfectly!
            # Let's trace all the fields from the Rust PoolState:
            # struct PoolState {
            #     bump: u8,                              // offset 8
            #     amm_config: Pubkey,                    // offset 9 (32 bytes) -> 41
            #     creator: Pubkey,                       // offset 41 (32 bytes) -> 73
            #     token_mint_0: Pubkey,                  // offset 73 (32 bytes) -> 105
            #     token_mint_1: Pubkey,                  // offset 105 (32 bytes) -> 137
            #     token_vault_0: Pubkey,                 // offset 137 (32 bytes) -> 169
            #     token_vault_1: Pubkey,                 // offset 169 (32 bytes) -> 201
            #     observation_key: Pubkey,               // offset 201 (32 bytes) -> 233
            #     tick_spacing: u16,                     // offset 233 (2 bytes) -> 235
            #     liquidity: u128,                       // offset 235? No, there is padding for alignment of u128!
            #     // u128 must be aligned to 8 or 16 bytes.
            #     // Let's print out all u128 candidates starting from offset 200 to 400!
            # }
            
            print(f"Pool: {pool_id} ({name})")
            for offset in range(230, 380, 2):
                val_u128 = int.from_bytes(raw[offset:offset+16], byteorder="little", signed=False)
                # If it's a realistic price or liquidity, let's print it:
                # Standard liquidity is around 1e21 (e.g. 1370...e18)
                # Standard sqrt_price is around 7e18 to 2e19
                if 1e18 < val_u128 < 1e24:
                    # Let's see what kind of SOL price this represents:
                    p_sol = (val_u128 / (2**64)) ** 2 * 1000
                    p_sol_inv = 1 / ((val_u128 / (2**64)) ** 2 / 1000) if val_u128 > 0 else 0
                    print(f"  Offset {offset}: {val_u128} -> SOL Price: ${p_sol:.4f} or ${p_sol_inv:.4f}")
            print("-" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
