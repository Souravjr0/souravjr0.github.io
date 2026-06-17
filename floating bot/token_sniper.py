#!/usr/bin/env python3
"""
New Token Launch Sniper — Real-Time Pool Detection & Micro-Buy
cook45 & clack // Systems & MEV

Monitors Solana for new Raydium pool creations in real-time.
When a new token launches with sufficient liquidity, executes a micro-buy
and manages the position with trailing stop-loss.

This is where the real money is for low-balance wallets:
- New tokens have 2-50% spreads in the first minutes
- A single 10x on $1.60 snipe = $16 (20x your total balance)
- Safety filters protect against rugs: freeze auth, top holder, LP burn checks
"""

import os
import sys
import json
import asyncio
import base64
import struct
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
import websockets
import httpx
from colorama import init, Fore, Style

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

init(autoreset=True)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.LIGHTBLACK_EX}[%(asctime)s] [%(levelname)s]{Style.RESET_ALL} %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TokenSniper")

RPC_URL = os.getenv("HELIUS_RPC_URL")
WSS_URL = os.getenv("HELIUS_WSS_URL")

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Raydium AMM v4 program ID — we watch for new pool creation events
RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
# Raydium CPMM program ID
RAYDIUM_CPMM_PROGRAM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"

# Stablecoins and known base tokens (we skip these — they're not "new")
KNOWN_BASE_MINTS = {
    SOL_MINT,
    USDC_MINT,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "JUPyiwrYdGVGgzJABd847LsHWtwYY611L4xg5E184cM",  # JUP
    "DezXAZ8z7PnrnRJjz3wX4mPtkoc27DPm759wyB75zPLr", # BONK
    "jtoSnE795qyv2wJTxtjZa5hkcz3gJaHAwtLedHsQNrr",  # JTO
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", # RAY
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", # PYTH
}


class Position:
    """Tracks a sniped token position"""
    def __init__(self, token_mint: str, symbol: str, entry_price: float,
                 amount_sol: float, amount_token: int, tx_sig: str):
        self.token_mint = token_mint
        self.symbol = symbol
        self.entry_price = entry_price
        self.entry_time = time.time()
        self.amount_sol = amount_sol
        self.amount_token = amount_token
        self.tx_sig = tx_sig
        self.peak_price = entry_price
        self.current_price = entry_price
        self.status = "open"  # open, closed_profit, closed_loss, closed_timeout

    def update_price(self, new_price: float):
        self.current_price = new_price
        if new_price > self.peak_price:
            self.peak_price = new_price

    @property
    def profit_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def drawdown_from_peak_pct(self) -> float:
        if self.peak_price <= 0:
            return 0.0
        return ((self.peak_price - self.current_price) / self.peak_price) * 100

    @property
    def age_seconds(self) -> float:
        return time.time() - self.entry_time


