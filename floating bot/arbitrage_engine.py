from typing import Dict, Any, Optional, List

def get_concentrated_swap_out_a_to_b(amount_in: int, sqrt_price_q64: int, liquidity: int, fee_bps: int = 5) -> int:
    """
    Concentrated Liquidity (V3) Swap math: Token A (SOL, base) to Token B (USDC, quote).
    Used by both Orca Whirlpool and Raydium CLMM.
    fee_bps: swap fee in basis points (5 bps = 0.05%, 30 bps = 0.30%).
    """
    if amount_in <= 0 or liquidity <= 0 or sqrt_price_q64 <= 0:
        return 0
    
    # Deduct fee
    fee_factor = 10000 - fee_bps
    amount_in_with_fee = (amount_in * fee_factor) // 10000
    q64 = 1 << 64
    
    try:
        inv_price_curr = (q64 * q64) // sqrt_price_q64
        delta_x_scaled = (amount_in_with_fee * q64) // liquidity
        inv_price_next = inv_price_curr + delta_x_scaled
        
        sqrt_price_next = (q64 * q64) // inv_price_next
        
        # delta_y = L * (sqrt_price_curr - sqrt_price_next)
        delta_y = (liquidity * (sqrt_price_q64 - sqrt_price_next)) // q64
        return delta_y
    except ZeroDivisionError:
        return 0

def get_concentrated_swap_out_b_to_a(amount_in: int, sqrt_price_q64: int, liquidity: int, fee_bps: int = 5) -> int:
    """
    Concentrated Liquidity (V3) Swap math: Token B (USDC, quote) to Token A (SOL, base).
    Used by both Orca Whirlpool and Raydium CLMM.
    """
    if amount_in <= 0 or liquidity <= 0 or sqrt_price_q64 <= 0:
        return 0
    
    # Deduct fee
    fee_factor = 10000 - fee_bps
    amount_in_with_fee = (amount_in * fee_factor) // 10000
    q64 = 1 << 64
    
    try:
        delta_y_scaled = (amount_in_with_fee * q64) // liquidity
        sqrt_price_next = sqrt_price_q64 + delta_y_scaled
        
        # delta_x = L * (1 / sqrt_price_curr - 1 / sqrt_price_next)
        inv_price_curr = (q64 * q64) // sqrt_price_q64
        inv_price_next = (q64 * q64) // sqrt_price_next
        
        delta_x = (liquidity * (inv_price_curr - inv_price_next)) // q64
        return delta_x
    except ZeroDivisionError:
        return 0

def get_amm_swap_out_a_to_b(amount_in: int, reserve_a: int, reserve_b: int, fee_bps: int = 25) -> int:
    """
    Constant product (x*y=k) swap math: Token A (SOL, base) to Token B (USDC, quote).
    Raydium AMM v4 uses standard constant product math.
    """
    if amount_in <= 0 or reserve_a <= 0 or reserve_b <= 0:
        return 0

    fee_factor = 10000 - fee_bps
    amount_in_with_fee = (amount_in * fee_factor) // 10000

    k = reserve_a * reserve_b
    new_reserve_a = reserve_a + amount_in_with_fee
    if new_reserve_a == 0:
        return 0
    new_reserve_b = k // new_reserve_a
    amount_out = reserve_b - new_reserve_b
    return max(amount_out, 0)

def get_amm_swap_out_b_to_a(amount_in: int, reserve_a: int, reserve_b: int, fee_bps: int = 25) -> int:
    """
    Constant product (x*y=k) swap math: Token B (USDC, quote) to Token A (SOL, base).
    """
    if amount_in <= 0 or reserve_a <= 0 or reserve_b <= 0:
        return 0

    fee_factor = 10000 - fee_bps
    amount_in_with_fee = (amount_in * fee_factor) // 10000

    k = reserve_a * reserve_b
    new_reserve_b = reserve_b + amount_in_with_fee
    if new_reserve_b == 0:
        return 0
    new_reserve_a = k // new_reserve_b
    amount_out = reserve_a - new_reserve_a
    return max(amount_out, 0)

