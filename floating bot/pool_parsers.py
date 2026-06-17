import struct
from typing import Dict, Any, Optional

def parse_spl_token_account(data: bytes) -> int:
    """
    Parses a standard Solana SPL Token Account (165 bytes).
    The 'amount' field (uint64) is at offset 64.
    """
    if len(data) < 165:
        raise ValueError("Invalid SPL Token Account data length. Must be at least 165 bytes.")
    
    # Read uint64 at offset 64
    amount = struct.unpack_from("<Q", data, 64)[0]
    return amount

def parse_orca_whirlpool(data: bytes) -> Dict[str, Any]:
    """
    Parses an Orca Whirlpool state account using verified mainnet offsets.
    """
    if len(data) < 380:
        raise ValueError("Invalid Orca Whirlpool data length.")

    # Verified mainnet offsets:
    # token_mint_a (SOL): 101 (32 bytes)
    # token_vault_a (SOL): 133 (32 bytes)
    # token_mint_b (USDC): 181 (32 bytes)
    # token_vault_b (USDC): 213 (32 bytes)
    # sqrt_price (u128): 65 (16 bytes)
    # liquidity (u128): 48 (16 bytes)
    # tick_current_index (i32): 81 (4 bytes)
    
    tick_current_index = struct.unpack_from("<i", data, 81)[0]
    
    # Read u128 values (16 bytes each)
    sqrt_price_bytes = data[65:65+16]
    sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
    
    liquidity_bytes = data[48:48+16]
    liquidity = int.from_bytes(liquidity_bytes, byteorder="little", signed=False)
    
    token_mint_a = data[101:133]
    token_vault_a = data[133:165]
    token_mint_b = data[181:213]
    token_vault_b = data[213:245]

    return {
        "tick_current_index": tick_current_index,
        "sqrt_price": sqrt_price,
        "liquidity": liquidity,
        "token_mint_a": token_mint_a.hex(),
        "token_vault_a": token_vault_a.hex(),
        "token_mint_b": token_mint_b.hex(),
        "token_vault_b": token_vault_b.hex()
    }

def parse_raydium_amm_v4(data: bytes) -> Dict[str, Any]:
    """
    Parses a Raydium AMM v4 state account using verified mainnet offsets.
    """
    if len(data) < 752:
        raise ValueError("Invalid Raydium AMM v4 state data length.")
    
    # Verified mainnet offsets:
    # base_decimal: offset 32 (u64)
    # quote_decimal: offset 40 (u64)
    # base_vault: offset 336 (32 bytes)
    # quote_vault: offset 368 (32 bytes)
    # base_mint: offset 400 (32 bytes)
    # quote_mint: offset 432 (32 bytes)
    # lp_mint: offset 464 (32 bytes)
    # open_orders: offset 496 (32 bytes)
    # market_id: offset 528 (32 bytes)
    
    base_decimal = struct.unpack_from("<Q", data, 32)[0]
    quote_decimal = struct.unpack_from("<Q", data, 40)[0]
    
    base_vault = data[336:368]
    quote_vault = data[368:400]
    base_mint = data[400:432]
    quote_mint = data[432:464]
    lp_mint = data[464:496]
    open_orders = data[496:528]
    market_id = data[528:560]
    
    return {
        "base_decimal": base_decimal,
        "quote_decimal": quote_decimal,
        "base_vault": base_vault.hex(),
        "quote_vault": quote_vault.hex(),
        "base_mint": base_mint.hex(),
        "quote_mint": quote_mint.hex(),
        "lp_mint": lp_mint.hex(),
        "open_orders": open_orders.hex(),
        "market_id": market_id.hex()
    }

def parse_raydium_clmm(data: bytes) -> Dict[str, Any]:
    """
    Parses a Raydium CLMM state account (1544 bytes) using verified offsets.
    """
    if len(data) < 400:
        raise ValueError("Invalid Raydium CLMM data length.")
    
    # Verified mainnet offsets:
    # token_mint_0 (SOL): 73 (32 bytes)
    # token_mint_1 (USDC): 105 (32 bytes)
    # liquidity (u128): 237 (16 bytes)
    # sqrt_price (u128): 253 (16 bytes)
    
    token_mint_0 = data[73:105]
    token_mint_1 = data[105:137]
    
    liquidity_bytes = data[237:237+16]
    liquidity = int.from_bytes(liquidity_bytes, byteorder="little", signed=False)
    
    sqrt_price_bytes = data[253:253+16]
    sqrt_price = int.from_bytes(sqrt_price_bytes, byteorder="little", signed=False)
    
    return {
        "token_mint_a": token_mint_0.hex(),
        "token_mint_b": token_mint_1.hex(),
        "liquidity": liquidity,
        "sqrt_price": sqrt_price
    }

