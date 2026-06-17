#!/usr/bin/env python3
"""
Copy Trading Engine — Follow Profitable Wallets on Solana
cook45 & clack // Systems & MEV

Monitors profitable wallets via Helius WebSocket, detects their trades,
and mirrors buys with configurable position sizing.
"""

import asyncio
import json
import time
import os
import base64
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from colorama import Fore, Style
import httpx
import websockets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("SolanaArbBot")

# ─── Constants ───────────────────────────────────────────────────────────────
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WSOL_MINT = SOL_MINT

# Known DEX program IDs to detect swaps
DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM v4",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "Raydium CPMM",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpool",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter v4",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump.fun",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
}

# Known stablecoins and major tokens to IGNORE (we want meme coins)
IGNORE_TOKENS = {
    SOL_MINT, USDC_MINT,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj", # stSOL
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",  # bSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn", # jitoSOL
}

# Curated Smart Money Wallets — pump.fun profitable traders
# Identified via DexScreener Top Traders, Dune Analytics, and on-chain analysis
# Selection criteria: >40% win rate, active in last 7d, 20+ trades, consistent PnL
DEFAULT_TRACKED_WALLETS = [
    # High-freq pump.fun sniper — 50+/day, small sizes, consistent 45%+ WR
    "Ai4zqY7gjyAPhtUsE6pFvMYLJRLybmNK3KkMdPpp11yh",
    # Smart accumulator — buys dips on bonding curve, holds to graduation, 3-5x avg
    "DNfuF1L62WWyW3pNakVMx3C5rR2ve6LxQwUbhFzKr1ra",
    # Early bird sniper — buys within 10s of creation, uses Jito bundles
    "7ooTHMH2JPhKfFjsVZjUc6bx2vPyZEwvBaZxQsFKCmXp",
    # Whale copy target — 0.5-2 SOL trades, follows narrative trends
    "BKPsqs2q9VsZMSaXnTuLkUUKWz1Bo56xkCAiGfF4RxCr",
    # Graduation sniper — targets 80%+ filled bonding curves, rides graduation pump
    "ARxa1uawDPpSGbnCtw1CbZrxCJPGTYzxS3QWvZW6dmJd",
]

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
RPC_WSS = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Jupiter swap endpoints
JUP_QUOTE = "https://api.jup.ag/swap/v1/quote"
JUP_SWAP = "https://api.jup.ag/swap/v1/swap"


@dataclass
class CopyPosition:
    """Active copy trade position"""
    token_mint: str
    entry_price_usd: float
    amount_sol: float
    amount_tokens: int
    peak_price_usd: float
    entry_time: float
    source_wallet: str
    tx_sig: str
    status: str = "active"  # active, sold, timeout, stopped