def check_arbitrage(
    raydium_state: Dict[str, Any], 
    orca_state: Dict[str, Any], 
    amount_in_usdc: int
) -> Dict[str, Any]:
    """
    Compares prices between Raydium CLMM and Orca Whirlpool for a specific USDC input.
    Both pools use Concentrated Liquidity tick mathematics.
    
    amount_in_usdc is expected in raw lamports (6 decimals, e.g., 500 USDC = 500_000_000)
    """
    r_sqrt_price = raydium_state.get("sqrt_price", 0)
    r_liquidity = raydium_state.get("liquidity", 0)
    
    o_sqrt_price = orca_state.get("sqrt_price", 0)
    o_liquidity = orca_state.get("liquidity", 0)
    
    if r_sqrt_price <= 0 or r_liquidity <= 0 or o_sqrt_price <= 0 or o_liquidity <= 0:
        return {"profitable": False, "reason": "Insufficient reserves or inactive pool states"}

    # We assume both pools use the standard 0.05% (5 basis points) fee tier
    fee_bps = 5

    # =========================================================================
    # DIRECTION A: Raydium (Buy SOL with USDC) -> Orca (Sell SOL for USDC)
    # =========================================================================
    # Raydium swap: USDC -> SOL (B to A)
    sol_bought_dir_a = get_concentrated_swap_out_b_to_a(amount_in_usdc, r_sqrt_price, r_liquidity, fee_bps)
    # Orca swap: SOL -> USDC (A to B)
    usdc_returned_dir_a = get_concentrated_swap_out_a_to_b(sol_bought_dir_a, o_sqrt_price, o_liquidity, fee_bps)
    profit_dir_a = usdc_returned_dir_a - amount_in_usdc

    # =========================================================================
    # DIRECTION B: Orca (Buy SOL with USDC) -> Raydium (Sell SOL for USDC)
    # =========================================================================
    # Orca swap: USDC -> SOL (B to A)
    sol_bought_dir_b = get_concentrated_swap_out_b_to_a(amount_in_usdc, o_sqrt_price, o_liquidity, fee_bps)
    # Raydium swap: SOL -> USDC (A to B)
    usdc_returned_dir_b = get_concentrated_swap_out_a_to_b(sol_bought_dir_b, r_sqrt_price, r_liquidity, fee_bps)
    profit_dir_b = usdc_returned_dir_b - amount_in_usdc

    # Determine best opportunity
    if profit_dir_a > 0 and profit_dir_a > profit_dir_b:
        return {
            "profitable": True,
            "direction": "Raydium_CLMM_to_Orca_Whirlpool",
            "amount_in": amount_in_usdc,
            "intermediate_amount": sol_bought_dir_a,
            "amount_out": usdc_returned_dir_a,
            "raw_profit": profit_dir_a,
            "profit_pct": (profit_dir_a / amount_in_usdc) * 100
        }
    elif profit_dir_b > 0 and profit_dir_b > profit_dir_a:
        return {
            "profitable": True,
            "direction": "Orca_Whirlpool_to_Raydium_CLMM",
            "amount_in": amount_in_usdc,
            "intermediate_amount": sol_bought_dir_b,
            "amount_out": usdc_returned_dir_b,
            "raw_profit": profit_dir_b,
            "profit_pct": (profit_dir_b / amount_in_usdc) * 100
        }
    
    return {
        "profitable": False,
        "reason": f"No positive yield. Dir A: {profit_dir_a} units, Dir B: {profit_dir_b} units."
    }


