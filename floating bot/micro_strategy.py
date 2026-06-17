#!/usr/bin/env python3
"""
Micro-Strategy Engine — Low-Balance Optimization Layer
cook45 & clack // Systems & MEV

Implements balance-aware trading strategies:
1. Spike Sniper — Waits for spread events (>0.3%) and fires Jito bundles
2. Adaptive Thresholds — Dynamic min-profit floors based on wallet balance
3. SOL-Native Arb — When USDC is too low, uses SOL balance for arb instead
4. Micro-Swap Mode — Ultra-small trades (~$0.10 minimum) for building balance
5. Hybrid Mode — Combines limit orders (no gas) + arbitrage for low balances
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from colorama import Fore, Style

logger = logging.getLogger("SolanaArbBot")


# Micro-swap constants
MIN_JUPITER_SWAP_USDC = 0.10  # Minimum viable Jupiter swap amount
MIN_JUPITER_SWAP_SOL = 0.0001  # Minimum viable SOL amount for swaps
MAX_MICRO_SWAP_USDC = 5.00  # Maximum micro-swap amount
MAX_MICRO_SWAP_SOL = 0.01  # Maximum micro-swap SOL amount
MICRO_TRADE_COOLDOWN = 5.0  # Seconds between micro-trades (avoid spam)


class BalanceTier:
    """Defines trading behavior tiers based on wallet balance"""
    DUST = "dust"        # < $0.50 — relaxed spike sniper (>0.3% spread, min $0.001 profit)
    MICRO = "micro"      # $0.50 - $2.00 — spike sniper (>0.2% spreads, min $0.001 profit)
    LOW = "low"          # $2.00 - $10.00 — moderate threshold (>0.1% net profit)
    MEDIUM = "medium"    # $10.00 - $100.00 — standard threshold (>0.05% net profit)
    HIGH = "high"        # $100+ — aggressive (any positive net profit)


# Fee constants (in USDC terms)
SOLANA_BASE_FEE_SOL = 0.000005        # Base signature fee
SOLANA_PRIORITY_FEE_SOL = 0.00005     # Priority fee (50k lamports)
JITO_TIP_SOL = 0.000001              # Minimum Jito tip (1000 lamports)
TOTAL_FIXED_COST_SOL = SOLANA_BASE_FEE_SOL + SOLANA_PRIORITY_FEE_SOL + JITO_TIP_SOL


def get_balance_tier(usdc_balance: float, sol_balance: float = 0.0, sol_price: float = 0.0) -> str:
    """Determines the trading tier based on available capital (USDC + SOL equivalent)"""
    total_capital = usdc_balance
    # Include SOL value if price is available — enables SOL-native trading tier
    if sol_price > 0 and sol_balance > 0:
        total_capital += sol_balance * sol_price
    if total_capital < 0.50:
        return BalanceTier.DUST
    elif total_capital < 2.00:
        return BalanceTier.MICRO
    elif total_capital < 10.00:
        return BalanceTier.LOW
    elif total_capital < 100.00:
        return BalanceTier.MEDIUM
    else:
        return BalanceTier.HIGH


def get_min_profit_threshold(tier: str, trade_amount_usdc: float, sol_price: float) -> Dict[str, float]:
    """
    Returns minimum profit requirements for a given tier.
    All values in USDC.
    """
    # Fixed cost in USDC (gas + priority + jito tip, converted from SOL)
    fixed_cost_usdc = TOTAL_FIXED_COST_SOL * sol_price

    # Per-tier minimum NET profit (after all fees including DEX swap fees)
    tier_minimums = {
        BalanceTier.DUST:  {"min_profit_usdc": max(0.001, fixed_cost_usdc * 2), "min_profit_pct": 0.30},   # Relaxed: 0.3% spread, $0.001 min
        BalanceTier.MICRO: {"min_profit_usdc": max(0.001, fixed_cost_usdc * 2), "min_profit_pct": 0.20},  # Relaxed: 0.2% spread, $0.001 min
        BalanceTier.LOW:   {"min_profit_usdc": max(0.002, fixed_cost_usdc * 2), "min_profit_pct": 0.10},  # Relaxed: 0.1% spread
        BalanceTier.MEDIUM:{"min_profit_usdc": max(0.002, fixed_cost_usdc * 2), "min_profit_pct": 0.05},
        BalanceTier.HIGH:  {"min_profit_usdc": max(0.001, fixed_cost_usdc * 1.5), "min_profit_pct": 0.01},
    }

    thresholds = tier_minimums.get(tier, tier_minimums[BalanceTier.MEDIUM])
    thresholds["fixed_cost_usdc"] = fixed_cost_usdc
    thresholds["tier"] = tier
    return thresholds


class SpikeDetector:
    """
    Monitors spread history and detects anomalous spikes.
    A spike is when the current spread exceeds the rolling average by a multiplier.
    For low-balance wallets, we only trade on spikes.
    
    OPTIMIZED: Relaxed thresholds for low-balance trading:
    - Smaller window (30 samples vs 120) for faster activation
    - Lower multiplier (1.5x vs 3.0x) for more signals
    - Shorter cooldown (10s vs 30s) for more frequent trades
    - Lower hard minimum (0.02% vs 0.05%) for micro opportunities
    """

    def __init__(self, window_size: int = 30, spike_multiplier: float = 1.5):
        self.window_size = window_size  # Number of spread samples to keep (relaxed from 120)
        self.spike_multiplier = spike_multiplier  # How many stdevs above mean = spike (relaxed from 3.0)
        self.spread_history: list = []
        self.last_spike_time: float = 0.0
        self.spike_cooldown: float = 10.0  # Min seconds between spike signals (relaxed from 30.0)
        self.spike_count: int = 0
        self.max_spread_seen: float = 0.0

    def record_spread(self, spread_pct: float):
        """Adds a spread observation to the rolling window"""
        self.spread_history.append(spread_pct)
        if len(self.spread_history) > self.window_size:
            self.spread_history.pop(0)
        if spread_pct > self.max_spread_seen:
            self.max_spread_seen = spread_pct

    def is_spike(self, current_spread_pct: float) -> Tuple[bool, Dict[str, float]]:
        """
        Determines if the current spread is a tradeable spike.
        Returns (is_spike, metadata).
        """
        self.record_spread(current_spread_pct)

        if len(self.spread_history) < 10:
            return False, {"reason": "insufficient_data", "samples": len(self.spread_history)}

        now = time.time()
        if (now - self.last_spike_time) < self.spike_cooldown:
            return False, {"reason": "cooldown_active"}

        # Calculate rolling statistics
        avg_spread = sum(self.spread_history) / len(self.spread_history)
        variance = sum((s - avg_spread) ** 2 for s in self.spread_history) / len(self.spread_history)
        stdev = variance ** 0.5

        threshold = avg_spread + (stdev * self.spike_multiplier)
        # Also enforce a hard minimum: spread must be at least 0.02% to be interesting (relaxed from 0.05%)
        threshold = max(threshold, 0.02)

        meta = {
            "avg_spread": avg_spread,
            "stdev": stdev,
            "threshold": threshold,
            "current": current_spread_pct,
            "max_seen": self.max_spread_seen,
            "samples": len(self.spread_history)
        }

        if current_spread_pct >= threshold:
            self.last_spike_time = now
            self.spike_count += 1
            meta["spike_number"] = self.spike_count
            logger.info(
                f"{Fore.LIGHTRED_EX}{Style.BRIGHT}[SPIKE #{self.spike_count}]{Style.RESET_ALL} "
                f"Spread {Fore.RED}{current_spread_pct:.4f}%{Style.RESET_ALL} exceeds threshold "
                f"{Fore.YELLOW}{threshold:.4f}%{Style.RESET_ALL} "
                f"(avg: {avg_spread:.4f}%, σ: {stdev:.4f}%)"
            )
            return True, meta

        return False, meta

    def get_stats(self) -> Dict[str, Any]:
        """Returns current spike detector statistics"""
        if not self.spread_history:
            return {"samples": 0}

        avg = sum(self.spread_history) / len(self.spread_history)
        return {
            "samples": len(self.spread_history),
            "avg_spread": avg,
            "max_spread": self.max_spread_seen,
            "spike_count": self.spike_count,
            "current_spread": self.spread_history[-1] if self.spread_history else 0
        }


def evaluate_opportunity(
    arb_result: Dict[str, Any],
    usdc_balance: float,
    sol_balance: float,
    sol_price: float,
    spike_detector: Optional[SpikeDetector] = None,
    quote_decimals: int = 6,
    quote_usd_price: float = 1.0
) -> Dict[str, Any]:
    """
    Master evaluation function. Takes a raw arbitrage result from check_arbitrage()
    and applies balance-tier filtering + spike detection to decide if we should trade.

    Returns dict with keys:
        - should_trade: bool
        - reason: str
        - tier: str
        - thresholds: dict
        - spike_data: dict (if spike detector provided)
    """
    if not arb_result.get("profitable"):
        return {"should_trade": False, "reason": "no_profitable_spread"}

    tier = get_balance_tier(usdc_balance, sol_balance, sol_price)
    thresholds = get_min_profit_threshold(tier, usdc_balance, sol_price)

    # Handle SOL-native results (input_type == "SOL") — convert lamports to USD
    is_sol_native = arb_result.get("input_type") == "SOL"
    if is_sol_native:
        raw_profit_usdc = (arb_result["raw_profit"] / 1e9) * sol_price
        profit_pct = arb_result["profit_pct"]
        amount_in_usdc = (arb_result["amount_in"] / 1e9) * sol_price
    else:
        raw_profit_usdc = (arb_result["raw_profit"] / (10 ** quote_decimals)) * quote_usd_price
        profit_pct = arb_result["profit_pct"]
        amount_in_usdc = (arb_result["amount_in"] / (10 ** quote_decimals)) * quote_usd_price

    # Calculate net profit after estimated gas costs
    net_profit = raw_profit_usdc - thresholds["fixed_cost_usdc"]
    net_profit_pct = (net_profit / amount_in_usdc) * 100 if amount_in_usdc > 0 else 0

    result = {
        "tier": tier,
        "input_type": arb_result.get("input_type", "USDC"),
        "raw_profit_usdc": raw_profit_usdc,
        "net_profit_usdc": net_profit,
        "net_profit_pct": net_profit_pct,
        "thresholds": thresholds,
        "direction": arb_result.get("direction", "unknown")
    }

    # Dust tier — relaxed spike requirements for low-balance trading
    if tier == BalanceTier.DUST:
        if spike_detector is not None:
            spread_pct = abs(profit_pct)
            is_spike, spike_meta = spike_detector.is_spike(spread_pct)
            result["spike_data"] = spike_meta
            # DUST tier: relaxed to 0.3% spread (was 1%), $0.001 profit (was $0.01)
            if is_spike and spread_pct >= 0.3 and net_profit >= 0.001:
                result["should_trade"] = True
                result["reason"] = (
                    f"✓ DUST tier spike approved. Net profit: ${net_profit:.4f} "
                    f"({net_profit_pct:.3f}%) — spread {spread_pct:.3f}%"
                )
                logger.info(
                    f"{Fore.LIGHTGREEN_EX}[MICRO-STRATEGY]{Style.RESET_ALL} "
                    f"Tier: {Fore.RED}{tier}{Style.RESET_ALL} | "
                    f"SPIKE {Fore.RED}{spread_pct:.3f}%{Style.RESET_ALL} | "
                    f"Net P&L: {Fore.GREEN}+${net_profit:.4f}{Style.RESET_ALL}"
                )
                return result
        # Fallback: trade on any decent spread even without spike detection
        spread_pct = abs(profit_pct)
        if spread_pct >= 0.5 and net_profit >= 0.001:
            result["should_trade"] = True
            result["reason"] = f"✓ DUST tier fallback: {spread_pct:.3f}% spread, ${net_profit:.4f} profit"
            return result
        result["should_trade"] = False
        result["reason"] = f"DUST tier (${usdc_balance:.2f}) — needs 0.3%+ spread, $0.001+ profit (spread: {spread_pct:.3f}%, profit: ${net_profit:.4f})"
        return result

    # Check minimum profit thresholds
    if net_profit < thresholds["min_profit_usdc"]:
        result["should_trade"] = False
        result["reason"] = (
            f"Net profit ${net_profit:.4f} below tier '{tier}' minimum "
            f"${thresholds['min_profit_usdc']:.4f}"
        )
        return result

    if net_profit_pct < thresholds["min_profit_pct"]:
        result["should_trade"] = False
        result["reason"] = (
            f"Net profit {net_profit_pct:.3f}% below tier '{tier}' minimum "
            f"{thresholds['min_profit_pct']:.2f}%"
        )
        return result

    # For MICRO tier, also require a spike (relaxed threshold)
    if tier == BalanceTier.MICRO and spike_detector is not None:
        spread_pct = abs(profit_pct)  # Use profit_pct as proxy for spread
        is_spike, spike_meta = spike_detector.is_spike(spread_pct)
        result["spike_data"] = spike_meta

        if not is_spike:
            # Fallback: trade on any 0.2%+ spread even without spike
            if spread_pct >= 0.2 and net_profit >= 0.001:
                result["should_trade"] = True
                result["reason"] = f"✓ MICRO tier fallback: {spread_pct:.3f}% spread, ${net_profit:.4f} profit"
                return result
            result["should_trade"] = False
            result["reason"] = f"MICRO tier requires spread spike or 0.2%+ spread. Current: {spread_pct:.4f}%"
            return result

    # All checks passed
    result["should_trade"] = True
    result["reason"] = (
        f"✓ Tier '{tier}' approved. Net profit: ${net_profit:.4f} "
        f"({net_profit_pct:.3f}%)"
    )

    logger.info(
        f"{Fore.LIGHTGREEN_EX}[MICRO-STRATEGY]{Style.RESET_ALL} "
        f"Tier: {Fore.CYAN}{tier}{Style.RESET_ALL} | "
        f"Net P&L: {Fore.GREEN}+${net_profit:.4f} ({net_profit_pct:.3f}%){Style.RESET_ALL} | "
        f"Threshold: ${thresholds['min_profit_usdc']:.4f} / {thresholds['min_profit_pct']:.2f}% | "
        f"Gas est: ${thresholds['fixed_cost_usdc']:.6f}"
    )

    return result


# ============================================================================
# MICRO-SWAP MODE: Ultra-small trades for building up balance
# ============================================================================

def get_micro_swap_amount(usdc_balance: float, sol_balance: float, sol_price: float) -> float:
    """
    Calculate the optimal micro-swap amount based on wallet balance.
    Uses a percentage of available balance to minimize risk while building up.
    
    Returns the recommended swap amount in USDC, or 0 if too small.
    """
    total_capital = usdc_balance + (sol_balance * sol_price)
    
    if total_capital < 0.10:
        # Ultra-micro: use 10% of balance, minimum $0.10
        recommended = max(0.10, total_capital * 0.10)
    elif total_capital < 1.00:
        # Micro: use 20% of balance, minimum $0.20
        recommended = max(0.20, total_capital * 0.20)
    elif total_capital < 5.00:
        # Small: use 30% of balance, minimum $0.50
        recommended = max(0.50, total_capital * 0.30)
    else:
        # Normal: use 50% of balance, minimum $1.00
        recommended = max(1.00, total_capital * 0.50)
    
    # Cap at minimum Jupiter swap size
    return min(recommended, MAX_MICRO_SWAP_USDC)


def is_micro_swap_viable(
    arb_result: Dict[str, Any],
    usdc_balance: float,
    sol_balance: float,
    sol_price: float,
    quote_decimals: int = 6,
    quote_usd_price: float = 1.0
) -> bool:
    """
    Check if a micro-swap is viable for the current balance.
    Micro-swaps are for DUST/MICRO tier wallets that can't do normal trades.
    """
    tier = get_balance_tier(usdc_balance, sol_balance, sol_price)
    
    # Only allow micro-swaps for DUST and MICRO tiers
    if tier not in [BalanceTier.DUST, BalanceTier.MICRO]:
        return False
    
    if not arb_result.get("profitable"):
        return False
    
    # Calculate profit
    is_sol_native = arb_result.get("input_type") == "SOL"
    if is_sol_native:
        raw_profit_usdc = (arb_result["raw_profit"] / 1e9) * sol_price
        amount_in_usdc = (arb_result["amount_in"] / 1e9) * sol_price
    else:
        raw_profit_usdc = (arb_result["raw_profit"] / (10 ** quote_decimals)) * quote_usd_price
        amount_in_usdc = (arb_result["amount_in"] / (10 ** quote_decimals)) * quote_usd_price
    
    # Micro-swap must have positive profit (we skip gas check for micro-swaps)
    # since we're using Jupiter which has lower fees
    if raw_profit_usdc <= 0:
        return False
    
    # Check if amount is viable
    if amount_in_usdc < MIN_JUPITER_SWAP_USDC:
        return False
    
    # Check if we have enough balance
    if is_sol_native:
        if sol_balance < (arb_result["amount_in"] / 1e9) * 1.1:  # 10% buffer
            return False
    else:
        if usdc_balance < amount_in_usdc * 1.1:  # 10% buffer
            return False
    
    return True


def get_micro_swap_recommendation(
    arb_result: Dict[str, Any],
    usdc_balance: float,
    sol_balance: float,
    sol_price: float,
    quote_decimals: int = 6,
    quote_usd_price: float = 1.0
) -> Dict[str, Any]:
    """
    Get a micro-swap recommendation for low-balance wallets.
    Returns details about the recommended micro-swap.
    """
    if not is_micro_swap_viable(arb_result, usdc_balance, sol_balance, sol_price, quote_decimals, quote_usd_price):
        return {"viable": False, "reason": "Not viable for micro-swap"}
    
    # Calculate amounts
    is_sol_native = arb_result.get("input_type") == "SOL"
    if is_sol_native:
        raw_profit_usdc = (arb_result["raw_profit"] / 1e9) * sol_price
        amount_in_usdc = (arb_result["amount_in"] / 1e9) * sol_price
    else:
        raw_profit_usdc = (arb_result["raw_profit"] / (10 ** quote_decimals)) * quote_usd_price
        amount_in_usdc = (arb_result["amount_in"] / (10 ** quote_decimals)) * quote_usd_price
    
    # Get recommended swap amount
    recommended_amount = get_micro_swap_amount(usdc_balance, sol_balance, sol_price)
    
    # Scale profit based on recommended amount
    if amount_in_usdc > 0:
        scaled_profit = raw_profit_usdc * (recommended_amount / amount_in_usdc)
    else:
        scaled_profit = 0
    
    return {
        "viable": True,
        "recommended_amount_usdc": recommended_amount,
        "estimated_profit_usdc": scaled_profit,
        "profit_per_dollar": scaled_profit / recommended_amount if recommended_amount > 0 else 0,
        "direction": arb_result.get("direction", "unknown"),
        "input_type": arb_result.get("input_type", "USDC"),
        "full_amount_profit_usdc": raw_profit_usdc,
        "full_amount_usdc": amount_in_usdc
    }


# ============================================================================
# HYBRID MODE: Limit orders + arbitrage for zero-gas trading
# ============================================================================

def calculate_limit_order_prices(
    current_price: float,
    spread_pct: float = 0.5,
    volatility_buffer_pct: float = 0.2
) -> Dict[str, float]:
    """
    Calculate limit order prices for hybrid mode.
    Places buy and sell orders around the current price with spread.
    
    Args:
        current_price: Current market price
        spread_pct: Distance from current price for orders (default 0.5%)
        volatility_buffer_pct: Extra buffer for price movement (default 0.2%)
    
    Returns dict with buy_price and sell_price
    """
    # Buy order: slightly below market
    buy_price = current_price * (1 - (spread_pct / 100) - (volatility_buffer_pct / 100))
    
    # Sell order: slightly above market
    sell_price = current_price * (1 + (spread_pct / 100) + (volatility_buffer_pct / 100))
    
    return {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "spread_pct": spread_pct,
        "current_price": current_price
    }


def is_hybrid_mode_suitable(
    usdc_balance: float,
    sol_balance: float,
    sol_price: float
) -> Tuple[bool, str]:
    """
    Check if hybrid mode (limit orders) is suitable for current balance.
    Hybrid mode is best for DUST tier wallets since it has no gas fees.
    """
    tier = get_balance_tier(usdc_balance, sol_balance, sol_price)
    total_capital = usdc_balance + (sol_balance * sol_price)
    
    if tier == BalanceTier.DUST:
        # Hybrid mode is perfect for DUST tier - no gas fees!
        return True, f"DUST tier (${total_capital:.2f}) — ideal for hybrid mode"
    elif tier == BalanceTier.MICRO and total_capital < 1.0:
        # MICRO tier with very low balance can also benefit
        return True, f"MICRO tier low balance (${total_capital:.2f}) — hybrid mode recommended"
    elif usdc_balance < 0.50 and sol_balance > 0.01:
        # Has SOL but no USDC - perfect for hybrid mode
        return True, "SOL-only wallet — hybrid mode ideal"
    
    return False, f"Balance ${total_capital:.2f} — standard mode recommended"


def get_hybrid_recommendation(
    current_price: float,
    usdc_balance: float,
    sol_balance: float,
    sol_price: float,
    spread_pct: float = 0.5
) -> Dict[str, Any]:
    """
    Get a hybrid mode recommendation for zero-gas trading.
    """
    suitable, reason = is_hybrid_mode_suitable(usdc_balance, sol_balance, sol_price)
    
    if not suitable:
        return {"suitable": False, "reason": reason}
    
    tier = get_balance_tier(usdc_balance, sol_balance, sol_price)
    prices = calculate_limit_order_prices(current_price, spread_pct)
    
    # Determine order sizes based on balance
    if usdc_balance > 0:
        buy_size = min(usdc_balance * 0.5, MAX_MICRO_SWAP_USDC)
        sell_size = min(sol_balance * 0.5 * sol_price, MAX_MICRO_SWAP_USDC)
    else:
        # SOL-only wallet
        buy_size = 0
        sell_size = min(sol_balance * 0.5, MAX_MICRO_SWAP_SOL)
    
    return {
        "suitable": True,
        "reason": reason,
        "tier": tier,
        "buy_order": {
            "price": prices["buy_price"],
            "size_usdc": buy_size,
            "side": "buy"
        },
        "sell_order": {
            "price": prices["sell_price"],
            "size_sol": sell_size / sol_price if sol_price > 0 else 0,
            "side": "sell"
        },
        "spread_pct": spread_pct,
        "estimated_profit_per_round_trip_pct": spread_pct * 2
    }