class CopyTrader:
    """
    Monitors profitable wallets and mirrors their token purchases.
    Uses Helius WebSocket for real-time transaction detection.
    """

    def __init__(
        self,
        tracked_wallets: Optional[List[str]] = None,
        max_trade_sol: float = 0.005,
        take_profit_pct: float = 50.0,
        stop_loss_pct: float = 25.0,
        timeout_secs: float = 300.0,
        max_concurrent_positions: int = 3,
        dry_run: bool = True,
    ):
        self.tracked_wallets = tracked_wallets or DEFAULT_TRACKED_WALLETS
        self.max_trade_sol = max_trade_sol
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.timeout_secs = timeout_secs
        self.max_concurrent = max_concurrent_positions
        self.dry_run = dry_run

        self.positions: Dict[str, CopyPosition] = {}
        self.trades_detected = 0
        self.trades_copied = 0
        self.running = False
        self.sol_price_usd = 80.0

        self.http = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_connections=20),
        )

        # Load wallet
        self.keypair = None
        pkey = os.getenv("SOLANA_PRIVATE_KEY")
        if pkey:
            try:
                from solders.keypair import Keypair
                key_bytes = base64.b64decode(pkey) if len(pkey) > 64 else bytes.fromhex(pkey) if len(pkey) == 128 else None
                if key_bytes and len(key_bytes) == 64:
                    self.keypair = Keypair.from_bytes(key_bytes)
                else:
                    self.keypair = Keypair.from_base58_string(pkey)
                logger.info(f"Copy trader wallet: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Failed to load keypair for copy trader: {e}")

    async def _fetch_sol_price(self):
        """Refresh SOL price from Jupiter"""
        try:
            resp = await self.http.get(
                f"https://api.jup.ag/price/v3?ids={SOL_MINT}", timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                p = data.get("data", {}).get(SOL_MINT, {}).get("price")
                if p:
                    self.sol_price_usd = float(p)
        except Exception:
            pass

    async def _get_token_price_usd(self, token_mint: str) -> float:
        """Get a token's price in USD from Jupiter"""
        try:
            resp = await self.http.get(
                f"https://api.jup.ag/price/v3?ids={token_mint}", timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                p = data.get("data", {}).get(token_mint, {}).get("price")
                if p:
                    return float(p)
        except Exception:
            pass
        return 0.0

    async def _parse_tx_for_swap(self, signature: str, tracked_wallet: str) -> Optional[Dict]:
        """
        Use getTransaction with jsonParsed to reliably detect swaps, identify the token involved,
        and determine whether it was a BUY or SELL for the tracked wallet or its owner.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        }
        try:
            resp = await self.http.post(RPC_HTTP, json=payload, timeout=10.0)
            if resp.status_code != 200:
                return None
            result = resp.json().get("result")
            if not result:
                return None

            meta = result.get("meta", {})
            if not meta or meta.get("err"):
                return None

            tx = result.get("transaction", {})
            message = tx.get("message", {})
            account_keys = [k.get("pubkey") if isinstance(k, dict) else k for k in message.get("accountKeys", [])]
            if not account_keys:
                return None

            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])

            # Find the non-SOL/USDC token mint involved in the swap
            token_mint = None
            for b in pre_balances + post_balances:
                mint = b.get("mint")
                if mint and mint not in IGNORE_TOKENS:
                    token_mint = mint
                    break

            if not token_mint:
                return None

            # Map account index to its owner
            account_owners = {}
            for b in pre_balances + post_balances:
                idx = b.get("accountIndex")
                owner = b.get("owner")
                if idx is not None and owner:
                    account_owners[idx] = owner

            # Check if the tracked wallet is involved in the transaction (either as account key or owner)
            tracked_wallet_involved = False
            for idx, pubkey in enumerate(account_keys):
                if pubkey == tracked_wallet:
                    tracked_wallet_involved = True
                    break
            
            if not tracked_wallet_involved:
                for idx, owner in account_owners.items():
                    if owner == tracked_wallet:
                        tracked_wallet_involved = True
                        break

            if not tracked_wallet_involved:
                return None

            # Determine target owners (tracked wallet itself, and its main owner if it is a token account)
            target_owners = {tracked_wallet}
            for idx, pubkey in enumerate(account_keys):
                if pubkey == tracked_wallet:
                    owner = account_owners.get(idx)
                    if owner:
                        target_owners.add(owner)

            # Calculate balance change of token_mint for the target owners
            pre_amount = 0.0
            post_amount = 0.0

            for b in pre_balances:
                if b.get("mint") == token_mint:
                    owner = b.get("owner")
                    idx = b.get("accountIndex")
                    token_account_pubkey = account_keys[idx] if idx < len(account_keys) else None
                    if owner in target_owners or token_account_pubkey == tracked_wallet:
                        pre_amount += float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)

            for b in post_balances:
                if b.get("mint") == token_mint:
                    owner = b.get("owner")
                    idx = b.get("accountIndex")
                    token_account_pubkey = account_keys[idx] if idx < len(account_keys) else None
                    if owner in target_owners or token_account_pubkey == tracked_wallet:
                        post_amount += float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)

            change = post_amount - pre_amount

            if change > 0:
                trade_type = "buy"
            elif change < 0:
                trade_type = "sell"
            else:
                return None

            # Determine DEX program
            dex_found = "unknown"
            for pid in account_keys:
                if pid in DEX_PROGRAMS:
                    dex_found = DEX_PROGRAMS[pid]
                    break

            return {
                "type": trade_type,
                "dex": dex_found,
                "token_mint": token_mint,
                "amount": abs(change),
            }
        except Exception as e:
            logger.debug(f"[COPY-TRADE] parse_tx_for_swap error: {e}")
            return None

    async def _execute_jupiter_buy(self, token_mint: str, sol_amount: float) -> Optional[str]:
        """Buy a token via Jupiter swap API"""
        if not self.keypair:
            logger.error("[COPY-TRADE] No keypair loaded")
            return None

        try:
            from solders.transaction import VersionedTransaction

            lamports = int(sol_amount * 1e9)

            # Get quote
            quote_resp = await self.http.get(
                JUP_QUOTE,
                params={
                    "inputMint": SOL_MINT,
                    "outputMint": token_mint,
                    "amount": str(lamports),
                    "slippageBps": "100",  # 1% slippage for copy trades
                },
                timeout=10.0,
            )

            if quote_resp.status_code != 200:
                logger.warning(f"[COPY-TRADE] Jupiter quote failed: {quote_resp.status_code}")
                return None

            quote = quote_resp.json()

            if "error" in quote:
                logger.warning(f"[COPY-TRADE] Quote error: {quote['error']}")
                return None

            # Get swap transaction
            swap_resp = await self.http.post(
                JUP_SWAP,
                json={
                    "quoteResponse": quote,
                    "userPublicKey": str(self.keypair.pubkey()),
                    "wrapAndUnwrapSol": True,
                    "prioritizationFeeLamports": 100_000,
                },
                timeout=10.0,
            )

            if swap_resp.status_code != 200:
                logger.warning(f"[COPY-TRADE] Jupiter swap failed: {swap_resp.status_code}")
                return None

            swap_data = swap_resp.json()
            swap_tx_b64 = swap_data.get("swapTransaction")
            if not swap_tx_b64:
                logger.warning("[COPY-TRADE] No swapTransaction in response")
                return None

            # Deserialize, sign, and submit
            raw_tx = base64.b64decode(swap_tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            signed_tx = VersionedTransaction(tx.message, [self.keypair])

            encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [
                    encoded,
                    {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
                ]
            }

            send_resp = await self.http.post(RPC_HTTP, json=send_payload, timeout=15.0)
            if send_resp.status_code == 200:
                result = send_resp.json()
                if "result" in result:
                    sig = result["result"]
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[COPY-BUY]{Style.RESET_ALL} "
                        f"TX: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}"
                    )
                    return sig
                else:
                    logger.warning(f"[COPY-TRADE] TX error: {result.get('error', {})}")

        except Exception as e:
            logger.error(f"[COPY-TRADE] Buy execution error: {e}")

        return None

    async def _execute_pumpportal_trade(self, action: str, mint: str, amount: Any, slippage_pct: int = 25, denominated_in_sol: bool = True, pool: str = "pump") -> Optional[str]:
        """Execute buy or sell via PumpPortal Trade API with dynamic pool fallbacks"""
        try:
            from solders.transaction import VersionedTransaction
            logger.info(f"  [COPY-PUMP] Invoking PumpPortal HTTP Trade API compilation for {action} (pool: {pool})...")
            
            payload = {
                "publicKey": str(self.keypair.pubkey()),
                "action": action,
                "mint": mint,
                "amount": str(amount),
                "denominatedInSol": "true" if denominated_in_sol else "false",
                "slippage": slippage_pct,
                "priorityFee": 0.0001,
                "pool": pool,
            }
            
            resp = await self.http.post(
                "https://pumpportal.fun/api/trade-local",
                json=payload,
                timeout=10.0
            )
            if resp.status_code != 200:
                logger.warning(f"[COPY-PUMP-API] error {resp.status_code}: {resp.text[:200]}")
                # Fallback to pump-amm pool if token migrated
                if pool == "pump" and "migrated" in resp.text:
                    logger.info("  [COPY-PUMP-FALLBACK] Token migrated, retrying with pool='pump-amm'...")
                    return await self._execute_pumpportal_trade(action, mint, amount, slippage_pct, denominated_in_sol, pool="pump-amm")
                return None
                
            tx_bytes = resp.content
            tx_api = VersionedTransaction.from_bytes(tx_bytes)
            signed_tx = VersionedTransaction(tx_api.message, [self.keypair])

            encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [
                    encoded,
                    {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
                ]
            }

            resp_rpc = await self.http.post(RPC_HTTP, json=send_payload, timeout=15.0)
            if resp_rpc.status_code == 200:
                result = resp_rpc.json()
                if "result" in result:
                    sig = result["result"]
                    logger.info(f"  [COPY-PUMP] TX submitted: {sig[:16]}... Checking confirmation...")
                    
                    confirmed = False
                    for attempt in range(15):
                        await asyncio.sleep(1.0)
                        try:
                            status_payload = {
                                "jsonrpc": "2.0", "id": 1,
                               "method": "getSignatureStatuses",
                                "params": [[sig]]
                            }
                            status_resp = await self.http.post(RPC_HTTP, json=status_payload, timeout=3.0)
                            if status_resp.status_code == 200:
                                status_data = status_resp.json().get("result", {}).get("value", [None])[0]
                                if status_data:
                                    err = status_data.get("err")
                                    if err is None:
                                        confirmations = status_data.get("confirmations")
                                        if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                            logger.info(f"  [COPY-PUMP] Transaction confirmed! Sig: {sig[:16]}")
                                            confirmed = True
                                            break
                                    else:
                                        logger.warning(f"  [COPY-PUMP] Transaction failed on-chain: {err}")
                                        return None
                        except Exception:
                            pass
                    if confirmed:
                        return sig
            return None
        except Exception as e:
            logger.error(f"[COPY-PUMP] Trade execution error: {e}")
            return None

    async def _execute_jupiter_sell(
        self, 
        token_mint: str, 
        token_amount: int,
        escalate_attempts: int = 5
    ) -> Optional[str]:
        """Sell tokens back to SOL via Jupiter with prioritized exit-assurance retries"""
        if not self.keypair:
            return None

        base_fee_lamports = 100_000  # ~0.0001 SOL
        slippage_bps = 150  # 1.5%

        for attempt in range(escalate_attempts):
            try:
                from solders.transaction import VersionedTransaction

                # Scale priority fee and slippage on failure
                fee_lamports = min(base_fee_lamports * (2 ** attempt), 1_000_000)  # scale up to 0.001 SOL tip
                if attempt > 0:
                    slippage_bps = 500  # Raise slippage to 5.0% to force completion
                    logger.info(
                        f"  {Fore.YELLOW}[COPY-SELL-RETRY]{Style.RESET_ALL} Attempt {attempt+1}/{escalate_attempts} for {token_mint[:8]}... | "
                        f"Priority fee: {fee_lamports} lamports | Slippage: 5.0%"
                    )

                quote_resp = await self.http.get(
                    JUP_QUOTE,
                    params={
                        "inputMint": token_mint,
                        "outputMint": SOL_MINT,
                        "amount": str(token_amount),
                        "slippageBps": str(slippage_bps),
                    },
                    timeout=10.0,
                )

                if quote_resp.status_code != 200:
                    await asyncio.sleep(1.0)
                    continue

                quote = quote_resp.json()
                if "error" in quote:
                    await asyncio.sleep(1.0)
                    continue

                swap_resp = await self.http.post(
                    JUP_SWAP,
                    json={
                        "quoteResponse": quote,
                        "userPublicKey": str(self.keypair.pubkey()),
                        "wrapAndUnwrapSol": True,
                        "prioritizationFeeLamports": fee_lamports,
                    },
                    timeout=10.0,
                )

                if swap_resp.status_code != 200:
                    await asyncio.sleep(1.0)
                    continue

                swap_data = swap_resp.json()
                swap_tx_b64 = swap_data.get("swapTransaction")
                if not swap_tx_b64:
                    await asyncio.sleep(1.0)
                    continue

                raw_tx = base64.b64decode(swap_tx_b64)
                tx = VersionedTransaction.from_bytes(raw_tx)
                signed_tx = VersionedTransaction(tx.message, [self.keypair])

                encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                send_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        encoded,
                        {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
                    ]
                }

                send_resp = await self.http.post(RPC_HTTP, json=send_payload, timeout=15.0)
                if send_resp.status_code == 200:
                    result = send_resp.json()
                    if "result" in result:
                        sig = result["result"]
                        
                        # Wait for confirmation (up to 10 seconds per attempt)
                        confirmed = False
                        for _ in range(10):
                            await asyncio.sleep(1.0)
                            try:
                                status_payload = {
                                    "jsonrpc": "2.0", "id": 1,
                                    "method": "getSignatureStatuses",
                                    "params": [[sig]]
                                }
                                status_resp = await self.http.post(RPC_HTTP, json=status_payload, timeout=3.0)
                                if status_resp.status_code == 200:
                                    status_data = status_resp.json().get("result", {}).get("value", [None])[0]
                                    if status_data:
                                        err = status_data.get("err")
                                        if err is None:
                                            confirmations = status_data.get("confirmations")
                                            if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                                confirmed = True
                                                break
                                        else:
                                            break
                            except Exception:
                                pass
                        
                        if confirmed:
                            return sig

            except Exception as e:
                logger.error(f"[COPY-SELL] Error on attempt {attempt+1}: {e}")

            await asyncio.sleep(1.0)

        return None

    async def _handle_wallet_trade(self, wallet: str, swap_info: Dict):
        """Process a detected trade from a tracked wallet"""
        self.trades_detected += 1
        token_mint = swap_info.get("token_mint")
        dex = swap_info.get("dex", "unknown")
        trade_type = swap_info.get("type", "buy")

        if not token_mint:
            return

        # Skip if not buy
        if trade_type != "buy":
            logger.debug(f"  → Ignored {trade_type} trade for {token_mint[:12]}...")
            return

        # Skip if already holding
        if token_mint in self.positions:
            logger.debug(f"  → Already holding {token_mint[:12]}...")
            return

        # Skip if max concurrent
        active = sum(1 for p in self.positions.values() if p.status == "active")
        if active >= self.max_concurrent:
            logger.debug(f"  → Max concurrent positions ({active}/{self.max_concurrent})")
            return

        logger.info(
            f"{Fore.LIGHTBLUE_EX}[COPY-DETECT]{Style.RESET_ALL} "
            f"Wallet {Fore.WHITE}{wallet[:8]}...{Style.RESET_ALL} "
            f"bought token on {Fore.YELLOW}{dex}{Style.RESET_ALL} | "
            f"Mint: {Fore.CYAN}{token_mint[:12]}...{Style.RESET_ALL}"
        )

        # Get token price
        price = await self._get_token_price_usd(token_mint)

        if self.dry_run:
            logger.info(
                f"  {Fore.LIGHTGREEN_EX}✓ WOULD COPY{Style.RESET_ALL} "
                f"— {self.max_trade_sol} SOL | Price: ${price:.8f} "
                f"[DRY RUN]"
            )
            self.positions[token_mint] = CopyPosition(
                token_mint=token_mint,
                entry_price_usd=price,
                amount_sol=self.max_trade_sol,
                amount_tokens=0,
                peak_price_usd=price,
                entry_time=time.time(),
                source_wallet=wallet,
                tx_sig="dry_run",
            )
            self.trades_copied += 1
            asyncio.create_task(self._monitor_single_position(token_mint))
            return

        # Execute real buy
        logger.info(
            f"  {Fore.LIGHTGREEN_EX}{Style.BRIGHT}⚡ COPYING{Style.RESET_ALL} "
            f"— {self.max_trade_sol} SOL"
        )

        sig = await self._execute_jupiter_buy(token_mint, self.max_trade_sol)
        if not sig and token_mint.endswith("pump"):
            logger.info("  [COPY-BUY] Jupiter route failed/unindexed. Falling back to PumpPortal bonding curve...")
            sig = await self._execute_pumpportal_trade("buy", token_mint, self.max_trade_sol)
        if sig:
            self.trades_copied += 1
            self.positions[token_mint] = CopyPosition(
                token_mint=token_mint,
                entry_price_usd=price if price > 0 else 0.001,
                amount_sol=self.max_trade_sol,
                amount_tokens=0,  # Will be fetched from chain
                peak_price_usd=price,
                entry_time=time.time(),
                source_wallet=wallet,
                tx_sig=sig,
            )
            logger.info(
                f"  {Fore.GREEN}✓ Position opened{Style.RESET_ALL} | TX: {sig[:16]}..."
            )
            asyncio.create_task(self._monitor_single_position(token_mint))
        else:
            logger.warning(f"  → Copy trade failed for {token_mint[:12]}...")

    async def _query_actual_balance_on_chain(self, mint: str) -> int:
        """Directly query the on-chain balance of a mint, returning raw_amount (handles Standard & Token-2022)"""
        from solders.pubkey import Pubkey
        mint_pubkey = Pubkey.from_string(mint)
        token_program = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        token2022_program = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")

        def derive_ata_local(wallet: Pubkey, mint: Pubkey, program_id: Pubkey) -> Pubkey:
            ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
            seeds = [bytes(wallet), bytes(program_id), bytes(mint)]
            ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
            return ata

        # 1. Try Token2022 first
        ata_2022 = derive_ata_local(self.keypair.pubkey(), mint_pubkey, token2022_program)
        try:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountBalance",
                "params": [str(ata_2022)]
            }
            resp = await self.http.post(RPC_HTTP, json=payload, timeout=5.0)
            if resp.status_code == 200 and "result" in resp.json():
                val = resp.json()["result"]["value"]
                raw_bal = int(val.get("amount", "0"))
                if raw_bal > 0:
                    return raw_bal
        except Exception:
            pass

        # 2. Try Standard Token next
        ata_std = derive_ata_local(self.keypair.pubkey(), mint_pubkey, token_program)
        try:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountBalance",
                "params": [str(ata_std)]
            }
            resp = await self.http.post(RPC_HTTP, json=payload, timeout=5.0)
            if resp.status_code == 200 and "result" in resp.json():
                val = resp.json()["result"]["value"]
                raw_bal = int(val.get("amount", "0"))
                if raw_bal > 0:
                    return raw_bal
        except Exception:
            pass

        return 0

    async def _execute_copy_sell(self, mint: str, token_amount: int) -> Optional[str]:
        """Sell tokens back to SOL via Jupiter first, falling back to PumpPortal for ungraduated pump.fun tokens"""
        sig = await self._execute_jupiter_sell(mint, token_amount)
        if not sig and mint.endswith("pump"):
            logger.info("  [COPY-SELL] Jupiter exit failed/unindexed. Falling back to PumpPortal bonding curve sell...")
            sig = await self._execute_pumpportal_trade("sell", mint, "100%", denominated_in_sol=False)
        return sig

    async def _monitor_single_position(self, mint: str):
        """Dedicated concurrent micro-monitor checking prices and executing exits for a single copy position"""
        pos = self.positions.get(mint)
        if not pos:
            return

        logger.info(
            f"{Fore.LIGHTCYAN_EX}[COPY-MICRO-MONITOR]{Style.RESET_ALL} "
            f"Started dedicated task for copy trade {mint[:8]}..."
        )

        # In live mode, we must query the Associated Token Account (ATA) balance 
        # with retries to allow the buy transaction to confirm on-chain.
        if not self.dry_run and pos.amount_tokens <= 0:
            for attempt in range(15):
                try:
                    raw_bal = await self._query_actual_balance_on_chain(mint)
                    if raw_bal > 0:
                        pos.amount_tokens = raw_bal
                        logger.info(f"  [Copy Monitor] Set amount_tokens on-chain: {pos.amount_tokens}")
                        break
                except Exception as e:
                    logger.debug(f"[Copy Monitor] Error fetching token balance on attempt {attempt+1}: {e}")
                await asyncio.sleep(1.0)

        # Helper to sell entire actual on-chain balance
        async def execute_exit():
            if not self.dry_run:
                # Query actual balance just in case
                actual_bal = await self._query_actual_balance_on_chain(mint)
                if actual_bal > 0:
                    logger.info(f"  [Copy Monitor] Exiting position with actual on-chain balance: {actual_bal}")
                    await self._execute_copy_sell(mint, actual_bal)
                else:
                    logger.warning(f"  [Copy Monitor] Attempted exit but actual balance is 0 for {mint[:8]}")

        while self.running and pos.status == "active":
            try:
                elapsed = time.time() - pos.entry_time

                # Timeout exit
                if elapsed >= self.timeout_secs:
                    logger.info(
                        f"{Fore.YELLOW}[COPY-TIMEOUT]{Style.RESET_ALL} "
                        f"Token {mint[:12]}... — held {elapsed:.0f}s, exiting..."
                    )
                    await execute_exit()
                    pos.status = "timeout"
                    break

                if not self.dry_run and pos.entry_price_usd > 0:
                    current_price = await self._get_token_price_usd(mint)
                    if current_price <= 0:
                        await asyncio.sleep(1.0)
                        continue

                    # Update peak
                    if current_price > pos.peak_price_usd:
                        pos.peak_price_usd = current_price

                    pnl_pct = ((current_price - pos.entry_price_usd) / pos.entry_price_usd) * 100

                    # Take profit
                    if pnl_pct >= self.take_profit_pct:
                        logger.info(
                            f"{Fore.LIGHTGREEN_EX}[COPY-TP]{Style.RESET_ALL} "
                            f"+{pnl_pct:.1f}% | Token {mint[:12]}..."
                        )
                        await execute_exit()
                        pos.status = "take_profit"
                        break

                    # Stop loss
                    if pnl_pct <= -self.stop_loss_pct:
                        logger.info(
                            f"{Fore.RED}[COPY-SL]{Style.RESET_ALL} "
                            f"{pnl_pct:.1f}% | Token {mint[:12]}..."
                        )
                        await execute_exit()
                        pos.status = "stop_loss"
                        break

                    # Trailing stop from peak
                    if pos.peak_price_usd > pos.entry_price_usd:
                        dd = ((pos.peak_price_usd - current_price) / pos.peak_price_usd) * 100
                        if dd >= self.stop_loss_pct:
                            logger.info(
                                f"{Fore.RED}[COPY-TRAIL]{Style.RESET_ALL} "
                                f"Drawdown {dd:.1f}% from peak | Token {mint[:12]}..."
                            )
                            await execute_exit()
                            pos.status = "trailing_stop"
                            break

                elif self.dry_run:
                    # In dry run, we just track timeout exit
                    if elapsed >= self.timeout_secs:
                        pos.status = "timeout"
                        break

            except Exception as e:
                logger.error(f"[COPY-MICRO-MONITOR] Error for {mint[:8]}: {e}")

            await asyncio.sleep(1.0)  # Polling every 1.0 second is perfect for Jupiter pricing

    async def _print_status(self):
        """Periodic status log"""
        while self.running:
            await asyncio.sleep(30)
            active = sum(1 for p in self.positions.values() if p.status == "active")
            mode = "DRY RUN" if self.dry_run else "LIVE"
            logger.info(
                f"{Fore.LIGHTBLUE_EX}[COPY-STATUS]{Style.RESET_ALL} "
                f"[{mode}] Tracking: {len(self.tracked_wallets)} wallets | "
                f"Detected: {self.trades_detected} | "
                f"Copied: {self.trades_copied} | "
                f"Active: {active}/{self.max_concurrent}"
            )

    async def run(self):
        """Main entry point — connects to Helius WebSocket and monitors wallets"""
        self.running = True
        mode = f"{Fore.RED}LIVE{Style.RESET_ALL}" if not self.dry_run else f"{Fore.YELLOW}DRY RUN{Style.RESET_ALL}"

        await self._fetch_sol_price()

        print(f"""
{Fore.LIGHTBLUE_EX}{Style.BRIGHT}========================================================================
                    COPY TRADING ENGINE
                 cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
Mode:           {mode}
Tracked wallets: {len(self.tracked_wallets)}
Trade size:     {self.max_trade_sol} SOL (~${self.max_trade_sol * self.sol_price_usd:.2f})
Take profit:    {self.take_profit_pct}%
Stop loss:      {self.stop_loss_pct}% trailing
Timeout:        {self.timeout_secs}s
Max positions:  {self.max_concurrent}
""")

        # Launch background tasks
        asyncio.create_task(self._print_status())

        # Main WebSocket loop with reconnect
        while self.running:
            try:
                logger.info(
                    f"{Fore.LIGHTBLUE_EX}[COPY-TRADER]{Style.RESET_ALL} "
                    f"Connecting to Helius WebSocket..."
                )

                async with websockets.connect(
                    RPC_WSS,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    # Subscribe to logsSubscribe for each tracked wallet
                    sub_ids = {}
                    for i, wallet in enumerate(self.tracked_wallets):
                        sub_msg = {
                            "jsonrpc": "2.0",
                            "id": 100 + i,
                            "method": "logsSubscribe",
                            "params": [
                                {"mentions": [wallet]},
                                {"commitment": "confirmed"}
                            ]
                        }
                        await ws.send(json.dumps(sub_msg))
                        logger.info(
                            f"  Tracking: {Fore.WHITE}{wallet[:12]}...{Style.RESET_ALL}"
                        )
                        await asyncio.sleep(0.2)

                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[COPY-TRADER]{Style.RESET_ALL} "
                        f"Subscribed to {len(self.tracked_wallets)} wallets. Watching for trades..."
                    )

                    async for message in ws:
                        try:
                            data = json.loads(message)

                            # Handle subscription confirmations
                            if "id" in data and "result" in data:
                                idx = data["id"] - 100
                                if 0 <= idx < len(self.tracked_wallets):
                                    sub_ids[data["result"]] = self.tracked_wallets[idx]
                                continue

                            # Handle log notifications
                            if data.get("method") == "logsNotification":
                                params = data.get("params", {})
                                result = params.get("result", {})
                                value = result.get("value", {})
                                logs = value.get("logs", [])
                                sig = value.get("signature", "")

                                # Determine which wallet this is from
                                sub_id = params.get("subscription")
                                wallet = sub_ids.get(sub_id, "unknown")

                                if not logs:
                                    continue

                                swap_info = await self._parse_tx_for_swap(sig, wallet)
                                if swap_info:
                                    await self._handle_wallet_trade(wallet, swap_info)
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"[COPY-TRADER] Handler error: {e}")
                        except websockets.exceptions.ConnectionClosed as e:
                            logger.warning(
                                f"[COPY-TRADER] WebSocket disconnected: {e}. Reconnecting in 3s..."
                            )
                            await asyncio.sleep(3)
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"[COPY-TRADER] WebSocket closed: {e}. Reconnecting in 3s..."
                )
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"[COPY-TRADER] WebSocket error: {e}")
                await asyncio.sleep(5)


async def main():
    import logging
    import colorama
    colorama.init()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("live_copy_trader.log", mode="w", encoding="utf-8"),
        ],
    )

    # Tracked wallets loaded from insider_wallets.json
    tracked_wallets = None
    try:
        if os.path.exists("insider_wallets.json"):
            with open("insider_wallets.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                tracked_wallets = data.get("wallets")
                logger.info(f"Loaded {len(tracked_wallets)} wallets from insider_wallets.json")
    except Exception as e:
        logger.error(f"Failed to load insider_wallets.json: {e}")

    # Read parameters from environment
    max_trade_sol = float(os.getenv("MAX_SNIPE_SOL", "0.001"))
    take_profit = float(os.getenv("TAKE_PROFIT_PCT", "50.0"))
    stop_loss = float(os.getenv("STOP_LOSS_PCT", "25.0"))
    timeout = float(os.getenv("TIMEOUT_SECS", "300.0"))
    max_positions = int(os.getenv("MAX_CONCURRENT", "3"))
    dry_run = os.getenv("DRY_RUN", "True").lower() == "true"

    trader = CopyTrader(
        tracked_wallets=tracked_wallets,
        max_trade_sol=max_trade_sol,
        take_profit_pct=take_profit,
        stop_loss_pct=stop_loss,
        timeout_secs=timeout,
        max_concurrent_positions=max_positions,
        dry_run=dry_run,
    )

    await trader.run()


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Copy Trader stopped cleanly by user.")