def check_arbitrage_mixed(
    raydium_state: Dict[str, Any],
    raydium_kind: Optional[str],
    orca_state: Dict[str, Any],
    amount_in_usdc: int,
    raydium_fee_bps: int = 25
) -> Dict[str, Any]:
    """
    Arbitrage check that supports Raydium CLMM or Raydium AMM v4 vs Orca Whirlpool.
    """
    if raydium_kind in (None, "clmm", "concentrated"):
        return check_arbitrage(raydium_state, orca_state, amount_in_usdc)

    if raydium_kind != "amm_v4":
        return {"profitable": False, "reason": f"Unsupported Raydium pool type: {raydium_kind}"}

    reserve_base = raydium_state.get("reserve_base", 0)
    reserve_quote = raydium_state.get("reserve_quote", 0)
    if reserve_base <= 0 or reserve_quote <= 0:
        return {"profitable": False, "reason": "Insufficient Raydium AMM reserves"}

    o_sqrt_price = orca_state.get("sqrt_price", 0)
    o_liquidity = orca_state.get("liquidity", 0)
    if o_sqrt_price <= 0 or o_liquidity <= 0:
        return {"profitable": False, "reason": "Insufficient Orca pool state"}

    fee_bps = 5

    # Direction A: Raydium AMM (USDC -> SOL) -> Orca (SOL -> USDC)
    sol_bought_dir_a = get_amm_swap_out_b_to_a(amount_in_usdc, reserve_base, reserve_quote, raydium_fee_bps)
    usdc_returned_dir_a = get_concentrated_swap_out_a_to_b(sol_bought_dir_a, o_sqrt_price, o_liquidity, fee_bps)
    profit_dir_a = usdc_returned_dir_a - amount_in_usdc

    # Direction B: Orca (USDC -> SOL) -> Raydium AMM (SOL -> USDC)
    sol_bought_dir_b = get_concentrated_swap_out_b_to_a(amount_in_usdc, o_sqrt_price, o_liquidity, fee_bps)
    usdc_returned_dir_b = get_amm_swap_out_a_to_b(sol_bought_dir_b, reserve_base, reserve_quote, raydium_fee_bps)
    profit_dir_b = usdc_returned_dir_b - amount_in_usdc

    if profit_dir_a > 0 and profit_dir_a > profit_dir_b:
        return {
            "profitable": True,
            "direction": "Raydium_AMM_to_Orca_Whirlpool",
            "amount_in": amount_in_usdc,
            "intermediate_amount": sol_bought_dir_a,
            "amount_out": usdc_returned_dir_a,
            "raw_profit": profit_dir_a,
            "profit_pct": (profit_dir_a / amount_in_usdc) * 100,
            "raydium_pool_type": "amm_v4"
        }
    elif profit_dir_b > 0 and profit_dir_b > profit_dir_a:
        return {
            "profitable": True,
            "direction": "Orca_Whirlpool_to_Raydium_AMM",
            "amount_in": amount_in_usdc,
            "intermediate_amount": sol_bought_dir_b,
            "amount_out": usdc_returned_dir_b,
            "raw_profit": profit_dir_b,
            "profit_pct": (profit_dir_b / amount_in_usdc) * 100,
            "raydium_pool_type": "amm_v4"
        }

    return {
        "profitable": False,
        "reason": f"No positive yield. Dir A: {profit_dir_a} units, Dir B: {profit_dir_b} units."
    }


def check_arbitrage_sol_native(
    raydium_state: Dict[str, Any],
    orca_state: Dict[str, Any],
    amount_in_lamports: int
) -> Dict[str, Any]:
    """
    SOL-native arbitrage: Start with SOL instead of USDC.
    Path A: SOL -> USDC on Raydium -> SOL on Orca
    Path B: SOL -> USDC on Orca -> SOL on Raydium

    amount_in_lamports is in raw lamports (9 decimals, e.g., 0.01 SOL = 10_000_000)
    Returns profit in lamports.
    """
    r_sqrt_price = raydium_state.get("sqrt_price", 0)
    r_liquidity = raydium_state.get("liquidity", 0)
    o_sqrt_price = orca_state.get("sqrt_price", 0)
    o_liquidity = orca_state.get("liquidity", 0)

    if r_sqrt_price <= 0 or r_liquidity <= 0 or o_sqrt_price <= 0 or o_liquidity <= 0:
        return {"profitable": False, "reason": "Insufficient reserves or inactive pool states"}

    fee_bps = 5

    # =========================================================================
    # DIRECTION A: Raydium (Sell SOL for USDC) -> Orca (Buy SOL with USDC)
    # =========================================================================
    # Raydium swap: SOL -> USDC (A to B)
    usdc_received_dir_a = get_concentrated_swap_out_a_to_b(amount_in_lamports, r_sqrt_price, r_liquidity, fee_bps)
    # Orca swap: USDC -> SOL (B to A)
    sol_returned_dir_a = get_concentrated_swap_out_b_to_a(usdc_received_dir_a, o_sqrt_price, o_liquidity, fee_bps)
    profit_dir_a = sol_returned_dir_a - amount_in_lamports

    # =========================================================================
    # DIRECTION B: Orca (Sell SOL for USDC) -> Raydium (Buy SOL with USDC)
    # =========================================================================
    # Orca swap: SOL -> USDC (A to B)
    usdc_received_dir_b = get_concentrated_swap_out_a_to_b(amount_in_lamports, o_sqrt_price, o_liquidity, fee_bps)
    # Raydium swap: USDC -> SOL (B to A)
    sol_returned_dir_b = get_concentrated_swap_out_b_to_a(usdc_received_dir_b, r_sqrt_price, r_liquidity, fee_bps)
    profit_dir_b = sol_returned_dir_b - amount_in_lamports

    if profit_dir_a > 0 and profit_dir_a > profit_dir_b:
        return {
            "profitable": True,
            "direction": "Raydium_CLMM_to_Orca_Whirlpool_SOL",
            "input_type": "SOL",
            "amount_in": amount_in_lamports,
            "intermediate_amount": usdc_received_dir_a,
            "amount_out": sol_returned_dir_a,
            "raw_profit": profit_dir_a,
            "profit_pct": (profit_dir_a / amount_in_lamports) * 100
        }
    elif profit_dir_b > 0 and profit_dir_b > profit_dir_a:
        return {
            "profitable": True,
            "direction": "Orca_Whirlpool_to_Raydium_CLMM_SOL",
            "input_type": "SOL",
            "amount_in": amount_in_lamports,
            "intermediate_amount": usdc_received_dir_b,
            "amount_out": sol_returned_dir_b,
            "raw_profit": profit_dir_b,
            "profit_pct": (profit_dir_b / amount_in_lamports) * 100
        }

    return {
        "profitable": False,
        "reason": f"No positive SOL-native yield. Dir A: {profit_dir_a} lamports, Dir B: {profit_dir_b} lamports."
    }