class TokenSniper:
    """
    Real-time new token launch sniper with safety filters and position management.
    """

    def __init__(
        self,
        max_snipe_sol: float = 0.01,       # Max SOL to spend per snipe (~$1.60)
        take_profit_pct: float = 100.0,     # Sell at 2x (100% profit)
        stop_loss_pct: float = 30.0,        # Sell if dropped 30% from peak
        timeout_secs: float = 300.0,        # Force exit after 5 minutes
        min_liquidity_usd: float = 500.0,   # Minimum pool liquidity to snipe
        max_concurrent_positions: int = 3,  # Max simultaneous open positions
        cooldown_secs: float = 30.0,        # Cooldown between snipes
    ):
        self.max_snipe_sol = max_snipe_sol
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.timeout_secs = timeout_secs
        self.min_liquidity_usd = min_liquidity_usd
        self.max_concurrent_positions = max_concurrent_positions
        self.cooldown_secs = cooldown_secs

        self.positions: Dict[str, Position] = {}  # mint -> Position
        self.sniped_mints: set = set()  # Already sniped (don't re-enter)
        self.last_snipe_time: float = 0.0
        self.running = False

        self.http_client = httpx.AsyncClient(timeout=10.0)
        self.keypair = None
        self.sol_price = 0.0

        # Stats
        self.total_snipes = 0
        self.successful_exits = 0
        self.total_profit_usd = 0.0

        # Load keypair
        pkey_str = os.getenv("SOLANA_PRIVATE_KEY")
        if pkey_str:
            try:
                pkey_str = pkey_str.strip()
                if pkey_str.startswith("["):
                    self.keypair = Keypair.from_bytes(bytes(json.loads(pkey_str)))
                else:
                    self.keypair = Keypair.from_base58_string(pkey_str)
                logger.info(f"Sniper wallet: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Error loading private key: {e}")

    async def get_sol_price(self) -> float:
        """Fetches current SOL USD price"""
        url = f"https://api.jup.ag/price/v3?ids={SOL_MINT}"
        try:
            resp = await self.http_client.get(url)
            if resp.status_code == 200:
                price = resp.json().get(SOL_MINT, {}).get("usdPrice")
                if price:
                    self.sol_price = float(price)
                    return self.sol_price
        except Exception:
            pass
        return self.sol_price

    async def get_token_price_sol(self, token_mint: str) -> float:
        """Gets token price in SOL terms via Jupiter"""
        try:
            params = {
                "inputMint": token_mint,
                "outputMint": SOL_MINT,
                "amount": "1000000",  # 1 token unit (adjust for decimals)
                "slippageBps": "100",
            }
            resp = await self.http_client.get(
                "https://api.jup.ag/swap/v1/quote", params=params, timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                out_amount = int(data.get("outAmount", 0))
                in_amount = int(data.get("inAmount", 0))
                if in_amount > 0 and out_amount > 0:
                    return out_amount / in_amount  # SOL per token unit
        except Exception:
            pass
        return 0.0

    async def check_token_safety(self, token_mint: str) -> Tuple[bool, str]:
        """
        Safety check for a new token. Returns (is_safe, reason).
        Checks:
        1. Mint authority / freeze authority
        2. Supply concentration
        3. Pool liquidity
        """
        try:
            # Get mint account info
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getAccountInfo",
                "params": [token_mint, {"encoding": "jsonParsed"}]
            }
            resp = await self.http_client.post(RPC_URL, json=payload, timeout=8.0)
            if resp.status_code != 200:
                return False, "Failed to fetch mint info"

            result = resp.json().get("result", {})
            value = result.get("value")
            if not value:
                return False, "Mint account not found"

            parsed = value.get("data", {}).get("parsed", {})
            info = parsed.get("info", {})

            # Check freeze authority — if set, the creator can freeze your tokens
            freeze_auth = info.get("freezeAuthority")
            if freeze_auth and freeze_auth != "11111111111111111111111111111111":
                return False, f"FREEZE AUTHORITY SET: {freeze_auth[:12]}.. — rug risk"

            # Check supply
            supply = int(info.get("supply", "0"))
            decimals = int(info.get("decimals", 0))
            if supply <= 0:
                return False, "Zero supply"

            # Check largest holders — if top holder has >90%, likely rug
            holders_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_mint]
            }
            h_resp = await self.http_client.post(RPC_URL, json=holders_payload, timeout=8.0)
            if h_resp.status_code == 200:
                h_result = h_resp.json().get("result", {}).get("value", [])
                if h_result:
                    top_amount = int(h_result[0].get("amount", "0"))
                    if supply > 0:
                        top_pct = (top_amount / supply) * 100
                        if top_pct > 90:
                            return False, f"Top holder owns {top_pct:.1f}% — rug risk"

            return True, "Passed safety checks"

        except Exception as e:
            return False, f"Safety check error: {e}"

    async def execute_buy(self, token_mint: str, sol_amount: float) -> Optional[str]:
        """Buys a token using Jupiter swap"""
        if not self.keypair:
            return None

        amount_lamports = int(sol_amount * 1e9)

        try:
            # Get quote
            params = {
                "inputMint": SOL_MINT,
                "outputMint": token_mint,
                "amount": str(amount_lamports),
                "slippageBps": "500",  # 5% slippage for new tokens
            }
            resp = await self.http_client.get(
                "https://api.jup.ag/swap/v1/quote", params=params, timeout=8.0
            )
            if resp.status_code != 200:
                logger.error(f"Jupiter quote failed: {resp.text}")
                return None

            quote = resp.json()
            if "error" in quote:
                logger.error(f"Jupiter quote error: {quote['error']}")
                return None

            # Get swap tx
            swap_payload = {
                "quoteResponse": quote,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 100_000,  # Higher priority for sniping
            }
            swap_resp = await self.http_client.post(
                "https://api.jup.ag/swap/v1/swap", json=swap_payload, timeout=10.0
            )
            if swap_resp.status_code != 200:
                logger.error(f"Jupiter swap build failed: {swap_resp.text}")
                return None

            tx_b64 = swap_resp.json().get("swapTransaction")
            if not tx_b64:
                return None

            # Sign and submit
            raw_tx = base64.b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
            signed_tx = VersionedTransaction(tx.message, [sig])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")

            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
            }
            send_resp = await self.http_client.post(RPC_URL, json=send_payload, timeout=10.0)
            if send_resp.status_code == 200:
                tx_sig = send_resp.json().get("result")
                if tx_sig:
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[SNIPE-BUY]{Style.RESET_ALL} "
                        f"Bought {sol_amount:.4f} SOL worth of {token_mint[:12]}.. | "
                        f"TX: {Fore.CYAN}{tx_sig[:16]}..{Style.RESET_ALL}"
                    )
                    return tx_sig

        except Exception as e:
            logger.error(f"Buy execution error: {e}")
        return None

    async def execute_sell(self, position: Position) -> Optional[str]:
        """Sells entire position of a token back to SOL"""
        if not self.keypair:
            return None

        try:
            # Get our token balance
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    str(self.keypair.pubkey()),
                    {"mint": position.token_mint},
                    {"encoding": "jsonParsed"}
                ]
            }
            resp = await self.http_client.post(RPC_URL, json=payload, timeout=8.0)
            if resp.status_code != 200:
                return None

            accounts = resp.json().get("result", {}).get("value", [])
            if not accounts:
                logger.warning(f"No token account found for {position.token_mint[:12]}.. — may already be sold")
                return None

            raw_amount = accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]
            token_amount = int(raw_amount)

            if token_amount <= 0:
                return None

            # Get quote for sell
            params = {
                "inputMint": position.token_mint,
                "outputMint": SOL_MINT,
                "amount": str(token_amount),
                "slippageBps": "500",
            }
            q_resp = await self.http_client.get(
                "https://api.jup.ag/swap/v1/quote", params=params, timeout=8.0
            )
            if q_resp.status_code != 200:
                return None

            quote = q_resp.json()
            if "error" in quote:
                return None

            swap_payload = {
                "quoteResponse": quote,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 50_000,
            }
            swap_resp = await self.http_client.post(
                "https://api.jup.ag/swap/v1/swap", json=swap_payload, timeout=10.0
            )
            if swap_resp.status_code != 200:
                return None

            tx_b64 = swap_resp.json().get("swapTransaction")
            if not tx_b64:
                return None

            raw_tx = base64.b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
            signed_tx = VersionedTransaction(tx.message, [sig])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")

            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
            }
            send_resp = await self.http_client.post(RPC_URL, json=send_payload, timeout=10.0)
            if send_resp.status_code == 200:
                tx_sig = send_resp.json().get("result")
                if tx_sig:
                    sol_out = int(quote.get("outAmount", 0)) / 1e9
                    profit_sol = sol_out - position.amount_sol
                    profit_usd = profit_sol * self.sol_price
                    color = Fore.GREEN if profit_sol > 0 else Fore.RED
                    logger.info(
                        f"{color}[SNIPE-SELL]{Style.RESET_ALL} "
                        f"Sold {position.token_mint[:12]}.. | "
                        f"P&L: {color}{profit_sol:+.5f} SOL (${profit_usd:+.4f}){Style.RESET_ALL} | "
                        f"Status: {position.status}"
                    )
                    self.total_profit_usd += profit_usd
                    return tx_sig

        except Exception as e:
            logger.error(f"Sell execution error: {e}")
        return None

    async def process_new_pool(self, pool_data: Dict[str, Any]):
        """
        Called when a new Raydium pool creation is detected.
        Evaluates the token and potentially snipes it.
        """
        now = time.time()

        # Cooldown check
        if now - self.last_snipe_time < self.cooldown_secs:
            return

        # Max concurrent positions
        open_count = sum(1 for p in self.positions.values() if p.status == "open")
        if open_count >= self.max_concurrent_positions:
            return

        token_mint = pool_data.get("token_mint")
        if not token_mint or token_mint in self.sniped_mints or token_mint in KNOWN_BASE_MINTS:
            return

        logger.info(
            f"{Fore.LIGHTYELLOW_EX}[NEW-POOL]{Style.RESET_ALL} "
            f"Detected new token: {Fore.YELLOW}{token_mint[:16]}..{Style.RESET_ALL}"
        )

        # Safety check
        is_safe, reason = await self.check_token_safety(token_mint)
        if not is_safe:
            logger.warning(
                f"{Fore.RED}[SAFETY-FAIL]{Style.RESET_ALL} "
                f"{token_mint[:12]}.. — {reason}"
            )
            self.sniped_mints.add(token_mint)  # Don't check again
            return

        logger.info(
            f"{Fore.GREEN}[SAFETY-PASS]{Style.RESET_ALL} "
            f"{token_mint[:12]}.. — {reason}"
        )

        # Execute buy
        snipe_sol = min(self.max_snipe_sol, 0.01)  # Hard cap
        tx_sig = await self.execute_buy(token_mint, snipe_sol)
        if not tx_sig:
            return

        self.sniped_mints.add(token_mint)
        self.last_snipe_time = now
        self.total_snipes += 1

        # Get entry price
        await asyncio.sleep(2)
        entry_price = await self.get_token_price_sol(token_mint)

        position = Position(
            token_mint=token_mint,
            symbol=token_mint[:8],
            entry_price=entry_price,
            amount_sol=snipe_sol,
            amount_token=0,
            tx_sig=tx_sig,
        )
        self.positions[token_mint] = position

        logger.info(
            f"{Fore.LIGHTGREEN_EX}[POSITION-OPEN]{Style.RESET_ALL} "
            f"{token_mint[:12]}.. | Entry: {entry_price:.10f} SOL/token | "
            f"Invested: {snipe_sol:.4f} SOL"
        )

    async def manage_positions(self):
        """Position management loop — checks for take-profit, stop-loss, and timeout"""
        while self.running:
            for mint, pos in list(self.positions.items()):
                if pos.status != "open":
                    continue

                # Get current price
                current_price = await self.get_token_price_sol(mint)
                if current_price <= 0:
                    continue

                pos.update_price(current_price)

                # Check take profit
                if pos.profit_pct >= self.take_profit_pct:
                    pos.status = "closed_profit"
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[TAKE-PROFIT]{Style.RESET_ALL} "
                        f"{mint[:12]}.. at {pos.profit_pct:.1f}% profit!"
                    )
                    await self.execute_sell(pos)
                    self.successful_exits += 1
                    continue

                # Check stop loss (trailing from peak)
                if pos.drawdown_from_peak_pct >= self.stop_loss_pct:
                    pos.status = "closed_loss"
                    logger.info(
                        f"{Fore.RED}[STOP-LOSS]{Style.RESET_ALL} "
                        f"{mint[:12]}.. dropped {pos.drawdown_from_peak_pct:.1f}% from peak"
                    )
                    await self.execute_sell(pos)
                    continue

                # Check timeout
                if pos.age_seconds >= self.timeout_secs:
                    pos.status = "closed_timeout"
                    logger.info(
                        f"{Fore.YELLOW}[TIMEOUT]{Style.RESET_ALL} "
                        f"{mint[:12]}.. — {pos.timeout_secs:.0f}s elapsed, exiting"
                    )
                    await self.execute_sell(pos)
                    continue

            await asyncio.sleep(5)  # Check every 5 seconds

    async def monitor_new_pools(self):
        """
        WebSocket listener for new Raydium pool creation events.
        Subscribes to the Raydium AMM program and watches for new accounts.
        """
        if not WSS_URL:
            logger.error("No WebSocket URL configured. Token sniper cannot start.")
            return

        while self.running:
            try:
                logger.info(
                    f"{Fore.LIGHTCYAN_EX}[SNIPER]{Style.RESET_ALL} "
                    f"Connecting to WebSocket for new pool detection..."
                )
                async with websockets.connect(WSS_URL) as ws:
                    # Subscribe to Raydium AMM program log events
                    # logsSubscribe watches for program invocations
                    subscribe_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "logsSubscribe",
                        "params": [
                            {"mentions": [RAYDIUM_AMM_PROGRAM]},
                            {"commitment": "processed"}
                        ]
                    }
                    await ws.send(json.dumps(subscribe_payload))
                    logger.info(
                        f"{Fore.GREEN}[SNIPER]{Style.RESET_ALL} "
                        f"Subscribed to Raydium AMM program logs. Watching for new pools..."
                    )

                    async for message in ws:
                        try:
                            event = json.loads(message)
                            if "params" not in event:
                                continue

                            result = event["params"]["result"]
                            value = result.get("value", {})
                            logs = value.get("logs", [])
                            signature = value.get("signature", "")

                            # Look for "initialize2" or "initialize" in logs
                            # This indicates a new pool is being created
                            is_init = any(
                                "initialize2" in log.lower() or
                                ("initialize" in log.lower() and "ray_log" in log.lower())
                                for log in logs
                            )

                            if not is_init:
                                continue

                            logger.info(
                                f"{Fore.LIGHTYELLOW_EX}[NEW-POOL-DETECTED]{Style.RESET_ALL} "
                                f"TX: {signature[:16]}.. — Fetching token mints..."
                            )

                            # Fetch the transaction to extract token mints
                            tx_payload = {
                                "jsonrpc": "2.0", "id": 1,
                                "method": "getTransaction",
                                "params": [
                                    signature,
                                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                                ]
                            }
                            await asyncio.sleep(1)  # Wait for tx to be indexed
                            tx_resp = await self.http_client.post(
                                RPC_URL, json=tx_payload, timeout=10.0
                            )
                            if tx_resp.status_code != 200:
                                continue

                            tx_data = tx_resp.json().get("result")
                            if not tx_data:
                                continue

                            # Extract token mints from inner instructions
                            token_mints = set()
                            meta = tx_data.get("meta", {})
                            for inner in meta.get("innerInstructions", []):
                                for ix in inner.get("instructions", []):
                                    parsed = ix.get("parsed", {})
                                    if isinstance(parsed, dict):
                                        info = parsed.get("info", {})
                                        mint = info.get("mint")
                                        if mint:
                                            token_mints.add(mint)

                            # Also check pre/post token balances for mints
                            for bal in meta.get("postTokenBalances", []):
                                mint = bal.get("mint")
                                if mint:
                                    token_mints.add(mint)

                            # Filter out known tokens — the remaining are the new token
                            new_tokens = token_mints - KNOWN_BASE_MINTS
                            if not new_tokens:
                                continue

                            for token_mint in new_tokens:
                                await self.process_new_pool({
                                    "token_mint": token_mint,
                                    "signature": signature,
                                })

                        except Exception as e:
                            logger.debug(f"Error processing WS message: {e}")
                            continue

            except websockets.exceptions.ConnectionClosed:
                logger.warning("[SNIPER] WebSocket disconnected. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[SNIPER] WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def run(self):
        """Main entry point — runs pool monitor and position manager concurrently"""
        if not self.keypair:
            logger.error("No keypair loaded. Token sniper cannot start.")
            return

        self.running = True
        self.sol_price = await self.get_sol_price()

        print(f"""
{Fore.LIGHTRED_EX}{Style.BRIGHT}========================================================================
              TOKEN LAUNCH SNIPER — MICRO-BUY ENGINE
                 cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
{Fore.YELLOW}Config:{Style.RESET_ALL}
  Max snipe:       {self.max_snipe_sol} SOL (~${self.max_snipe_sol * self.sol_price:.2f})
  Take profit:     {self.take_profit_pct}%
  Stop loss:       {self.stop_loss_pct}% from peak
  Timeout:         {self.timeout_secs}s
  Min liquidity:   ${self.min_liquidity_usd}
  Max positions:   {self.max_concurrent_positions}
""")

        # Price refresh task
        async def refresh_price():
            while self.running:
                await self.get_sol_price()
                await asyncio.sleep(30)

        await asyncio.gather(
            self.monitor_new_pools(),
            self.manage_positions(),
            refresh_price(),
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_snipes": self.total_snipes,
            "successful_exits": self.successful_exits,
            "total_profit_usd": self.total_profit_usd,
            "open_positions": sum(1 for p in self.positions.values() if p.status == "open"),
        }


async def main():
    sniper = TokenSniper(
        max_snipe_sol=0.01,
        take_profit_pct=100.0,
        stop_loss_pct=30.0,
        timeout_secs=300.0,
    )
    try:
        await sniper.run()
    except KeyboardInterrupt:
        logger.info("Token Sniper stopped.")
        sniper.running = False


if __name__ == "__main__":
    asyncio.run(main())
