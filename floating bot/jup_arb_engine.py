#!/usr/bin/env python3
"""
Jupiter Quote-Based Arbitrage Engine — Multi-Path Profit Detection
cook45 & clack // Systems & MEV

Instead of local pool math on 2 DEXes, this queries Jupiter's aggregator
for round-trip profit detection across ALL 20+ Solana DEXes.

Jupiter handles:
- Multi-hop routing (splits across pools)
- Tick crossing (accurate for concentrated liquidity)
- All DEXes: Raydium, Orca, Meteora, Lifinity, Phoenix, Openbook, etc.

We just check: does round_trip_out > round_trip_in + gas_cost?
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from colorama import Fore, Style

logger = logging.getLogger("SolanaArbBot")

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

# Mid-cap tokens for triangular arb scanning (top 5 by liquidity)
TRIANGLE_TOKENS = {
    "JUP":  {"mint": "JUPyiwrYdGVGgzJABd847LsHWtwYY611L4xg5E184cM", "decimals": 6},
    "BONK": {"mint": "DezXAZ8z7PnrnRJjz3wX4mPtkoc27DPm759wyB75zPLr", "decimals": 5},
    "JTO":  {"mint": "jtoSnE795qyv2wJTxtjZa5hkcz3gJaHAwtLedHsQNrr",  "decimals": 9},
    "RAY":  {"mint": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", "decimals": 6},
    "W":    {"mint": "85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ", "decimals": 6},
}

# Jupiter API rate limit: free tier enforces ~1 req/sec sustained
# Aggressive spacing to avoid 429 storms
JUPITER_QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
MAX_REQUESTS_PER_SEC = 1
MIN_REQUEST_INTERVAL = 1.0 / MAX_REQUESTS_PER_SEC


class JupiterRateLimiter:
    """Token bucket rate limiter for Jupiter API — enforces strict spacing"""
    def __init__(self, min_interval: float = 1.5):
        self.min_interval = min_interval  # 1.5s between requests
        self.last_request_time = 0.0
        self.request_count = 0
        self.error_count = 0
        self.backoff_until = 0.0

    async def wait(self):
        """Wait if needed to respect rate limits"""
        now = time.time()

        # If we hit a 429, back off for longer
        if now < self.backoff_until:
            wait_time = self.backoff_until - now
            await asyncio.sleep(wait_time)

        # Always enforce minimum spacing from last request
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)

        # Set time right before we return (just before the HTTP call fires)
        self.last_request_time = time.time()
        self.request_count += 1

    def report_429(self):
        """Called when we get a 429 rate limit response"""
        self.error_count += 1
        backoff_secs = min(3 * self.error_count, 30)  # 3, 6, 9, ... up to 30
        self.backoff_until = time.time() + backoff_secs
        logger.warning(
            f"[JUP-RATE-LIMIT] 429 received. Backing off for {backoff_secs}s "
            f"(error #{self.error_count})"
        )

    def report_success(self):
        """Slowly reset error count on success"""
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)


class JupiterArbEngine:
    """
    Queries Jupiter aggregator for round-trip arbitrage opportunities.
    Works at ANY balance level because Jupiter handles micro-swaps.
    """

    def __init__(self, http_client, sol_price: float = 0.0):
        self.http = http_client
        self.rate_limiter = JupiterRateLimiter()
        self.sol_price = sol_price
        self.scan_count = 0
        self.opportunities_found = 0
        self.best_profit_seen = 0.0
        self.last_scan_time = 0.0

        # Estimated gas cost in lamports for a single Jupiter swap tx
        # Base fee (5000) + priority fee (dynamic, ~10000-50000)
        self.est_gas_lamports = 25_000  # ~$0.004 at $160 SOL

    def update_sol_price(self, price: float):
        self.sol_price = price

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Queries Jupiter for a swap quote.
        Returns dict with outAmount, route info, or None on failure.
        """
        await self.rate_limiter.wait()

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
        }

        try:
            resp = await self.http.get(JUPITER_QUOTE_URL, params=params, timeout=8.0)

            if resp.status_code == 429:
                self.rate_limiter.report_429()
                return None

            if resp.status_code != 200:
                return None

            self.rate_limiter.report_success()
            data = resp.json()

            if "error" in data:
                return None

            return {
                "outAmount": int(data.get("outAmount", 0)),
                "inAmount": int(data.get("inAmount", 0)),
                "priceImpactPct": float(data.get("priceImpactPct", 0)),
                "routePlan": data.get("routePlan", []),
                "otherAmountThreshold": int(data.get("otherAmountThreshold", 0)),
            }
        except Exception as e:
            logger.debug(f"Jupiter quote error: {e}")
            return None

    async def check_round_trip_usdc(self, amount_usdc_raw: int) -> Dict[str, Any]:
        """
        Round-trip: USDC → SOL → USDC
        Checks if Jupiter's aggregated routing produces profit.
        """
        self.scan_count += 1

        # Leg 1: USDC → SOL
        quote1 = await self.get_quote(USDC_MINT, SOL_MINT, amount_usdc_raw)
        if not quote1 or quote1["outAmount"] <= 0:
            return {"profitable": False, "reason": "Quote leg 1 failed"}

        sol_intermediate = quote1["outAmount"]

        # Leg 2: SOL → USDC (using the SOL we'd get from leg 1)
        quote2 = await self.get_quote(SOL_MINT, USDC_MINT, sol_intermediate)
        if not quote2 or quote2["outAmount"] <= 0:
            return {"profitable": False, "reason": "Quote leg 2 failed"}

        usdc_returned = quote2["outAmount"]
        gross_profit = usdc_returned - amount_usdc_raw
        gross_profit_pct = (gross_profit / amount_usdc_raw) * 100 if amount_usdc_raw > 0 else 0

        # Deduct estimated gas for 2 transactions
        gas_cost_usdc = 0
        if self.sol_price > 0:
            gas_cost_usdc = int((self.est_gas_lamports * 2 / 1e9) * self.sol_price * 1e6)

        net_profit = gross_profit - gas_cost_usdc
        net_profit_usd = net_profit / 1e6

        result = {
            "profitable": net_profit > 0,
            "direction": "USDC_SOL_USDC",
            "input_type": "USDC",
            "amount_in": amount_usdc_raw,
            "intermediate_amount": sol_intermediate,
            "amount_out": usdc_returned,
            "raw_profit": gross_profit,
            "net_profit": net_profit,
            "net_profit_usd": net_profit_usd,
            "profit_pct": gross_profit_pct,
            "gas_cost_usdc": gas_cost_usdc,
            "leg1_impact": quote1["priceImpactPct"],
            "leg2_impact": quote2["priceImpactPct"],
            "leg1_routes": len(quote1.get("routePlan", [])),
            "leg2_routes": len(quote2.get("routePlan", [])),
        }

        if net_profit > 0:
            self.opportunities_found += 1
            if net_profit_usd > self.best_profit_seen:
                self.best_profit_seen = net_profit_usd
            logger.info(
                f"{Fore.LIGHTGREEN_EX}[JUP-ARB]{Style.RESET_ALL} "
                f"USDC→SOL→USDC round-trip profit: "
                f"{Fore.GREEN}+${net_profit_usd:.6f}{Style.RESET_ALL} "
                f"({gross_profit_pct:.4f}%) | "
                f"In: ${amount_usdc_raw/1e6:.4f} | Out: ${usdc_returned/1e6:.4f}"
            )

        return result

    async def check_round_trip_sol(self, amount_sol_lamports: int) -> Dict[str, Any]:
        """
        Round-trip: SOL → USDC → SOL
        """
        self.scan_count += 1

        # Leg 1: SOL → USDC
        quote1 = await self.get_quote(SOL_MINT, USDC_MINT, amount_sol_lamports)
        if not quote1 or quote1["outAmount"] <= 0:
            return {"profitable": False, "reason": "Quote leg 1 failed"}

        usdc_intermediate = quote1["outAmount"]

        # Leg 2: USDC → SOL
        quote2 = await self.get_quote(USDC_MINT, SOL_MINT, usdc_intermediate)
        if not quote2 or quote2["outAmount"] <= 0:
            return {"profitable": False, "reason": "Quote leg 2 failed"}

        sol_returned = quote2["outAmount"]
        gross_profit = sol_returned - amount_sol_lamports
        gross_profit_pct = (gross_profit / amount_sol_lamports) * 100 if amount_sol_lamports > 0 else 0

        # Gas cost in lamports
        gas_cost = self.est_gas_lamports * 2
        net_profit = gross_profit - gas_cost
        net_profit_usd = (net_profit / 1e9) * self.sol_price if self.sol_price > 0 else 0

        result = {
            "profitable": net_profit > 0,
            "direction": "SOL_USDC_SOL",
            "input_type": "SOL",
            "amount_in": amount_sol_lamports,
            "intermediate_amount": usdc_intermediate,
            "amount_out": sol_returned,
            "raw_profit": gross_profit,
            "net_profit": net_profit,
            "net_profit_usd": net_profit_usd,
            "profit_pct": gross_profit_pct,
            "gas_cost_lamports": gas_cost,
            "leg1_impact": quote1["priceImpactPct"],
            "leg2_impact": quote2["priceImpactPct"],
        }

        if net_profit > 0:
            self.opportunities_found += 1
            if net_profit_usd > self.best_profit_seen:
                self.best_profit_seen = net_profit_usd
            logger.info(
                f"{Fore.LIGHTGREEN_EX}[JUP-ARB]{Style.RESET_ALL} "
                f"SOL→USDC→SOL round-trip profit: "
                f"{Fore.GREEN}+${net_profit_usd:.6f}{Style.RESET_ALL} "
                f"({gross_profit_pct:.4f}%) | "
                f"In: {amount_sol_lamports/1e9:.5f} SOL | Out: {sol_returned/1e9:.5f} SOL"
            )

        return result

    async def check_triangle_arb(
        self,
        amount_usdc_raw: int,
        mid_token_mint: str,
        mid_token_symbol: str,
    ) -> Dict[str, Any]:
        """
        Triangular arb: USDC → SOL → TOKEN → USDC
        Exploits price inefficiencies across three legs.
        """
        self.scan_count += 1

        # Leg 1: USDC → SOL
        q1 = await self.get_quote(USDC_MINT, SOL_MINT, amount_usdc_raw)
        if not q1 or q1["outAmount"] <= 0:
            return {"profitable": False, "reason": "Leg 1 (USDC→SOL) failed"}

        # Leg 2: SOL → TOKEN
        q2 = await self.get_quote(SOL_MINT, mid_token_mint, q1["outAmount"])
        if not q2 or q2["outAmount"] <= 0:
            return {"profitable": False, "reason": f"Leg 2 (SOL→{mid_token_symbol}) failed"}

        # Leg 3: TOKEN → USDC
        q3 = await self.get_quote(mid_token_mint, USDC_MINT, q2["outAmount"])
        if not q3 or q3["outAmount"] <= 0:
            return {"profitable": False, "reason": f"Leg 3 ({mid_token_symbol}→USDC) failed"}

        usdc_returned = q3["outAmount"]
        gross_profit = usdc_returned - amount_usdc_raw
        gross_profit_pct = (gross_profit / amount_usdc_raw) * 100 if amount_usdc_raw > 0 else 0

        # 3 transactions worth of gas
        gas_cost_usdc = 0
        if self.sol_price > 0:
            gas_cost_usdc = int((self.est_gas_lamports * 3 / 1e9) * self.sol_price * 1e6)

        net_profit = gross_profit - gas_cost_usdc
        net_profit_usd = net_profit / 1e6

        direction = f"USDC_SOL_{mid_token_symbol}_USDC"

        result = {
            "profitable": net_profit > 0,
            "direction": direction,
            "input_type": "USDC",
            "amount_in": amount_usdc_raw,
            "amount_out": usdc_returned,
            "raw_profit": gross_profit,
            "net_profit": net_profit,
            "net_profit_usd": net_profit_usd,
            "profit_pct": gross_profit_pct,
            "gas_cost_usdc": gas_cost_usdc,
            "mid_token": mid_token_symbol,
            "mid_token_mint": mid_token_mint,
            "legs": [
                {"path": "USDC→SOL", "out": q1["outAmount"], "impact": q1["priceImpactPct"]},
                {"path": f"SOL→{mid_token_symbol}", "out": q2["outAmount"], "impact": q2["priceImpactPct"]},
                {"path": f"{mid_token_symbol}→USDC", "out": q3["outAmount"], "impact": q3["priceImpactPct"]},
            ],
        }

        if net_profit > 0:
            self.opportunities_found += 1
            if net_profit_usd > self.best_profit_seen:
                self.best_profit_seen = net_profit_usd
            logger.info(
                f"{Fore.LIGHTMAGENTA_EX}[TRIANGLE]{Style.RESET_ALL} "
                f"USDC→SOL→{mid_token_symbol}→USDC profit: "
                f"{Fore.GREEN}+${net_profit_usd:.6f}{Style.RESET_ALL} "
                f"({gross_profit_pct:.4f}%)"
            )

        return result

    async def check_triangle_arb_reverse(
        self,
        amount_usdc_raw: int,
        mid_token_mint: str,
        mid_token_symbol: str,
    ) -> Dict[str, Any]:
        """
        Reverse triangular arb: USDC → TOKEN → SOL → USDC
        """
        self.scan_count += 1

        # Leg 1: USDC → TOKEN
        q1 = await self.get_quote(USDC_MINT, mid_token_mint, amount_usdc_raw)
        if not q1 or q1["outAmount"] <= 0:
            return {"profitable": False, "reason": f"Leg 1 (USDC→{mid_token_symbol}) failed"}

        # Leg 2: TOKEN → SOL
        q2 = await self.get_quote(mid_token_mint, SOL_MINT, q1["outAmount"])
        if not q2 or q2["outAmount"] <= 0:
            return {"profitable": False, "reason": f"Leg 2 ({mid_token_symbol}→SOL) failed"}

        # Leg 3: SOL → USDC
        q3 = await self.get_quote(SOL_MINT, USDC_MINT, q2["outAmount"])
        if not q3 or q3["outAmount"] <= 0:
            return {"profitable": False, "reason": "Leg 3 (SOL→USDC) failed"}

        usdc_returned = q3["outAmount"]
        gross_profit = usdc_returned - amount_usdc_raw
        gross_profit_pct = (gross_profit / amount_usdc_raw) * 100 if amount_usdc_raw > 0 else 0

        gas_cost_usdc = 0
        if self.sol_price > 0:
            gas_cost_usdc = int((self.est_gas_lamports * 3 / 1e9) * self.sol_price * 1e6)

        net_profit = gross_profit - gas_cost_usdc
        net_profit_usd = net_profit / 1e6

        direction = f"USDC_{mid_token_symbol}_SOL_USDC"

        result = {
            "profitable": net_profit > 0,
            "direction": direction,
            "input_type": "USDC",
            "amount_in": amount_usdc_raw,
            "amount_out": usdc_returned,
            "raw_profit": gross_profit,
            "net_profit": net_profit,
            "net_profit_usd": net_profit_usd,
            "profit_pct": gross_profit_pct,
            "gas_cost_usdc": gas_cost_usdc,
            "mid_token": mid_token_symbol,
            "mid_token_mint": mid_token_mint,
        }

        if net_profit > 0:
            self.opportunities_found += 1
            if net_profit_usd > self.best_profit_seen:
                self.best_profit_seen = net_profit_usd
            logger.info(
                f"{Fore.LIGHTMAGENTA_EX}[TRIANGLE-REV]{Style.RESET_ALL} "
                f"USDC→{mid_token_symbol}→SOL→USDC profit: "
                f"{Fore.GREEN}+${net_profit_usd:.6f}{Style.RESET_ALL} "
                f"({gross_profit_pct:.4f}%)"
            )

        return result

    async def scan_all_opportunities(
        self,
        usdc_balance_raw: int,
        sol_balance_lamports: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Master scanner: checks round-trip arb and all triangular paths.
        Returns the best profitable opportunity, or None.
        """
        best_result = None
        best_profit_usd = 0.0

        # 1. Direct round-trip: USDC → SOL → USDC
        if usdc_balance_raw >= 100_000:  # $0.10 minimum
            rt_usdc = await self.check_round_trip_usdc(usdc_balance_raw)
            if rt_usdc.get("profitable") and rt_usdc.get("net_profit_usd", 0) > best_profit_usd:
                best_profit_usd = rt_usdc["net_profit_usd"]
                best_result = rt_usdc

        # 2. Direct round-trip: SOL → USDC → SOL
        if sol_balance_lamports >= 100_000:  # 0.0001 SOL minimum
            # Reserve gas: use 90% of SOL balance
            sol_to_arb = int(sol_balance_lamports * 0.9)
            rt_sol = await self.check_round_trip_sol(sol_to_arb)
            if rt_sol.get("profitable") and rt_sol.get("net_profit_usd", 0) > best_profit_usd:
                best_profit_usd = rt_sol["net_profit_usd"]
                best_result = rt_sol

        # 3. Triangular arb: USDC → SOL → TOKEN → USDC (both directions)
        if usdc_balance_raw >= 100_000:
            for symbol, info in TRIANGLE_TOKENS.items():
                # Forward: USDC → SOL → TOKEN → USDC
                tri = await self.check_triangle_arb(
                    usdc_balance_raw, info["mint"], symbol
                )
                if tri.get("profitable") and tri.get("net_profit_usd", 0) > best_profit_usd:
                    best_profit_usd = tri["net_profit_usd"]
                    best_result = tri

                # Reverse: USDC → TOKEN → SOL → USDC
                tri_rev = await self.check_triangle_arb_reverse(
                    usdc_balance_raw, info["mint"], symbol
                )
                if tri_rev.get("profitable") and tri_rev.get("net_profit_usd", 0) > best_profit_usd:
                    best_profit_usd = tri_rev["net_profit_usd"]
                    best_result = tri_rev

        self.last_scan_time = time.time()
        return best_result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_scans": self.scan_count,
            "opportunities_found": self.opportunities_found,
            "best_profit_usd": self.best_profit_seen,
            "last_scan": self.last_scan_time,
        }