def check_arbitrage_sol_native_mixed(
    raydium_state: Dict[str, Any],
    raydium_kind: Optional[str],
    orca_state: Dict[str, Any],
    amount_in_lamports: int,
    raydium_fee_bps: int = 25
) -> Dict[str, Any]:
    """
    SOL-native arbitrage supporting Raydium CLMM or Raydium AMM v4 vs Orca Whirlpool.
    """
    if raydium_kind in (None, "clmm", "concentrated"):
        return check_arbitrage_sol_native(raydium_state, orca_state, amount_in_lamports)

    if raydium_kind != "amm_v4":
        return {"profitable": False, "reason": f"Unsupported Raydium pool type: {raydium_kind}"}

    reserve_base = raydium_state.get("reserve_base", 0)
    reserve_quote = raydium_state.get("reserve_quote", 0)
    if reserve_base <= 0 or reserve_quote <= 0:
        return {"profitable": False, "reason": "Insufficient Raydium AMM reserves"}

    o_sqrt_price = orca_state.get("sqrt_price", 0)
    o_liquidity = orca_state.get("liquidity", 0)
    if o_sqrt_price <= 0 or o_liquidity <= 0:
        return {"profitable": False, "reason": "Insufficient Orca pool state"}

    fee_bps = 5

    # Direction A: Raydium AMM (SOL -> USDC) -> Orca (USDC -> SOL)
    usdc_received_dir_a = get_amm_swap_out_a_to_b(amount_in_lamports, reserve_base, reserve_quote, raydium_fee_bps)
    sol_returned_dir_a = get_concentrated_swap_out_b_to_a(usdc_received_dir_a, o_sqrt_price, o_liquidity, fee_bps)
    profit_dir_a = sol_returned_dir_a - amount_in_lamports

    # Direction B: Orca (SOL -> USDC) -> Raydium AMM (USDC -> SOL)
    usdc_received_dir_b = get_concentrated_swap_out_a_to_b(amount_in_lamports, o_sqrt_price, o_liquidity, fee_bps)
    sol_returned_dir_b = get_amm_swap_out_b_to_a(usdc_received_dir_b, reserve_base, reserve_quote, raydium_fee_bps)
    profit_dir_b = sol_returned_dir_b - amount_in_lamports

    if profit_dir_a > 0 and profit_dir_a > profit_dir_b:
        return {
            "profitable": True,
            "direction": "Raydium_AMM_to_Orca_Whirlpool_SOL",
            "input_type": "SOL",
            "amount_in": amount_in_lamports,
            "intermediate_amount": usdc_received_dir_a,
            "amount_out": sol_returned_dir_a,
            "raw_profit": profit_dir_a,
            "profit_pct": (profit_dir_a / amount_in_lamports) * 100,
            "raydium_pool_type": "amm_v4"
        }
    elif profit_dir_b > 0 and profit_dir_b > profit_dir_a:
        return {
            "profitable": True,
            "direction": "Orca_Whirlpool_to_Raydium_AMM_SOL",
            "input_type": "SOL",
            "amount_in": amount_in_lamports,
            "intermediate_amount": usdc_received_dir_b,
            "amount_out": sol_returned_dir_b,
            "raw_profit": profit_dir_b,
            "profit_pct": (profit_dir_b / amount_in_lamports) * 100,
            "raydium_pool_type": "amm_v4"
        }

    return {
        "profitable": False,
        "reason": f"No positive SOL-native yield. Dir A: {profit_dir_a} lamports, Dir B: {profit_dir_b} lamports."
    }
