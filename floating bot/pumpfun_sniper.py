#!/usr/bin/env python3
"""
Pump.fun Token Sniper — Real-Time Launch Detection & Micro-Buy Engine
cook45 & clack // Systems & MEV

Monitors PumpPortal WebSocket for new pump.fun token launches.
Applies smart filters, buys on bonding curve, manages positions.

This is the PRIMARY profit engine for low-balance wallets.
"""

import asyncio
import json
import time
import os
import base64
import struct
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from colorama import Fore, Style
import httpx
import websockets
import websockets
from dotenv import load_dotenv

from jito_mempool import JitoMempoolMonitor
from insider_tracker import InsiderTracker
from dev_tripwire import DevTripwire
from jito_bundle import JitoBundleEngine
from launch_predictor import LaunchPredictor
from backtester import PaperTradingEngine

# Load environmental variables at module level
load_dotenv()

def b58encode(v: bytes) -> str:
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(v, "big")
    result = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        result.append(alphabet[r])
    for b in v:
        if b == 0:
            result.append(alphabet[0])
        else:
            break
    result.reverse()
    return result.decode("ascii")


logger = logging.getLogger("SolanaArbBot")

# ─── Constants ───────────────────────────────────────────────────────────────
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_AMM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
PUMP_FEES_ID = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
PUMP_MIGRATION_ACCOUNT = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
PUMP_GLOBAL_ACCOUNT = "4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# PumpPortal endpoints
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
PUMPPORTAL_TRADE_API = "https://pumpportal.fun/api/trade-local"

# Bonding curve initial values
INITIAL_VIRTUAL_TOKEN_RESERVES = 1_073_000_000_000_000  # 1.073B tokens (6 decimals)
INITIAL_VIRTUAL_SOL_RESERVES = 30_000_000_000  # 30 SOL in lamports
INITIAL_REAL_TOKEN_RESERVES = 793_100_000_000_000  # 793.1M tokens
GRADUATION_SOL_THRESHOLD = 85_000_000_000  # ~85 SOL triggers graduation

# Scam name patterns to skip
SCAM_PATTERNS = [
    "test", "rug", "scam", "fake", "hack", "honeypot", "airdrop",
    "free", "presale", "send", "claim", "nft drop",
    "elon", "elonmusk",  # Typically scam impersonation
]

# RPC config
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
RPC_WSS = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"


@dataclass
class SniperPosition:
    """Tracks an active pump.fun snipe position"""
    token_mint: str
    token_name: str
    token_symbol: str
    bonding_curve: str
    entry_sol: float  # SOL spent
    entry_time: float
    entry_price: float  # SOL per token at entry
    token_amount: int  # Raw token amount received (6 decimals)
    peak_price: float  # Highest price seen since entry
    buy_tx: str  # Transaction signature
    status: str = "active"  # active, sold, timeout, stopped
    break_even_locked: bool = False  # Locked at +5% once it hits +15%
    profit_lock_30: bool = False     # Locked at +15% once it hits +30%
    # Phase 2: Tiered take-profit tracking
    sell_tier_1: bool = False  # Sold 40% at +50%
    sell_tier_2: bool = False  # Sold 30% at +100%
    # Phase 1: Dev wallet for monitoring
    dev_wallet: str = ""
    # Phase 2: Pressure baseline (entry bonding curve SOL reserves)
    entry_virtual_sol: int = 0
    total_sol_returned: float = 0.0
    jito_tip_paid: float = 0.0


class PumpFunSniper:
    """
    Real-time pump.fun token launch sniper.
    Detects new tokens via PumpPortal WebSocket, filters for quality,
    and buys on bonding curve with configurable risk parameters.
    """

    def __init__(
        self,
        max_snipe_sol: float = 0.005,
        take_profit_pct: float = 100.0,  # 2x
        stop_loss_pct: float = 30.0,
        timeout_secs: float = 300.0,
        max_concurrent: int = 3,
        min_name_length: int = 3,
        strict_cabal_mode: bool = False,
        jito_tip_pct: float = 5.0,        # 5% of trade size goes to Jito validator
        tripwire_slippage_pct: float = 100.0, # 100% slippage guarantees exit on rug
        dry_run: bool = True,
    ):
        self.max_snipe_sol = max_snipe_sol
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.timeout_secs = timeout_secs
        self.max_concurrent = max_concurrent
        self.min_name_length = min_name_length
        self.strict_cabal_mode = strict_cabal_mode
        self.jito_tip_pct = jito_tip_pct
        self.tripwire_slippage_pct = tripwire_slippage_pct
        self.dry_run = dry_run
        self.use_pumpportal_api_primary = os.getenv("USE_PUMPPORTAL_API_PRIMARY", "True").lower() == "true"

        # Offensive Modules
        self.insider_tracker = InsiderTracker()
        self.jito_bundle = JitoBundleEngine(dry_run=dry_run)
        self.tripwire = DevTripwire(rpc_wss_url=RPC_WSS)
        self.predictor = LaunchPredictor()
        self.paper_engine = PaperTradingEngine()

        # State
        self.positions: Dict[str, SniperPosition] = {}
        self.total_snipes = 0
        self.total_sells = 0
        self.total_profit_sol = 0.0
        self.tokens_seen = 0
        self.tokens_filtered = 0
        self.tokens_bought = 0
        self.running = False
        self.sol_price_usd = 0.0
        self._token_program_cache: Dict[str, str] = {}  # mint -> owner program ID string

        # HTTP client (with RPC Resiliency/Retries)
        transport = httpx.AsyncHTTPTransport(retries=3)
        self.http = httpx.AsyncClient(
            transport=transport,
            timeout=10.0,
            limits=httpx.Limits(max_connections=20),
            headers={"User-Agent": "PumpSniper/1.0"},
        )

        # Wallet
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
                logger.info(f"Pump sniper wallet: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Failed to load keypair: {e}")

        # Daily loss tracking
        self.daily_loss = 0.0
        self.daily_loss_limit = 0.03  # SOL
        self.last_loss_reset = time.time()

        # Multi-Node RPC Fallback Rotation System
        self.rpc_endpoints = [
            RPC_HTTP,
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana"
        ]
        self.rpc_index = 0

    async def _rpc_call(self, payload: dict, timeout: float = 5.0) -> Optional[dict]:
        """
        Sends JSON-RPC payload with automatic multi-node fallback rotation
        if rate-limited (HTTP 429) or offline.
        """
        for attempt in range(len(self.rpc_endpoints)):
            url = self.rpc_endpoints[self.rpc_index]
            try:
                resp = await self.http.post(url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    logger.warning(
                        f"{Fore.LIGHTRED_EX}[RPC-RATE-LIMIT]{Style.RESET_ALL} "
                        f"RPC {url[:30]}... rate-limited (HTTP 429). Rotating to next node..."
                    )
                else:
                    logger.warning(
                        f"[RPC-ERROR] Node {url[:30]}... returned HTTP {resp.status_code}."
                    )
            except Exception as e:
                logger.debug(
                    f"[RPC-TIMEOUT/NET] Failed connecting to {url[:30]}...: {e}"
                )
                
            # Rotate
            self.rpc_index = (self.rpc_index + 1) % len(self.rpc_endpoints)
            
        return None

    async def _fetch_sol_price(self):
        """Get current SOL price from Jupiter"""
        try:
            resp = await self.http.get(
                f"https://api.jup.ag/price/v3?ids={SOL_MINT}"
            )
            if resp.status_code == 200:
                data = resp.json()
                price_data = data.get("data", {}).get(SOL_MINT, {})
                self.sol_price_usd = float(price_data.get("price", 0))
        except Exception:
            pass

    def _passes_name_filter(self, name: str, symbol: str) -> bool:
        """Check if token name/symbol passes basic scam filter"""
        name_lower = name.lower().strip()
        symbol_lower = symbol.lower().strip()

        # Too short
        if len(name_lower) < self.min_name_length or len(symbol_lower) < 2:
            return False

        # Known scam patterns
        for pattern in SCAM_PATTERNS:
            if pattern in name_lower or pattern in symbol_lower:
                return False

        # All numbers or special chars
        if name_lower.replace(" ", "").replace("-", "").replace("_", "").isdigit():
            return False

        return True

    def _calculate_bonding_curve_price(
        self,
        virtual_sol_reserves: int,
        virtual_token_reserves: int,
    ) -> float:
        """Calculate current price on bonding curve (SOL per token)"""
        if virtual_token_reserves <= 0:
            return 0.0
        return virtual_sol_reserves / virtual_token_reserves

    def _calculate_buy_output(
        self,
        sol_amount_lamports: int,
        virtual_sol_reserves: int,
        virtual_token_reserves: int,
    ) -> int:
        """Calculate tokens received for a given SOL input on bonding curve"""
        # Constant product: (x + dx) * (y - dy) = x * y
        # dy = y - (x * y) / (x + dx)
        # Fee: 1.25% total
        sol_after_fee = int(sol_amount_lamports * 0.9875)  # 1.25% fee
        k = virtual_sol_reserves * virtual_token_reserves
        new_sol_reserves = virtual_sol_reserves + sol_after_fee
        new_token_reserves = k // new_sol_reserves
        tokens_out = virtual_token_reserves - new_token_reserves
        return max(0, tokens_out)

    async def _check_token_safety(self, mint: str) -> Dict[str, Any]:
        """
        Basic safety checks on a new token.
        Returns dict with 'safe' bool and 'reason' string.
        """
        result = {"safe": True, "reason": "passed", "details": {}}

        try:
            # Check mint account for freeze authority
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getAccountInfo",
                "params": [mint, {"encoding": "jsonParsed"}]
            }
            res = await self._rpc_call(payload, timeout=5.0)
            if not res:
                result["safe"] = False
                result["reason"] = "RPC error checking mint"
                return result

            data = res.get("result", {}).get("value", {})
            if not data:
                result["safe"] = False
                result["reason"] = "Mint account not found"
                return result

            parsed = data.get("data", {}).get("parsed", {}).get("info", {})

            # Check freeze authority (if set, they can freeze your tokens)
            freeze_auth = parsed.get("freezeAuthority")
            if freeze_auth:
                result["safe"] = False
                result["reason"] = f"Freeze authority set: {freeze_auth[:8]}..."
                return result

            result["details"]["decimals"] = parsed.get("decimals", 6)
            result["details"]["supply"] = parsed.get("supply", "0")

        except Exception as e:
            # On timeout/error, still allow (don't miss opportunity)
            result["details"]["safety_check_error"] = str(e)

        return result

    # ─── Phase 1: Safety Layer APIs ──────────────────────────────────────────

    async def _check_rugcheck(self, mint: str) -> dict:
        """
        Query RugCheck.xyz for token risk score (0-100).
        Higher = safer. Threshold: score >= 300 to proceed.
        Fail-open: if API is down or slow, return safe=True.
        """
        try:
            resp = await self.http.get(
                f"https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary",
                timeout=3.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                score = data.get("score", 0)
                risks = data.get("risks", [])
                risk_names = [r.get("name", "") for r in risks] if risks else []

                # RugCheck scores: lower = safer, higher = riskier
                # But their "score" field varies. Check risk level string.
                risk_level = data.get("riskLevel", "unknown").lower()
                is_safe = risk_level in ("good", "low", "unknown")

                return {
                    "safe": is_safe,
                    "score": score,
                    "risk_level": risk_level,
                    "risks": risk_names,
                }
        except Exception as e:
            logger.debug(f"[RUGCHECK] API error (fail-open): {e}")

        # Fail-open: don't block trades on API failure
        return {"safe": True, "score": 0, "risk_level": "unknown", "risks": []}

    async def _check_goplus(self, mint: str) -> dict:
        """
        GoPlus Security API — honeypot, blacklist, mintable detection.
        Free API, Solana-specific endpoint.
        Fail-open on timeout/error.
        """
        try:
            url = (
                f"https://api.gopluslabs.io/api/v1/token_security/solana"
                f"?contract_addresses={mint}"
            )
            resp = await self.http.get(url, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("result", {}).get(mint, {})
                if not token:
                    return {"safe": True}  # No data yet for brand-new token

                is_honeypot = str(token.get("is_honeypot", "0")) == "1"
                is_blacklisted = str(token.get("is_blacklisted", "0")) == "1"
                is_mintable = str(token.get("is_mintable", "0")) == "1"

                safe = not (is_honeypot or is_blacklisted or is_mintable)
                return {
                    "safe": safe,
                    "is_honeypot": is_honeypot,
                    "is_blacklisted": is_blacklisted,
                    "is_mintable": is_mintable,
                }
        except Exception as e:
            logger.debug(f"[GOPLUS] API error (fail-open): {e}")

        return {"safe": True}

    async def _check_dev_history(self, dev_wallet: str) -> dict:
        """
        Check if token creator has launched prior rug-pull tokens.
        Queries Helius for recent pump.fun token creations by this wallet.
        If they've created many tokens recently (serial launcher), flag as risky.
        """
        if not dev_wallet or len(dev_wallet) < 32:
            return {"safe": True, "reason": "no dev wallet", "token_count": 0}

        try:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    dev_wallet,
                    {"limit": 50, "commitment": "confirmed"}
                ]
            }
            res = await self._rpc_call(payload, timeout=3.0)
            if not res:
                return {"safe": True, "reason": "rpc error", "token_count": 0}

            sigs = res.get("result", [])

            # Count pump.fun program interactions (token creations)
            pump_interactions = 0
            for sig_info in sigs:
                memo = sig_info.get("memo", "") or ""
                # Pump.fun token creations show up as interactions with the program
                # A serial launcher creates >5 tokens in a short time
                if sig_info.get("err") is None:
                    pump_interactions += 1

            # Heuristic: if dev has >20 recent transactions, they're a serial launcher
            # Serial launchers are often rug factories
            is_serial = False  # Disabled to prevent false positives (signatures count contains all standard transactions)

            if is_serial:
                return {
                    "safe": False,
                    "reason": f"serial launcher ({pump_interactions} recent txs)",
                    "token_count": pump_interactions,
                }

            return {"safe": True, "reason": "ok", "token_count": pump_interactions}

        except Exception as e:
            logger.debug(f"[DEV-CHECK] Error (fail-open): {e}")

        return {"safe": True, "reason": "check failed", "token_count": 0}

    async def _resolve_token_program(self, mint: str, force_refresh: bool = False) -> 'Pubkey':
        """
        Query the mint account on-chain to determine whether it belongs to
        standard SPL Token (TokenkegQ...) or Token-2022 (TokenzQdBNb...).
        Returns the correct program Pubkey for ATA derivation and instruction accounts.
        Uses in-memory cache + retry with backoff for indexer lag on fresh mints.
        """
        from solders.pubkey import Pubkey
        STD_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        T22_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        TOKEN_PROGRAM_STD = Pubkey.from_string(STD_ID)
        TOKEN_2022_PROGRAM = Pubkey.from_string(T22_ID)

        # Check cache first (skip if forced refresh after on-chain error)
        if not force_refresh and mint in self._token_program_cache:
            cached = self._token_program_cache[mint]
            return TOKEN_2022_PROGRAM if cached == T22_ID else TOKEN_PROGRAM_STD

        # Retry loop with backoff — new mints may not be indexed for 1-5 seconds
        for attempt in range(3):
            try:
                payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getAccountInfo",
                    "params": [mint, {"encoding": "jsonParsed"}]
                }
                resp = await self._rpc_call(payload, timeout=3.0)
                if resp:
                    value = resp.get("result", {}).get("value")
                    if value:
                        owner = value.get("owner", "")
                        self._token_program_cache[mint] = owner
                        if owner == T22_ID:
                            logger.info(f"  [TOKEN-RESOLVE] Mint {mint[:8]}... is Token-2022")
                            return TOKEN_2022_PROGRAM
                        else:
                            logger.debug(f"  [TOKEN-RESOLVE] Mint {mint[:8]}... is standard SPL")
                            return TOKEN_PROGRAM_STD
                    else:
                        # Account not indexed yet — wait and retry
                        if attempt < 2:
                            wait = 1.0 * (attempt + 1)
                            logger.debug(f"  [TOKEN-RESOLVE] Mint {mint[:8]} not indexed yet, retry in {wait}s...")
                            await asyncio.sleep(wait)
            except Exception as e:
                logger.debug(f"  [TOKEN-RESOLVE] Query attempt {attempt+1} failed for {mint[:8]}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)

        # Default to standard SPL — pump.fun's legacy path. Most tokens are standard.
        logger.debug(f"  [TOKEN-RESOLVE] Defaulting {mint[:8]}... to standard SPL after retries.")
        self._token_program_cache[mint] = STD_ID
        return TOKEN_PROGRAM_STD

    def _invalidate_token_program_cache(self, mint: str):
        """Remove a mint from the token program cache (called after IncorrectProgramId)."""
        self._token_program_cache.pop(mint, None)

    async def _build_local_buy_tx(
        self,
        mint: str,
        sol_amount: float,
        slippage_pct: int = 25,
        priority_fee: float = 0.001
    ):
        from solders.pubkey import Pubkey
        from solders.instruction import Instruction, AccountMeta
        from solders.message import MessageV0
        from solders.transaction import VersionedTransaction
        from solders.hash import Hash
        import struct

        try:
            mint_pubkey = Pubkey.from_string(mint)
            wallet_pubkey = self.keypair.pubkey()
            
            # Program IDs — dynamically resolve Token program for Token-2022 support
            PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
            TOKEN_PROGRAM = await self._resolve_token_program(mint)
            ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
            SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
            RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
            COMPUTE_BUDGET_PROGRAM = Pubkey.from_string("ComputeBudget111111111111111111111111111111")

            # Pump Accounts
            global_account = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf")
            fee_recipient = Pubkey.from_string("Crt7PRtVAB61vq9KPdCD4gLf1TvGJS27725pQATh34Xg")
            event_authority = Pubkey.from_string("Ce691wAYNs6121hjGvtzeoVfGLJNG2m3JAX2CeJHX912")

            # PDA derivation for bonding curve
            bonding_curve, _ = Pubkey.find_program_address(
                [b"bonding-curve", bytes(mint_pubkey)],
                PUMP_PROGRAM
            )
            
            def derive_ata_local(wallet: Pubkey, mint: Pubkey, program_id: Pubkey) -> Pubkey:
                seeds = [bytes(wallet), bytes(program_id), bytes(mint)]
                ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM)
                return ata

            associated_bonding_curve = derive_ata_local(bonding_curve, mint_pubkey, TOKEN_PROGRAM)
            associated_token_account = derive_ata_local(wallet_pubkey, mint_pubkey, TOKEN_PROGRAM)

            # Fetch bonding curve state to calculate precise output tokens.
            # Fall back to static initial pump.fun reserves if indexing lag blocks retrieval on Block 0 launches.
            bc_state = await self._get_bonding_curve_state(str(bonding_curve))
            if bc_state:
                vsol = bc_state["virtual_sol_reserves"]
                vtok = bc_state["virtual_token_reserves"]
            else:
                logger.info("  [LOCAL-BUY] RPC indexer lag: using static initial pump.fun reserves (30 SOL / 1.073B tokens).")
                vsol = INITIAL_VIRTUAL_SOL_RESERVES
                vtok = INITIAL_VIRTUAL_TOKEN_RESERVES
            sol_amount_lamports = int(sol_amount * 1e9)

            # Compute output tokens
            tokens_out = self._calculate_buy_output(sol_amount_lamports, vsol, vtok)
            if tokens_out <= 0:
                return None

            # max SOL to spend (input sol + slippage)
            max_sol_lamports = int(sol_amount_lamports * (1 + slippage_pct / 100))

            # instructions list
            ixs = []

            # 1. Set Compute Unit Limit (100k CU is plenty for Pump.fun)
            ixs.append(
                Instruction(
                    COMPUTE_BUDGET_PROGRAM,
                    struct.pack("<BI", 2, 100_000),
                    []
                )
            )

            # 2. Set Compute Unit Price (convert SOL priority fee to micro-lamports)
            # micro_lamports = (priority_fee_sol * 1e9) / 100_000 * 1e6
            micro_lamports = int((priority_fee * 1e9) / 100_000 * 1e6)
            ixs.append(
                Instruction(
                    COMPUTE_BUDGET_PROGRAM,
                    struct.pack("<BQ", 3, micro_lamports),
                    []
                )
            )

            # 3. Create ATA if it doesn't exist (use self._rpc_call for automatic node rotation)
            payload_ata = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getAccountInfo",
                "params": [str(associated_token_account), {"encoding": "base64"}]
            }
            res_ata = await self._rpc_call(payload_ata, timeout=3.0)
            ata_exists = res_ata is not None and res_ata.get("result", {}).get("value") is not None
            
            if not ata_exists:
                logger.info("  [LOCAL-BUY] Appending Associate Token Account creation instruction...")
                ixs.append(
                    Instruction(
                        ASSOCIATED_TOKEN_PROGRAM,
                        b"",
                        [
                            AccountMeta(wallet_pubkey, is_signer=True, is_writable=True),
                            AccountMeta(associated_token_account, is_signer=False, is_writable=True),
                            AccountMeta(wallet_pubkey, is_signer=False, is_writable=False),
                            AccountMeta(mint_pubkey, is_signer=False, is_writable=False),
                            AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                            AccountMeta(TOKEN_PROGRAM, is_signer=False, is_writable=False),
                            AccountMeta(RENT_SYSVAR, is_signer=False, is_writable=False)
                        ]
                    )
                )

            # 4. Pump.fun Buy Instruction
            buy_disc = struct.pack("<Q", 16927863322537952870)
            buy_data = buy_disc + struct.pack("<Q", tokens_out) + struct.pack("<Q", max_sol_lamports)

            ixs.append(
                Instruction(
                    PUMP_PROGRAM,
                    buy_data,
                    [
                        AccountMeta(global_account, is_signer=False, is_writable=False),
                        AccountMeta(fee_recipient, is_signer=False, is_writable=True),
                        AccountMeta(mint_pubkey, is_signer=False, is_writable=False),
                        AccountMeta(bonding_curve, is_signer=False, is_writable=True),
                        AccountMeta(associated_bonding_curve, is_signer=False, is_writable=True),
                        AccountMeta(associated_token_account, is_signer=False, is_writable=True),
                        AccountMeta(wallet_pubkey, is_signer=True, is_writable=True),
                        AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                        AccountMeta(TOKEN_PROGRAM, is_signer=False, is_writable=False),
                        AccountMeta(RENT_SYSVAR, is_signer=False, is_writable=False),
                        AccountMeta(event_authority, is_signer=False, is_writable=False),
                        AccountMeta(PUMP_PROGRAM, is_signer=False, is_writable=False)
                    ]
                )
            )

            # Get fresh blockhash (use self._rpc_call for automatic node rotation)
            payload_bh = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            res_bh = await self._rpc_call(payload_bh, timeout=3.0)
            if not res_bh:
                return None
            bh_str = res_bh.get("result", {}).get("value", {}).get("blockhash")
            if not bh_str:
                return None
                
            recent_blockhash = Hash.from_string(bh_str)

            # Compile into MessageV0
            message = MessageV0.try_compile(
                wallet_pubkey,
                ixs,
                [],
                recent_blockhash
            )
            
            # Create VersionedTransaction
            tx = VersionedTransaction(message, [self.keypair])
            return tx
            
        except Exception as e:
            logger.error(f"[LOCAL-BUY-BUILD] Exception building transaction: {e}")
            return None

    async def _build_local_sell_tx(
        self,
        mint: str,
        token_amount: int,
        slippage_pct: int = 25,
        priority_fee: float = 0.001
    ):
        from solders.pubkey import Pubkey
        from solders.instruction import Instruction, AccountMeta
        from solders.message import MessageV0
        from solders.transaction import VersionedTransaction
        from solders.hash import Hash
        import struct

        try:
            mint_pubkey = Pubkey.from_string(mint)
            wallet_pubkey = self.keypair.pubkey()

            # Program IDs — dynamically resolve Token program for Token-2022 support
            PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
            TOKEN_PROGRAM = await self._resolve_token_program(mint)
            ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
            SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
            COMPUTE_BUDGET_PROGRAM = Pubkey.from_string("ComputeBudget111111111111111111111111111111")

            # Pump Accounts
            global_account = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf")
            fee_recipient = Pubkey.from_string("Crt7PRtVAB61vq9KPdCD4gLf1TvGJS27725pQATh34Xg")
            event_authority = Pubkey.from_string("Ce691wAYNs6121hjGvtzeoVfGLJNG2m3JAX2CeJHX912")

            # PDA derivation for bonding curve
            bonding_curve, _ = Pubkey.find_program_address(
                [b"bonding-curve", bytes(mint_pubkey)],
                PUMP_PROGRAM
            )

            def derive_ata_local(wallet: Pubkey, mint: Pubkey, program_id: Pubkey) -> Pubkey:
                seeds = [bytes(wallet), bytes(program_id), bytes(mint)]
                ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM)
                return ata

            associated_bonding_curve = derive_ata_local(bonding_curve, mint_pubkey, TOKEN_PROGRAM)
            associated_token_account = derive_ata_local(wallet_pubkey, mint_pubkey, TOKEN_PROGRAM)

            # Fetch bonding curve state to calculate minimum SOL out
            bc_state = await self._get_bonding_curve_state(str(bonding_curve))
            if not bc_state:
                logger.warning("[LOCAL-SELL] Failed to fetch bonding curve state. Falling back to PumpPortal API.")
                return None

            vsol = bc_state["virtual_sol_reserves"]
            vtok = bc_state["virtual_token_reserves"]

            try:
                k = vsol * vtok
                new_tok = vtok + token_amount
                new_sol = k // new_tok
                sol_out = vsol - new_sol
                sol_out_after_fee = int(sol_out * 0.9875)  # 1.25% fee
            except ZeroDivisionError:
                return None

            if sol_out_after_fee <= 0:
                return None

            # min SOL to receive (estimate - slippage)
            min_sol_lamports = int(sol_out_after_fee * (1 - slippage_pct / 100))

            # instructions list
            ixs = []

            # 1. Set Compute Limit
            ixs.append(
                Instruction(
                    COMPUTE_BUDGET_PROGRAM,
                    struct.pack("<BI", 2, 100_000),
                    []
                )
            )

            # 2. Set Compute Price
            micro_lamports = int((priority_fee * 1e9) / 100_000 * 1e6)
            ixs.append(
                Instruction(
                    COMPUTE_BUDGET_PROGRAM,
                    struct.pack("<BQ", 3, micro_lamports),
                    []
                )
            )

            # 3. Pump.fun Sell Instruction
            sell_disc = struct.pack("<Q", 12502976611210543446)
            sell_data = sell_disc + struct.pack("<Q", token_amount) + struct.pack("<Q", min_sol_lamports)

            ixs.append(
                Instruction(
                    PUMP_PROGRAM,
                    sell_data,
                    [
                        AccountMeta(global_account, is_signer=False, is_writable=False),
                        AccountMeta(fee_recipient, is_signer=False, is_writable=True),
                        AccountMeta(mint_pubkey, is_signer=False, is_writable=False),
                        AccountMeta(bonding_curve, is_signer=False, is_writable=True),
                        AccountMeta(associated_bonding_curve, is_signer=False, is_writable=True),
                        AccountMeta(associated_token_account, is_signer=False, is_writable=True),
                        AccountMeta(wallet_pubkey, is_signer=True, is_writable=True),
                        AccountMeta(SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                        AccountMeta(ASSOCIATED_TOKEN_PROGRAM, is_signer=False, is_writable=False),
                        AccountMeta(TOKEN_PROGRAM, is_signer=False, is_writable=False),
                        AccountMeta(event_authority, is_signer=False, is_writable=False),
                        AccountMeta(PUMP_PROGRAM, is_signer=False, is_writable=False)
                    ]
                )
            )

            # Get fresh blockhash (use self._rpc_call for automatic node rotation)
            payload_bh = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            res_bh = await self._rpc_call(payload_bh, timeout=3.0)
            if not res_bh:
                return None
            bh_str = res_bh.get("result", {}).get("value", {}).get("blockhash")
            if not bh_str:
                return None

            recent_blockhash = Hash.from_string(bh_str)

            # Compile into MessageV0
            message = MessageV0.try_compile(
                wallet_pubkey,
                ixs,
                [],
                recent_blockhash
            )

            # Create VersionedTransaction
            tx = VersionedTransaction(message, [self.keypair])
            return tx

        except Exception as e:
            logger.error(f"[LOCAL-SELL-BUILD] Exception building transaction: {e}")
            return None

    async def _execute_buy_pumpportal(
        self,
        mint: str,
        sol_amount: float,
        slippage_pct: int = 25,
    ) -> Optional[str]:
        """
        Buy a pump.fun token using pure Python local compilation as priority,
        with automatic fallback to PumpPortal Trade API in case of failure.
        """
        if not self.keypair:
            logger.error("[PUMP-SNIPER] No keypair loaded, cannot execute buy")
            return None

        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction

            # Hardening Fix: Fee-cap lock to protect small balances from congestion slaughter
            priority_fee = float(os.getenv("PRIORITY_FEE", "0.001"))
            max_allowed_fee = float(os.getenv("MAX_PRIORITY_FEE", "0.0015"))
            if priority_fee > max_allowed_fee:
                logger.warning(
                    f"\n{Fore.LIGHTRED_EX}[FEE-GUARD]{Style.RESET_ALL} Snipe aborted! "
                    f"Current priority fee ({priority_fee:.5f} SOL) exceeds your safety cap ({max_allowed_fee:.5f} SOL) to prevent fee bleed.\n"
                )
                return None

            if self.use_pumpportal_api_primary:
                sig = await self._execute_buy_api_path(mint, sol_amount, slippage_pct, priority_fee)
                if sig:
                    return sig
                logger.info("  [PUMP-BUY] Primary API compilation failed or dropped. Falling back to local compilation...")
                return await self._execute_buy_local_path(mint, sol_amount, slippage_pct, priority_fee)
            else:
                sig = await self._execute_buy_local_path(mint, sol_amount, slippage_pct, priority_fee)
                if sig:
                    return sig
                logger.info("  [PUMP-BUY] Primary local compilation failed or dropped. Falling back to PumpPortal API...")
                return await self._execute_buy_api_path(mint, sol_amount, slippage_pct, priority_fee)

        except Exception as e:
            logger.error(f"[PUMP-SNIPER] Buy execution error: {e}")
            return None

    async def _execute_buy_api_path(self, mint: str, sol_amount: float, slippage_pct: int, priority_fee: float) -> Optional[str]:
        try:
            from solders.transaction import VersionedTransaction
            logger.info("  [PUMP-BUY] Invoking PumpPortal HTTP Trade API compilation...")
            payload = {
                "publicKey": str(self.keypair.pubkey()),
                "action": "buy",
                "mint": mint,
                "amount": sol_amount,
                "denominatedInSol": "true",
                "slippage": slippage_pct,
                "priorityFee": priority_fee,
                "pool": "pump",
            }
            resp = await self.http.post(PUMPPORTAL_TRADE_API, json=payload, timeout=10.0)
            if resp.status_code != 200:
                logger.warning(f"[PUMP-SNIPER] PumpPortal API error {resp.status_code}: {resp.text[:200]}")
                return None
            tx_bytes = resp.content
            tx_api = VersionedTransaction.from_bytes(tx_bytes)
            signed_tx = VersionedTransaction(tx_api.message, [self.keypair])
            encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
            }
            result = await self._rpc_call(send_payload, timeout=15.0)
            if result and "result" in result:
                sig = result["result"]
                logger.info(f"  {Fore.LIGHTGREEN_EX}[PUMP-BUY-API]{Style.RESET_ALL} TX submitted: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}. Checking confirmation...")
                confirmed = False
                for attempt in range(15):
                    await asyncio.sleep(1.0)
                    try:
                        status_payload = {
                            "jsonrpc": "2.0", "id": 1,
                            "method": "getSignatureStatuses",
                            "params": [[sig]]
                        }
                        status_resp = await self._rpc_call(status_payload, timeout=3.0)
                        if status_resp:
                            status_data = status_resp.get("result", {}).get("value", [None])[0]
                            if status_data:
                                err = status_data.get("err")
                                if err is None:
                                    confirmations = status_data.get("confirmations")
                                    if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                        logger.info(f"  [PUMP-BUY-API] Transaction confirmed on-chain! Sig: {sig[:16]}...")
                                        confirmed = True
                                        break
                                else:
                                    logger.warning(f"  [PUMP-BUY-API] Transaction failed on-chain: {err}")
                                    return None
                    except Exception as e:
                        logger.debug(f"  [Confirmation Check Error] {e}")
                
                if confirmed:
                    return sig
                else:
                    logger.warning(f"  [PUMP-BUY-API] Transaction not confirmed after 15 attempts / dropped. Sig: {sig[:16]}...")
                    return None
            else:
                error = result.get("error", {})
                logger.warning(f"[PUMP-SNIPER] TX error: {error}")
                return None
        except Exception as e:
            logger.error(f"[PUMP-SNIPER] Buy API execution error: {e}")
            return None

    async def _execute_buy_local_path(self, mint: str, sol_amount: float, slippage_pct: int, priority_fee: float) -> Optional[str]:
        try:
            tx = await self._build_local_buy_tx(
                mint=mint,
                sol_amount=sol_amount,
                slippage_pct=slippage_pct,
                priority_fee=priority_fee
            )
            if tx is None:
                return None
            encoded = base64.b64encode(bytes(tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
            }
            result = await self._rpc_call(send_payload, timeout=15.0)
            if result and "result" in result:
                sig = result["result"]
                logger.info(f"  {Fore.LIGHTGREEN_EX}[PUMP-BUY-LOCAL]{Style.RESET_ALL} TX submitted: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}. Checking confirmation...")
                confirmed = False
                for attempt in range(15):
                    await asyncio.sleep(1.0)
                    try:
                        status_payload = {
                            "jsonrpc": "2.0", "id": 1,
                            "method": "getSignatureStatuses",
                            "params": [[sig]]
                        }
                        status_resp = await self._rpc_call(status_payload, timeout=3.0)
                        if status_resp:
                            status_data = status_resp.get("result", {}).get("value", [None])[0]
                            if status_data:
                                err = status_data.get("err")
                                if err is None:
                                    confirmations = status_data.get("confirmations")
                                    if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                        logger.info(f"  [PUMP-BUY-LOCAL] Transaction confirmed on-chain! Sig: {sig[:16]}...")
                                        confirmed = True
                                        break
                                else:
                                    err_str = str(err)
                                    logger.warning(f"  [PUMP-BUY-LOCAL] Transaction failed on-chain: {err}")
                                    if "IncorrectProgramId" in err_str or ("InstructionError" in err_str and "2" in err_str):
                                        logger.info(f"  [PUMP-BUY-LOCAL] Detected program ID mismatch! Retrying with flipped token program...")
                                        self._invalidate_token_program_cache(mint)
                                        # Retry build
                                        return await self._execute_buy_local_path(mint, sol_amount, slippage_pct, priority_fee)
                                    return None
                    except Exception as e:
                        logger.debug(f"  [Confirmation Check Error] {e}")
                
                if confirmed:
                    return sig
                else:
                    logger.warning(f"  [PUMP-BUY-LOCAL] Transaction not confirmed / dropped: {sig[:16]}")
                    return None
        except Exception as e:
            logger.error(f"[PUMP-SNIPER] Buy local execution error: {e}")
            return None

        return None

    async def _execute_jito_buy(self, mint: str, sol_amount: float) -> Optional[str]:
        """
        Execute a buy using Jito Bundles for Cabal Snipes (Delivery Dominance)
        """
        if not self.keypair or self.dry_run:
            # We don't actually send real Jito bundles on dry run
            return await self.jito_bundle.submit_bundle(["simulated_tx"])
            
        try:
            from solders.transaction import VersionedTransaction
            from solders.system_program import TransferParams, transfer
            from solders.message import MessageV0
            from solders.hash import Hash
            from solders.pubkey import Pubkey
            import random
            from jito_bundle import JITO_TIP_ACCOUNTS
            
            # Calculate dynamic tip (in lamports)
            dynamic_tip_sol = sol_amount * (self.jito_tip_pct / 100.0)
            tip_lamports = int(dynamic_tip_sol * 1e9)
            if tip_lamports < 1000:
                tip_lamports = 1000  # Fallback to minimum tip
                
            # 1. Get raw unsigned buy tx from PumpPortal
            payload = {
                "publicKey": str(self.keypair.pubkey()),
                "action": "buy",
                "mint": mint,
                "amount": sol_amount,
                "denominatedInSol": "true",
                "slippage": 50, # Higher slippage for cabal riding
                "pool": "pump",
            }

            resp = await self.http.post(PUMPPORTAL_TRADE_API, json=payload, timeout=5.0)
            if resp.status_code != 200:
                logger.error(f"[JITO-BUY] PumpPortal API error: HTTP {resp.status_code} — {resp.text}")
                return None
                
            tx_bytes = resp.content
            tx = VersionedTransaction.from_bytes(tx_bytes)
            
            # Sign the PumpPortal buy transaction
            signed_tx = VersionedTransaction(tx.message, [self.keypair])
            encoded_tx = b58encode(bytes(signed_tx))
            
            # 2. Build the Jito Tip Transaction (separate transaction in the bundle)
            # Fetch fresher blockhash using self._rpc_call for automatic node rotation
            bh_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            bh_res = await self._rpc_call(bh_payload, timeout=5.0)
            if not bh_res or "result" not in bh_res:
                logger.error("[JITO-BUY] Failed to fetch blockhash for tip.")
                return None
                
            recent_blockhash_str = bh_res["result"]["value"]["blockhash"]
            recent_blockhash = Hash.from_string(recent_blockhash_str)
            
            # Randomly select a Jito tip account
            tip_account = random.choice(JITO_TIP_ACCOUNTS)
            
            from solders.instruction import Instruction, AccountMeta
            import struct
            
            # System Program transfer discriminator is 2, followed by lamports (u64)
            transfer_data = struct.pack("<IQ", 2, tip_lamports)
            
            ix = Instruction(
                program_id=Pubkey.from_string("11111111111111111111111111111111"),
                data=transfer_data,
                accounts=[
                    AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
                    AccountMeta(Pubkey.from_string(tip_account), is_signer=False, is_writable=True) # Explicit Jito Tip Account write-lock!
                ]
            )
            
            msg = MessageV0.try_compile(
                self.keypair.pubkey(),
                [ix],
                [],
                recent_blockhash
            )
            tip_tx = VersionedTransaction(msg, [self.keypair])
            encoded_tip_tx = b58encode(bytes(tip_tx))
            
            # 3. Submit both via Jito Bundle Engine
            uuid = await self.jito_bundle.submit_bundle([encoded_tx, encoded_tip_tx])
            
            if not uuid:
                logger.warning("[JITO-BUY] Bundle submission returned empty UUID.")
                return None
                
            logger.info(f"{Fore.MAGENTA}[JITO BUNDLE SUCCESS]{Style.RESET_ALL} UUID: {uuid}")
            
            # 4. CRITICAL: Verify the buy TX actually landed on-chain.
            # Jito bundle acceptance != on-chain confirmation. The bundle can be
            # outbid or dropped by the block engine auction.
            buy_sig = str(signed_tx.signatures[0])
            
            confirmed = False
            for check in range(12):  # 12 attempts x 1s = 12s max wait
                await asyncio.sleep(1.0)
                try:
                    st_payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method": "getSignatureStatuses",
                        "params": [[buy_sig]]
                    }
                    st_resp = await self._rpc_call(st_payload, timeout=3.0)
                    if st_resp:
                        sd = st_resp.get("result", {}).get("value", [None])[0]
                        if sd:
                            if sd.get("err") is None:
                                cs = sd.get("confirmationStatus", "")
                                if sd.get("confirmations") is not None or cs in ["confirmed", "finalized"]:
                                    logger.info(f"  [JITO-BUY] Buy TX confirmed on-chain! Sig: {buy_sig[:16]}...")
                                    confirmed = True
                                    break
                            else:
                                logger.warning(f"  [JITO-BUY] Buy TX failed on-chain: {sd.get('err')}")
                                return None
                except Exception:
                    pass
            
            if confirmed:
                return buy_sig  # Return actual on-chain signature, not bundle UUID
            else:
                logger.warning(f"  [JITO-BUY] Bundle accepted but buy TX never landed on-chain (outbid/dropped). UUID: {uuid[:16]}...")
                return None
            
        except Exception as e:
            import traceback
            logger.error(f"[JITO-BUY] Error: {e}")
            logger.error(traceback.format_exc())
            return None

    async def _execute_sell_pumpportal(
        self,
        mint: str,
        token_amount: int,
        slippage_pct: int = 25,
        partial: bool = False,
        priority_fee: Optional[float] = None,
    ) -> Optional[str]:
        """
        Sell pump.fun tokens using pure Python local compilation / PumpPortal API
        compilation based on the configured preference, with automatic fallback.
        """
        if not self.keypair:
            logger.error("[PUMP-SNIPER] No keypair loaded, cannot execute sell")
            return None

        try:
            priority_fee_val = priority_fee if priority_fee is not None else float(os.getenv("PRIORITY_FEE", "0.001"))

            if self.use_pumpportal_api_primary:
                sig = await self._execute_sell_api_path(mint, token_amount, slippage_pct, partial, priority_fee_val)
                if sig:
                    return sig
                logger.info("  [PUMP-SELL] Primary API compilation failed or dropped. Falling back to local compilation...")
                return await self._execute_sell_local_path(mint, token_amount, slippage_pct, priority_fee_val)
            else:
                sig = await self._execute_sell_local_path(mint, token_amount, slippage_pct, priority_fee_val)
                if sig:
                    return sig
                logger.info("  [PUMP-SELL] Primary local compilation failed or dropped. Falling back to PumpPortal API...")
                return await self._execute_sell_api_path(mint, token_amount, slippage_pct, partial, priority_fee_val)

        except Exception as e:
            logger.error(f"[PUMP-SNIPER] Sell execution error: {e}")
            return None

    async def _execute_sell_api_path(
        self,
        mint: str,
        token_amount: int,
        slippage_pct: int,
        partial: bool,
        priority_fee: float,
    ) -> Optional[str]:
        try:
            from solders.transaction import VersionedTransaction
            logger.info("  [PUMP-SELL] Invoking PumpPortal HTTP Trade API compilation...")
            sell_amount = str(token_amount) if partial else "100%"
            payload = {
                "publicKey": str(self.keypair.pubkey()),
                "action": "sell",
                "mint": mint,
                "amount": sell_amount,
                "denominatedInSol": "false",
                "slippage": slippage_pct,
                "priorityFee": priority_fee,
                "pool": "pump",
            }

            resp = await self.http.post(
                PUMPPORTAL_TRADE_API,
                json=payload,
                timeout=10.0,
            )

            if resp.status_code != 200:
                logger.warning(f"[PUMP-SELL-API] PumpPortal API error {resp.status_code}: {resp.text[:200]}")
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

            result = await self._rpc_call(send_payload, timeout=15.0)
            if result and "result" in result:
                sig = result["result"]
                logger.info(f"  {Fore.LIGHTGREEN_EX}[PUMP-SELL-API]{Style.RESET_ALL} TX submitted: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}. Checking confirmation...")
                
                confirmed = False
                for attempt in range(15):
                    await asyncio.sleep(1.0)
                    try:
                        status_payload = {
                            "jsonrpc": "2.0", "id": 1,
                            "method": "getSignatureStatuses",
                            "params": [[sig]]
                        }
                        status_resp = await self._rpc_call(status_payload, timeout=3.0)
                        if status_resp:
                            status_data = status_resp.get("result", {}).get("value", [None])[0]
                            if status_data:
                                err = status_data.get("err")
                                if err is None:
                                    confirmations = status_data.get("confirmations")
                                    if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                        logger.info(f"  [PUMP-SELL-API] Transaction confirmed on-chain! Sig: {sig[:16]}...")
                                        confirmed = True
                                        break
                                else:
                                    logger.warning(f"  [PUMP-SELL-API] Transaction failed on-chain: {err}")
                                    return None
                    except Exception as e:
                        logger.debug(f"  [Confirmation Check Error] {e}")
                
                if confirmed:
                    return sig
                else:
                    logger.warning(f"  [PUMP-SELL-API] Transaction not confirmed after 15 attempts / dropped. Sig: {sig[:16]}...")
                    return None
            else:
                error = result.get("error", {}) if result else "Blank response"
                logger.warning(f"[PUMP-SELL-API] RPC error / response blank: {error}")
                return None
        except Exception as e:
            logger.error(f"[PUMP-SELL-API] Sell API execution error: {e}")
            return None

    async def _execute_sell_local_path(
        self,
        mint: str,
        token_amount: int,
        slippage_pct: int,
        priority_fee: float,
    ) -> Optional[str]:
        try:
            tx = None
            if isinstance(token_amount, int) and token_amount > 0:
                try:
                    logger.info(f"  [LOCAL-SELL] Building transaction locally for {mint[:8]}...")
                    tx = await self._build_local_sell_tx(
                        mint=mint,
                        token_amount=token_amount,
                        slippage_pct=slippage_pct,
                        priority_fee=priority_fee
                    )
                except Exception as ex:
                    logger.warning(f"  [LOCAL-SELL] Local building failed: {ex}.")
                    return None

            if tx is None:
                return None

            encoded = base64.b64encode(bytes(tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [
                    encoded,
                    {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
                ]
            }
            result = await self._rpc_call(send_payload, timeout=15.0)
            if result and "result" in result:
                sig = result["result"]
                logger.info(f"  {Fore.LIGHTGREEN_EX}[PUMP-SELL-LOCAL]{Style.RESET_ALL} TX submitted: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}. Checking confirmation...")
                
                confirmed = False
                for attempt in range(15):
                    await asyncio.sleep(1.0)
                    try:
                        status_payload = {
                            "jsonrpc": "2.0", "id": 1,
                            "method": "getSignatureStatuses",
                            "params": [[sig]]
                        }
                        status_resp = await self._rpc_call(status_payload, timeout=3.0)
                        if status_resp:
                            status_data = status_resp.get("result", {}).get("value", [None])[0]
                            if status_data:
                                err = status_data.get("err")
                                if err is None:
                                    confirmations = status_data.get("confirmations")
                                    if confirmations is not None or status_data.get("confirmationStatus") in ["confirmed", "finalized"]:
                                        logger.info(f"  [PUMP-SELL-LOCAL] Transaction confirmed on-chain! Sig: {sig[:16]}...")
                                        confirmed = True
                                        break
                                else:
                                    err_str = str(err)
                                    logger.warning(f"  [PUMP-SELL-LOCAL] Transaction failed on-chain: {err}")
                                    if "IncorrectProgramId" in err_str or ("InstructionError" in err_str and "2" in err_str):
                                        logger.info(f"  [PUMP-SELL-LOCAL] Detected program ID mismatch! Retrying with flipped token program...")
                                        self._invalidate_token_program_cache(mint)
                                        # Retry build
                                        return await self._execute_sell_local_path(mint, token_amount, slippage_pct, priority_fee)
                                    return None
                    except Exception as e:
                        logger.debug(f"  [Confirmation Check Error] {e}")
                
                if confirmed:
                    return sig
                else:
                    logger.warning(f"  [PUMP-SELL-LOCAL] Transaction not confirmed after 15 attempts / dropped. Sig: {sig[:16]}...")
                    return None
            else:
                error = result.get("error", {}) if result else "Blank response"
                logger.warning(f"[PUMP-SELL-LOCAL] RPC error / response blank: {error}")
                return None
        except Exception as e:
            logger.error(f"[PUMP-SELL-LOCAL] Sell local execution error: {e}")
            return None

    async def _get_bonding_curve_state(self, bonding_curve_address: str) -> Optional[Dict]:
        """Fetch bonding curve account to get current reserves"""
        try:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getAccountInfo",
                "params": [bonding_curve_address, {"encoding": "base64"}]
            }
            res = await self._rpc_call(payload, timeout=5.0)
            if not res:
                return None

            data = res.get("result", {}).get("value", {})
            if not data:
                return None

            account_data = base64.b64decode(data["data"][0])

            # Bonding curve layout (after 8-byte discriminator):
            # u64 virtual_token_reserves  (offset 8)
            # u64 virtual_sol_reserves    (offset 16)
            # u64 real_token_reserves     (offset 24)
            # u64 real_sol_reserves       (offset 32)
            # u64 token_total_supply      (offset 40)
            # bool complete               (offset 48)
            if len(account_data) < 49:
                return None

            virtual_token = struct.unpack_from("<Q", account_data, 8)[0]
            virtual_sol = struct.unpack_from("<Q", account_data, 16)[0]
            real_token = struct.unpack_from("<Q", account_data, 24)[0]
            real_sol = struct.unpack_from("<Q", account_data, 32)[0]
            total_supply = struct.unpack_from("<Q", account_data, 40)[0]
            complete = account_data[48] != 0

            price = virtual_sol / virtual_token if virtual_token > 0 else 0
            fill_pct = (real_sol / GRADUATION_SOL_THRESHOLD) * 100 if GRADUATION_SOL_THRESHOLD > 0 else 0
            mcap_sol = price * total_supply / 1e6  # tokens are 6 decimals

            return {
                "virtual_token_reserves": virtual_token,
                "virtual_sol_reserves": virtual_sol,
                "real_token_reserves": real_token,
                "real_sol_reserves": real_sol,
                "total_supply": total_supply,
                "complete": complete,
                "price_sol": price,
                "fill_pct": fill_pct,
                "mcap_sol": mcap_sol / 1e9,  # convert lamports to SOL
            }

        except Exception as e:
            logger.debug(f"[PUMP-SNIPER] Bonding curve fetch error: {e}")
            return None

    async def _handle_new_token(self, data: Dict[str, Any]):
        """Process a new token creation event from PumpPortal"""
        self.tokens_seen += 1

        mint = data.get("mint", "")
        # Sanitize to ASCII to prevent CP1252 terminal encoding crashes on foreign characters/emojis
        name = data.get("name", "").encode("ascii", errors="replace").decode("ascii")
        symbol = data.get("symbol", "").encode("ascii", errors="replace").decode("ascii")
        bonding_curve = data.get("bondingCurveKey", "")
        uri = data.get("uri", "")
        creator = data.get("traderPublicKey", "")

        if not mint or not name:
            return

        # Strict single-trade circuit breaker for live verification
        if not self.dry_run and (self.total_snipes >= 1 or self.total_sells >= 1):
            return

        # [OFFENSIVE MODULE: CABAL TRACKER]
        # Simulate payload mutation to test bypass logic in dry run
        if self.dry_run:
            data = self.insider_tracker.simulate_insider_launch(data)
        buyer_wallet = data.get("traderPublicKey", creator)
        is_shadow_copy = self.insider_tracker.is_insider(buyer_wallet)

        # Quick logging
        logger.info(
            f"{Fore.LIGHTYELLOW_EX}[NEW-TOKEN]{Style.RESET_ALL} "
            f"{Fore.WHITE}{name}{Style.RESET_ALL} ({symbol}) | "
            f"Mint: {Fore.CYAN}{mint[:12]}...{Style.RESET_ALL} | "
            f"Creator: {creator[:8]}..."
        )

        # ─── Filter Chain ───────────────────────────────────────────────
        # 1. Name/symbol filter
        if not self._passes_name_filter(name, symbol):
            self.tokens_filtered += 1
            logger.debug(f"  -> Filtered: bad name/symbol pattern")
            return

        # 2. Max concurrent positions
        active_positions = sum(1 for p in self.positions.values() if p.status == "active")
        if active_positions >= self.max_concurrent:
            logger.debug(f"  -> Skipped: max concurrent positions ({active_positions}/{self.max_concurrent})")
            return

        # 3. Daily loss limit
        if self.daily_loss >= self.daily_loss_limit:
            logger.debug(f"  -> Skipped: daily loss limit reached ({self.daily_loss:.4f} SOL)")
            return

        # 4. Already holding this token
        if mint in self.positions:
            logger.debug(f"  -> Skipped: already holding {symbol}")
            return

        # 5. Safety APIs — RugCheck + GoPlus + Dev History (concurrent, fail-open)
        actual_snipe_sol = self.max_snipe_sol

        if is_shadow_copy:
            logger.info(
                f"  {Fore.MAGENTA}{Style.BRIGHT}[CABAL DETECTED]{Style.RESET_ALL} "
                f"Alpha wallet {buyer_wallet[:8]} bought Block 0. PERFORMING ALL AUDITS..."
            )
            # Double the snipe size for cabal riding
            actual_snipe_sol *= 2.0
        else:
            if self.strict_cabal_mode:
                logger.debug(f"  -> Skipped: Strict Cabal Mode enabled. No alpha wallet detected.")
                return
                
        if is_shadow_copy:
            dev_result = {"safe": True, "reason": "shadow copy bypass", "token_count": 0}
            rugcheck_result, goplus_result = await asyncio.gather(
                self._check_rugcheck(mint),
                self._check_goplus(mint),
                return_exceptions=True,
            )
        else:
            rugcheck_result, goplus_result, dev_result = await asyncio.gather(
                self._check_rugcheck(mint),
                self._check_goplus(mint),
                self._check_dev_history(creator),
                return_exceptions=True,
            )

        # Handle exceptions from gather
        if isinstance(rugcheck_result, Exception):
            rugcheck_result = {"safe": True, "risk_level": "unknown"}
        if isinstance(goplus_result, Exception):
            goplus_result = {"safe": True}
        if not is_shadow_copy and isinstance(dev_result, Exception):
            dev_result = {"safe": True, "reason": "error"}

        # RugCheck: reject high-risk tokens
        if not rugcheck_result.get("safe", True):
            self.tokens_filtered += 1
            risk_level = rugcheck_result.get("risk_level", "?")
            risks = rugcheck_result.get("risks", [])
            logger.info(
                f"  {Fore.RED}[X] RUGCHECK FAILED{Style.RESET_ALL} "
                f"Risk: {risk_level} | Flags: {', '.join(risks[:3])}"
            )
            return

        # GoPlus: reject honeypots, blacklisted, mintable tokens
        if not goplus_result.get("safe", True):
            self.tokens_filtered += 1
            flags = []
            if goplus_result.get("is_honeypot"): flags.append("HONEYPOT")
            if goplus_result.get("is_blacklisted"): flags.append("BLACKLISTED")
            if goplus_result.get("is_mintable"): flags.append("MINTABLE")
            logger.info(
                f"  {Fore.RED}[X] GOPLUS FAILED{Style.RESET_ALL} "
                f"Flags: {', '.join(flags)}"
            )
            return

        # Dev history: reject serial launchers (rug factories)
        if not dev_result.get("safe", True):
            self.tokens_filtered += 1
            logger.info(
                f"  {Fore.RED}[X] DEV CHECK FAILED{Style.RESET_ALL} "
                f"{dev_result.get('reason', 'unknown')}"
            )
            return

        logger.debug(
            f"  -> Safety: RugCheck={rugcheck_result.get('risk_level','?')} "
            f"GoPlus={'safe' if goplus_result.get('safe') else 'FAIL'} "
            f"Dev={dev_result.get('reason','?')}"
        )

        # 5.5. Quantitative ML & Heuristic Launch Scoring
        logger.info(f"  [QUANT-AUDIT] Evaluating {symbol} via ML RandomForest & Heuristics...")
        try:
            pred = self.predictor.predict_launch(mint)
            h_score = pred["heuristic_score"]
            ml_prob = pred["ml_probability"]
            
            # Circuit breaker: reject tokens with extremely low scores or high cabal rug characteristics
            if h_score < 40.0:
                logger.info(
                    f"  {Fore.RED}[X] QUANT HEURISTIC FILTER FAILED{Style.RESET_ALL} "
                    f"Score: {h_score:.1f}/100 < 40.0 (High Rug risk, skipping)"
                )
                self.tokens_filtered += 1
                return
                
            # ML probability filter — disabled during cold-start (no graduated tokens in DB yet).
            # The heuristic filter at 40.0 + GoPlus/RugCheck/DevCheck still protect against rugs.
            # Re-enable once we have real graduated token data for proper ML training.
            # if ml_prob < 0.35:
            #     logger.info(
            #         f"  {Fore.RED}[X] QUANT ML CLASSIFIER FAILED{Style.RESET_ALL} "
            #         f"ML Prob: {ml_prob*100:.1f}% < 35.0% (Suboptimal regime, skipping)"
            #     )
            #     self.tokens_filtered += 1
            #     return
                
            logger.info(
                f"  {Fore.GREEN}[PASS] QUANT AUDIT PASSED{Style.RESET_ALL} | "
                f"Heuristic: {h_score:.1f}/100 | ML Prob: {ml_prob*100:.1f}%"
            )
        except Exception as e:
            logger.debug(f"[QUANT-AUDIT] Engine bypass (fail-open): {e}")

        # 6. Check SOL balance (only in live mode)
        if self.keypair and not self.dry_run:
            try:
                bal_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getBalance",
                    "params": [str(self.keypair.pubkey())]
                }
                bal_resp = await self.http.post(RPC_HTTP, json=bal_payload, timeout=5.0)
                if bal_resp.status_code == 200:
                    sol_balance = bal_resp.json().get("result", {}).get("value", 0) / 1e9
                    if sol_balance < actual_snipe_sol + 0.002:  # Reserve for fees
                        logger.info(f"  -> Skipped: insufficient SOL ({sol_balance:.4f})")
                        return
            except Exception:
                pass

        # ─── PASSED ALL FILTERS — EXECUTE ─────────────────────────────
        self.tokens_bought += 1

        if self.dry_run:
            # Fetch bonding curve state to get real starting price and reserves for high-fidelity simulation
            bc_state = await self._get_bonding_curve_state(bonding_curve)
            
            # Fallback to standard initial bonding curve reserves if RPC indexer lag returns None
            vsol = bc_state["virtual_sol_reserves"] if bc_state else INITIAL_VIRTUAL_SOL_RESERVES
            vtok = bc_state["virtual_token_reserves"] if bc_state else INITIAL_VIRTUAL_TOKEN_RESERVES
            entry_price = bc_state["price_sol"] if bc_state else (vsol / vtok)
            entry_vsol = bc_state.get("virtual_sol_reserves", 0) if bc_state else vsol

            # Estimate tokens received
            tokens = self._calculate_buy_output(
                int(actual_snipe_sol * 1e9),
                vsol,
                vtok,
            )

            if is_shadow_copy:
                logger.info(
                    f"  {Fore.LIGHTGREEN_EX}[OK] WOULD JITO-BUNDLE CABAL SNIPE{Style.RESET_ALL} "
                    f"{name} ({symbol}) — {actual_snipe_sol} SOL [DRY RUN]"
                )
            else:
                logger.info(
                    f"  {Fore.LIGHTGREEN_EX}[OK] WOULD SNIPE{Style.RESET_ALL} "
                    f"{name} ({symbol}) — {actual_snipe_sol} SOL [DRY RUN]"
                )
                
            # Track as simulated position
            pos = SniperPosition(
                token_mint=mint,
                token_name=name,
                token_symbol=symbol,
                bonding_curve=bonding_curve,
                entry_sol=actual_snipe_sol,
                entry_time=time.time(),
                entry_price=entry_price,
                token_amount=tokens,
                peak_price=entry_price,
                buy_tx="dry_run",
                status="active",
                dev_wallet=creator,
                entry_virtual_sol=entry_vsol,
            )
            try:
                paper_id = self.paper_engine.execute_paper_buy(mint, actual_snipe_sol, entry_price)
                pos.paper_id = paper_id
            except Exception as e:
                logger.debug(f"Paper buy logging failed: {e}")

            self.positions[mint] = pos
            asyncio.create_task(self._monitor_single_position(mint))

            # [OFFENSIVE MODULE: DEV TRIPWIRE]
            # When we buy, we arm the tripwire on the dev's account.
            # If they transfer tokens or dump, we emergency sell.
            async def on_tripwire_snapped(dump_mint: str):
                logger.info(f"{Fore.RED}{Style.BRIGHT}[TRIPWIRE EXECUTOR]{Style.RESET_ALL} Auto-dumping {dump_mint} due to Dev Wallet Activity!")
                await self._close_position(dump_mint, "dev_tripwire", entry_price)
                
            # For simplicity, we track the creator wallet directly. In a full implementation,
            # we'd derive the creator's ATA for this specific mint.
            self.tripwire.set_tripwire(creator, mint, on_tripwire_snapped)
            return

        if is_shadow_copy:
            logger.info(
                f"  {Fore.MAGENTA}{Style.BRIGHT}⚡ JITO BUNDLE SNIPING{Style.RESET_ALL} "
                f"{name} ({symbol}) — {actual_snipe_sol} SOL"
            )
            sig = await self._execute_jito_buy(mint, actual_snipe_sol)
            if not sig:
                logger.info(
                    f"  {Fore.YELLOW}{Style.BRIGHT}[JITO FALLBACK]{Style.RESET_ALL} "
                    f"Jito bundle buy returned None. Retrying via standard PumpPortal local/API route..."
                )
                sig = await self._execute_buy_pumpportal(mint, actual_snipe_sol, slippage_pct=50)
        else:
            logger.info(
                f"  {Fore.LIGHTGREEN_EX}{Style.BRIGHT}⚡ SNIPING{Style.RESET_ALL} "
                f"{name} ({symbol}) — {actual_snipe_sol} SOL"
            )
            sig = await self._execute_buy_pumpportal(mint, actual_snipe_sol)
            
        if sig:
            self.total_snipes += 1

            # Get bonding curve state for entry price
            bc_state = await self._get_bonding_curve_state(bonding_curve)
            
            # Fallback to standard initial bonding curve reserves if RPC indexer lag returns None
            vsol = bc_state["virtual_sol_reserves"] if bc_state else INITIAL_VIRTUAL_SOL_RESERVES
            vtok = bc_state["virtual_token_reserves"] if bc_state else INITIAL_VIRTUAL_TOKEN_RESERVES
            entry_price = bc_state["price_sol"] if bc_state else (vsol / vtok)
            entry_vsol = bc_state.get("virtual_sol_reserves", 0) if bc_state else vsol

            # Estimate tokens received
            tokens = self._calculate_buy_output(
                int(actual_snipe_sol * 1e9),
                vsol,
                vtok,
            )

            self.positions[mint] = SniperPosition(
                token_mint=mint,
                token_name=name,
                token_symbol=symbol,
                bonding_curve=bonding_curve,
                entry_sol=actual_snipe_sol,
                entry_time=time.time(),
                entry_price=entry_price,
                token_amount=tokens,
                peak_price=entry_price,
                buy_tx=sig,
                status="active",
                dev_wallet=creator,
                entry_virtual_sol=entry_vsol,
            )
            asyncio.create_task(self._monitor_single_position(mint))

            logger.info(
                f"  {Fore.GREEN}[OK] Position opened{Style.RESET_ALL} | "
                f"Tokens: ~{tokens / 1e6:.2f} | "
                f"TX: {sig[:16]}..."
            )
            
            # Arm Tripwire
            async def on_tripwire_snapped(dump_mint: str):
                logger.info(f"{Fore.RED}{Style.BRIGHT}[TRIPWIRE EXECUTOR]{Style.RESET_ALL} Auto-dumping {dump_mint} due to Dev Wallet Activity!")
                current_price = 0.0
                if dump_mint in self.positions:
                    bc_state = await self._get_bonding_curve_state(self.positions[dump_mint].bonding_curve)
                    current_price = bc_state["price_sol"] if bc_state else self.positions[dump_mint].entry_price
                await self._close_position(dump_mint, "dev_tripwire", current_price)
                
            self.tripwire.set_tripwire(creator, mint, on_tripwire_snapped)
            
        else:
            logger.warning(f"  → Buy failed for {symbol}")

    async def _monitor_single_position(self, mint: str):
        """Micro-monitor task spawned concurrently per position for sub-second reactive exits"""
        pos = self.positions.get(mint)
        if not pos:
            return

        logger.info(
            f"{Fore.LIGHTCYAN_EX}[PUMP-MICRO-MONITOR]{Style.RESET_ALL} "
            f"Started dedicated task for {pos.token_symbol} ({mint[:8]}...)"
        )

        while self.running and pos.status == "active":
            try:
                elapsed = time.time() - pos.entry_time

                # Timeout exit
                if elapsed >= self.timeout_secs:
                    logger.info(
                        f"{Fore.YELLOW}[TIMEOUT]{Style.RESET_ALL} "
                        f"{pos.token_symbol} — held {elapsed:.0f}s, selling..."
                    )
                    current_price = 0.0
                    if pos.bonding_curve:
                        bc_state = await self._get_bonding_curve_state(pos.bonding_curve)
                        current_price = bc_state["price_sol"] if bc_state else pos.entry_price
                    await self._close_position(mint, "timeout", current_price)
                    break

                # Check current price via bonding curve
                if pos.bonding_curve:
                    bc_state = await self._get_bonding_curve_state(pos.bonding_curve)
                    if bc_state:
                        current_price = bc_state["price_sol"]

                        # --- Sell Pressure Detection -----------
                        if pos.entry_virtual_sol > 0:
                            current_vsol = bc_state.get("virtual_sol_reserves", 0)
                            vsol_change_pct = ((current_vsol - pos.entry_virtual_sol) / pos.entry_virtual_sol) * 100
                            if vsol_change_pct < -25.0:
                                logger.info(
                                    f"{Fore.RED}[SELL PRESSURE]{Style.RESET_ALL} "
                                    f"{pos.token_symbol} - SOL reserves dropped {vsol_change_pct:.1f}% -> emergency exit"
                                )
                                await self._close_position(mint, "sell_pressure", current_price)
                                break

                        # Update peak
                        if current_price > pos.peak_price:
                            pos.peak_price = current_price

                        # Calculate P&L
                        if pos.entry_price > 0:
                            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100

                            # Dynamic Break-Even & Profit Lock Stops (Institutional Safeguards)
                            if pnl_pct >= 30.0 and not pos.profit_lock_30:
                                pos.profit_lock_30 = True
                                logger.info(f"{Fore.LIGHTGREEN_EX}[PROFIT LOCK]{Style.RESET_ALL} {pos.token_symbol} reached +30.0%! Lock trailing stop-loss at +15.0% profit.")
                            elif pnl_pct >= 15.0 and not pos.break_even_locked:
                                pos.break_even_locked = True
                                logger.info(f"{Fore.LIGHTGREEN_EX}[BREAK-EVEN]{Style.RESET_ALL} {pos.token_symbol} reached +15.0%! Lock stop-loss at +5.0% break-even.")

                            # Exit triggers based on dynamic locks
                            if pos.profit_lock_30 and pnl_pct <= 15.0:
                                logger.info(f"{Fore.YELLOW}[DYNAMIC SL]{Style.RESET_ALL} {pos.token_symbol} hit locked +15.0% profit stop (P&L: {pnl_pct:.1f}%)")
                                await self._close_position(mint, "profit_lock_30", current_price)
                                break
                            elif pos.break_even_locked and not pos.profit_lock_30 and pnl_pct <= 5.0:
                                logger.info(f"{Fore.YELLOW}[BREAK-EVEN SL]{Style.RESET_ALL} {pos.token_symbol} hit locked +5.0% break-even stop (P&L: {pnl_pct:.1f}%)")
                                await self._close_position(mint, "break_even", current_price)
                                break
                            
                            # ─── Tiered Take-Profit ──────────────────
                            # Tier 1: +50% -> sell 40% of position
                            if pnl_pct >= 50.0 and not pos.sell_tier_1:
                                pos.sell_tier_1 = True
                                logger.info(
                                    f"{Fore.LIGHTGREEN_EX}[TIER-1 TP]{Style.RESET_ALL} "
                                    f"{pos.token_symbol} +{pnl_pct:.1f}% -> selling 40%"
                                )
                                await self._partial_sell(mint, 40, current_price)

                            # Tier 2: +100% -> sell 30% of remaining
                            if pnl_pct >= 100.0 and not pos.sell_tier_2:
                                pos.sell_tier_2 = True
                                logger.info(
                                    f"{Fore.LIGHTGREEN_EX}[TIER-2 TP]{Style.RESET_ALL} "
                                    f"{pos.token_symbol} +{pnl_pct:.1f}% -> selling 30% more"
                                )
                                await self._partial_sell(mint, 50, current_price)  # 50% of remaining ≈ 30% of original

                            # Final take profit (full exit)
                            if pnl_pct >= self.take_profit_pct:
                                logger.info(
                                    f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}[FULL TP]{Style.RESET_ALL} "
                                    f"{pos.token_symbol} +{pnl_pct:.1f}% -> selling remaining"
                                )
                                await self._close_position(mint, "take_profit", current_price)
                                break

                            # Trailing stop from peak
                            if pos.peak_price > pos.entry_price:
                                drawdown_from_peak = ((pos.peak_price - current_price) / pos.peak_price) * 100
                                if drawdown_from_peak >= self.stop_loss_pct:
                                    logger.info(
                                        f"{Fore.RED}[STOP LOSS]{Style.RESET_ALL} "
                                        f"{pos.token_symbol} — {drawdown_from_peak:.1f}% from peak"
                                    )
                                    await self._close_position(mint, "stop_loss", current_price)
                                    break

                            # Hard stop loss from entry
                            if pnl_pct <= -self.stop_loss_pct:
                                logger.info(
                                    f"{Fore.RED}[HARD STOP]{Style.RESET_ALL} "
                                    f"{pos.token_symbol} — {pnl_pct:.1f}% from entry"
                                )
                                await self._close_position(mint, "hard_stop", current_price)
                                break

                        # Graduation detection
                        if bc_state.get("complete"):
                            logger.info(
                                f"{Fore.LIGHTMAGENTA_EX}[GRADUATED]{Style.RESET_ALL} "
                                f"{pos.token_symbol} graduated to PumpSwap!"
                            )
                            await asyncio.sleep(2)
                            await self._close_position(mint, "graduation", current_price)
                            break

            except Exception as e:
                logger.error(f"[PUMP-MICRO-MONITOR] Error: {e}")

            await asyncio.sleep(0.2)  # Tight 200ms polling for microsecond reaction

    async def _partial_sell(self, mint: str, percent: int, current_price: float):
        """
        Sell a percentage of held tokens (for tiered take-profit).
        percent: 1-99 (e.g. 40 = sell 40% of current balance).
        Does NOT close the position — leaves remaining tokens active.
        """
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        if self.dry_run:
            sell_amount = int(pos.token_amount * percent / 100)
            proceeds = (sell_amount * current_price) / 1e9
            pos.total_sol_returned += proceeds
            pos.token_amount -= sell_amount
            logger.info(
                f"  {Fore.YELLOW}[DRY-PARTIAL]{Style.RESET_ALL} "
                f"Would sell {percent}% of {pos.token_symbol} | "
                f"Proceeds: {proceeds:.5f} SOL"
            )
            return

        try:
            # Query actual token balance via unified, robust call (handles standard & Token-2022)
            raw_amount, active_program = await self._query_actual_balance_on_chain(mint)
            if raw_amount <= 0:
                return

            # Calculate partial amount
            sell_amount = int(raw_amount * percent / 100)
            if sell_amount <= 0:
                return

            # Execute partial sell via PumpPortal (specific amount, not "100%")
            sig = await self._execute_sell_pumpportal(mint, sell_amount, partial=True)
            if sig:
                proceeds = (sell_amount * current_price) / 1e9
                pos.total_sol_returned += proceeds
                logger.info(
                    f"{Fore.LIGHTCYAN_EX}[PARTIAL-SOLD]{Style.RESET_ALL} "
                    f"{pos.token_symbol} — {percent}% sold | Proceeds: {proceeds:.5f} SOL | TX: {sig[:16]}..."
                )
            else:
                logger.warning(f"[PARTIAL-SELL] Failed for {pos.token_symbol}")

        except Exception as e:
            logger.error(f"[PARTIAL-SELL] Error: {e}")

    async def _query_actual_balance_on_chain(self, mint: str) -> tuple[int, Any]:
        """Directly query the on-chain balance of a mint, returning (raw_amount, active_program)"""
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
                    return raw_bal, token2022_program
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
                    return raw_bal, token_program
        except Exception:
            pass

        # 3. Dynamic resolution fallback if balance is 0 or query failed
        resolved_program = token_program
        try:
            resolved_program = await self._resolve_token_program(mint)
        except Exception:
            pass

        return 0, resolved_program

    async def _close_position(self, mint: str, reason: str, current_price: float):
        """Close a position by selling all tokens with exit-assurance retry loops"""
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        if self.dry_run:
            pos.status = reason
            proceeds = (pos.token_amount * current_price) / 1e9
            pos.total_sol_returned += proceeds
            trade_pnl = pos.total_sol_returned - pos.entry_sol
            self.total_profit_sol += trade_pnl
            pos.token_amount = 0

            pnl_color = Fore.LIGHTGREEN_EX if trade_pnl >= 0 else Fore.LIGHTRED_EX
            pnl_symbol = "[+]" if trade_pnl >= 0 else "[-]"
            
            reason_str = f"{Fore.RED}{Style.BRIGHT}{reason.upper()}{Style.RESET_ALL}" if reason == "dev_tripwire" else reason
            
            logger.info(
                f"  {Fore.YELLOW}[DRY-SELL]{Style.RESET_ALL} "
                f"Would sell {pos.token_symbol} — reason: {reason_str} | "
                f"Proceeds: {proceeds:.5f} SOL | "
                f"Net P&L: {pnl_color}{pnl_symbol} {trade_pnl:+.5f} SOL{Style.RESET_ALL}"
            )
            
            if hasattr(pos, "paper_id") and pos.paper_id:
                try:
                    self.paper_engine.execute_paper_sell(pos.paper_id, current_price)
                except Exception as e:
                    logger.debug(f"Paper sell logging failed: {e}")

            # Clean up tripwire if we sell for any reason
            self.tripwire.disarm(pos.dev_wallet)
            return

        # Direct on-chain balance query
        actual_amount, active_program = await self._query_actual_balance_on_chain(mint)

        # Fallback to tracked memory balance if direct queries failed due to indexer lag
        if actual_amount <= 0 and pos.token_amount > 0:
            actual_amount = int(pos.token_amount)
            logger.info(f"  [FALLBACK] Indexer lag detected. Using tracked memory balance: {actual_amount} raw tokens")

        if actual_amount <= 0:
            logger.info(
                f"  {Fore.YELLOW}[NO-BALANCE]{Style.RESET_ALL} "
                f"No tokens of {pos.token_symbol} found in wallet — marking as {reason}"
            )
            pos.status = reason
            return

        # Determine dynamic slippage and base priority fee
        is_emergency = reason in ["dev_tripwire", "sell_pressure", "hard_stop", "stop_loss", "profit_lock_30", "break_even"]
        sell_slippage = int(self.tripwire_slippage_pct) if is_emergency else 25
        base_priority_fee = float(os.getenv("PRIORITY_FEE", "0.001"))

        sig = None
        max_retries = 5

        for attempt in range(max_retries):
            # Scale priority fee on failed retries up to a safety cap of 0.005 SOL
            escalated_fee = min(base_priority_fee * (2 ** attempt), 0.005)
            if attempt > 0:
                logger.info(
                    f"  {Fore.YELLOW}[PANIC-EXIT-RETRY]{Style.RESET_ALL} Attempt {attempt+1}/{max_retries} for {pos.token_symbol} | "
                    f"Escalating Priority Fee to {escalated_fee:.5f} SOL | Slippage: 100%"
                )
                sell_slippage = 100 # Force validator inclusion with max slippage on retry

            sig = await self._execute_sell_pumpportal(
                mint, 
                actual_amount, 
                slippage_pct=sell_slippage,
                priority_fee=escalated_fee
            )
            if sig:
                break

            await asyncio.sleep(1.0)
            
            # Re-fetch balance on failure in case of partial executions
            actual_amount, active_program = await self._query_actual_balance_on_chain(mint)
            if actual_amount <= 0:
                logger.info(f"  [Direct Query] Balance dropped to 0 during retries. Exiting retry loop.")
                sig = "confirmed_during_retry"
                break

        if sig:
            pos.status = reason
            self.total_sells += 1
            proceeds = (actual_amount * current_price) / 1e9
            pos.total_sol_returned += proceeds
            trade_pnl = pos.total_sol_returned - pos.entry_sol
            self.total_profit_sol += trade_pnl

            pnl_color = Fore.LIGHTGREEN_EX if trade_pnl >= 0 else Fore.LIGHTRED_EX
            pnl_symbol = "[+]" if trade_pnl >= 0 else "[-]"
            logger.info(
                f"{Fore.LIGHTCYAN_EX}[SOLD]{Style.RESET_ALL} "
                f"{pos.token_symbol} — reason: {reason} | "
                f"Proceeds: {proceeds:.5f} SOL | "
                f"Net P&L: {pnl_color}{pnl_symbol} {trade_pnl:+.5f} SOL{Style.RESET_ALL} | "
                f"TX: {sig[:16]}..."
            )
            # Reclaim ATA rent directly in background
            asyncio.create_task(self._close_token_account_directly(mint, active_program))
            # Clean up tripwire
            self.tripwire.disarm(pos.dev_wallet)

            # Strict single-trade termination breaker for live safety verification
            if not self.dry_run and self.total_sells >= 1:
                logger.info("")
                logger.info(f"{Fore.RED}{Style.BRIGHT}=================================================={Style.RESET_ALL}")
                logger.info(f"{Fore.RED}{Style.BRIGHT}   [CIRCUIT BREAKER] SINGLE LIVE TRADE CLOSED!      {Style.RESET_ALL}")
                logger.info(f"{Fore.RED}{Style.BRIGHT}   AUTONOMOUS TERMINATION ENGAGED TO PROTECT GAS.   {Style.RESET_ALL}")
                logger.info(f"{Fore.RED}{Style.BRIGHT}=================================================={Style.RESET_ALL}")
                # Wait 3.0 seconds to allow the rent reclamation task to submit to the RPC network
                await asyncio.sleep(3.0)
                # Force clean exit to prevent further trades
                os._exit(0)
        else:
            logger.warning(f"[PUMP-SELL] Failed to sell {pos.token_symbol} after {max_retries} attempts.")
            pos.status = "sell_failed"

    async def _close_token_account_directly(self, mint: str, program_id: Pubkey = None) -> bool:
        """
        Directly compile, sign, and submit a close account transaction via RPC
        to reclaim the 0.00204 SOL rent exemption.
        """
        if not self.keypair or self.dry_run:
            return False

        try:
            from solders.pubkey import Pubkey
            from solders.transaction import Transaction
            from solders.hash import Hash
            from spl.token.instructions import close_account, CloseAccountParams
            import base64

            # Dynamic ATA program owner self-detection (recovers edge cases with zero balances)
            token_program = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            token2022_program = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
            wallet_pub = self.keypair.pubkey()
            mint_pub = Pubkey.from_string(mint)
            
            # 1. Check if caller forced standard token program, otherwise auto-detect
            if program_id is None or program_id == token_program:
                ata_2022, _ = Pubkey.find_program_address(
                    [bytes(wallet_pub), bytes(token2022_program), bytes(mint_pub)],
                    Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
                )
                # Check if Token2022 account exists on-chain
                payload_info = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getAccountInfo",
                    "params": [str(ata_2022), {"encoding": "base64"}]
                }
                is_2022 = False
                try:
                    resp_info = await self.http.post(RPC_HTTP, json=payload_info, timeout=5.0)
                    if resp_info.status_code == 200 and resp_info.json().get("result", {}).get("value") is not None:
                        is_2022 = True
                except Exception:
                    pass
                program_id = token2022_program if is_2022 else token_program
            
            # 2. Derive the correct active ATA
            ata_pub, _ = Pubkey.find_program_address(
                [
                    bytes(wallet_pub),
                    bytes(program_id),
                    bytes(mint_pub),
                ],
                Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"),
            )

            # Get recent blockhash
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            resp = await self.http.post(RPC_HTTP, json=payload, timeout=5.0)
            if resp.status_code != 200:
                logger.warning(f"[RECLAIM] Failed to get latest blockhash for {mint[:8]}")
                return False
                
            blockhash_str = resp.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash_str:
                return False

            # Compile instruction
            inst = close_account(
                CloseAccountParams(
                    program_id=program_id,
                    account=ata_pub,
                    dest=wallet_pub,
                    owner=wallet_pub,
                )
            )

            # Build signed transaction
            tx = Transaction.new_signed_with_payer(
                [inst],
                wallet_pub,
                [self.keypair],
                Hash.from_string(blockhash_str)
            )

            # Send transaction
            encoded = base64.b64encode(bytes(tx)).decode("utf-8")
            send_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [
                    encoded,
                    {"encoding": "base64", "skipPreflight": True}
                ]
            }

            send_resp = await self.http.post(RPC_HTTP, json=send_payload, timeout=10.0)
            if send_resp.status_code == 200:
                result = send_resp.json()
                if "result" in result:
                    sig = result["result"]
                    logger.info(f"{Fore.LIGHTGREEN_EX}[RECLAIM-SUCCESS]{Style.RESET_ALL} Reclaimed rent for {mint[:8]}... | TX: {sig[:16]}...")
                    return True
                else:
                    logger.warning(f"[RECLAIM-ERROR] Failed to send reclaim tx for {mint[:8]}: {result.get('error')}")
            else:
                logger.warning(f"[RECLAIM-ERROR] RPC HTTP error: {send_resp.status_code}")

        except Exception as e:
            logger.error(f"[RECLAIM-EXCEPTION] Error closing token account for {mint[:8]}: {e}")

        return False

    async def reclaim_all_dust_accounts(self) -> float:
        """
        Scans wallet for any active token accounts with 0 balance
        ending in 'pump' and closes them to reclaim the locked 0.00204 SOL rent.
        Supports both standard SPL and Token-2022 programs.
        """
        if not self.keypair or self.dry_run:
            return 0.0

        logger.info(f"{Fore.LIGHTCYAN_EX}[ATA-CLEANER]{Style.RESET_ALL} Scanning for dead token accounts...")
        reclaimed_sol = 0.0
        try:
            token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            token2022_program = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

            accounts = []
            for prog_id in [token_program, token2022_program]:
                payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        str(self.keypair.pubkey()),
                        {"programId": prog_id},
                        {"encoding": "jsonParsed"}
                    ]
                }
                resp = await self.http.post(RPC_HTTP, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    prog_accounts = resp.json().get("result", {}).get("value", [])
                    # Append program ID context to each account dict
                    for a in prog_accounts:
                        a["programId"] = prog_id
                    accounts.extend(prog_accounts)

            dead_accounts = []

            for acct in accounts:
                info = acct["account"]["data"]["parsed"]["info"]
                mint = info["mint"]
                amount = float(info["tokenAmount"].get("uiAmount") or 0)
                ata_pubkey = acct["pubkey"]
                prog_id = acct.get("programId", token_program)

                # Only sweep genuine pump.fun accounts with 0 balance
                if mint.endswith("pump") and amount == 0:
                    dead_accounts.append((mint, ata_pubkey, prog_id))

            if not dead_accounts:
                logger.info(f"{Fore.LIGHTCYAN_EX}[ATA-CLEANER]{Style.RESET_ALL} No dead token accounts found.")
                return 0.0

            logger.info(f"{Fore.LIGHTCYAN_EX}[ATA-CLEANER]{Style.RESET_ALL} Found {len(dead_accounts)} dead token accounts. Batch reclaiming...")

            # Get recent blockhash
            payload_bh = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            }
            resp_bh = await self.http.post(RPC_HTTP, json=payload_bh, timeout=5.0)
            if resp_bh.status_code != 200:
                return 0.0
            blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash_str:
                return 0.0

            from solders.pubkey import Pubkey
            from solders.transaction import Transaction
            from solders.hash import Hash
            from spl.token.instructions import close_account, CloseAccountParams
            import base64

            # Batch them in sizes of 8 to fit within transaction bounds safely
            batch_size = 8
            for i in range(0, len(dead_accounts), batch_size):
                chunk = dead_accounts[i:i+batch_size]
                instructions = []
                
                for mint, ata, prog_id in chunk:
                    inst = close_account(
                        CloseAccountParams(
                            program_id=Pubkey.from_string(prog_id),
                            account=Pubkey.from_string(ata),
                            dest=self.keypair.pubkey(),
                            owner=self.keypair.pubkey(),
                        )
                    )
                    instructions.append(inst)

                tx = Transaction.new_signed_with_payer(
                    instructions,
                    self.keypair.pubkey(),
                    [self.keypair],
                    Hash.from_string(blockhash_str)
                )

                encoded = base64.b64encode(bytes(tx)).decode("utf-8")
                send_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        encoded,
                        {"encoding": "base64", "skipPreflight": True}
                    ]
                }
                
                send_resp = await self.http.post(RPC_HTTP, json=send_payload, timeout=10.0)
                if send_resp.status_code == 200:
                    res = send_resp.json()
                    if "result" in res:
                        sig = res["result"]
                        chunk_reclaimed = len(chunk) * 0.00203928
                        reclaimed_sol += chunk_reclaimed
                        logger.info(
                            f"{Fore.GREEN}[ATA-CLEANER-SUCCESS]{Style.RESET_ALL} Reclaimed {len(chunk)} accounts! "
                            f"Refund: +{chunk_reclaimed:.5f} SOL | TX: {sig[:16]}..."
                        )
                        # Avoid rate limit
                        await asyncio.sleep(1.0)
                    else:
                        logger.warning(f"[ATA-CLEANER-ERROR] Failed to reclaim chunk: {res.get('error')}")

        except Exception as e:
            logger.error(f"[ATA-CLEANER-EXCEPTION] Error during dead account sweep: {e}")

        return reclaimed_sol

    async def _print_status(self):
        """Periodic status output"""
        while self.running:
            await asyncio.sleep(30)
            active = sum(1 for p in self.positions.values() if p.status == "active")
            mode = "DRY RUN" if self.dry_run else "LIVE"

            logger.info(
                f"{Fore.LIGHTCYAN_EX}[PUMP-STATUS]{Style.RESET_ALL} "
                f"[{mode}] Seen: {self.tokens_seen} | "
                f"Filtered: {self.tokens_filtered} | "
                f"Sniped: {self.tokens_bought} | "
                f"Active: {active}/{self.max_concurrent} | "
                f"P&L: {self.total_profit_sol:+.4f} SOL"
            )
    async def _recover_positions(self):
        """
        Scan wallet for existing token holdings on startup.
        Registers any found tokens as active positions so the monitor
        can manage them (take profit, stop loss, timeout).
        This prevents orphaned tokens when the bot restarts.
        """
        if not self.keypair:
            return

        try:
            # Known tokens to ignore (not from pump.fun sniping)
            IGNORE_MINTS = {
                "So11111111111111111111111111111111111111112",   # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", # USDC
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            }

            token_program = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            token2022_program = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

            accounts = []
            for prog_id in [token_program, token2022_program]:
                payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        str(self.keypair.pubkey()),
                        {"programId": prog_id},
                        {"encoding": "jsonParsed"}
                    ]
                }
                resp = await self.http.post(RPC_HTTP, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    prog_accounts = resp.json().get("result", {}).get("value", [])
                    accounts.extend(prog_accounts)

            recovered = 0
            from solders.pubkey import Pubkey

            for acct in accounts:
                info = acct["account"]["data"]["parsed"]["info"]
                mint = info["mint"]
                amount = float(info["tokenAmount"].get("uiAmount") or 0)
                raw_amount = int(info["tokenAmount"].get("amount", "0"))
                decimals = info["tokenAmount"].get("decimals", 6)

                # Core fix: Only recover genuine pump.fun tokens (must end with "pump")
                if not mint.endswith("pump"):
                    continue

                # Skip zero balances, known tokens, and dust (< 10 tokens)
                if amount <= 10 or mint in IGNORE_MINTS:
                    continue

                # Skip if already tracked
                if mint in self.positions:
                    continue

                # Derive bonding curve PDA for real-time price monitoring
                bonding_curve = ""
                entry_price = 0.0
                entry_virtual_sol = 0
                
                try:
                    mint_pubkey = Pubkey.from_string(mint)
                    program_id = Pubkey.from_string(PUMPFUN_PROGRAM_ID)
                    pda, _ = Pubkey.find_program_address(
                        [b"bonding-curve", bytes(mint_pubkey)],
                        program_id
                    )
                    bonding_curve = str(pda)
                    
                    # Fetch current price & virtual SOL reserves to establish high-fidelity paper trading baseline
                    bc_state = await self._get_bonding_curve_state(bonding_curve)
                    if bc_state:
                        entry_price = bc_state["price_sol"]
                        entry_virtual_sol = bc_state["virtual_sol_reserves"]
                except Exception as e:
                    logger.debug(f"[RECOVERY] Error deriving PDA / state for {mint[:8]}: {e}")

                entry_sol = (raw_amount * entry_price) / 1e9 if entry_price > 0 else self.max_snipe_sol

                # Register as a recovered position
                self.positions[mint] = SniperPosition(
                    token_mint=mint,
                    token_name=f"Recovered-{mint[:8]}",
                    token_symbol="???",
                    bonding_curve=bonding_curve,
                    entry_sol=entry_sol,
                    entry_time=time.time(),  # Treat as just bought
                    entry_price=entry_price,
                    token_amount=raw_amount,
                    peak_price=entry_price,
                    buy_tx="recovered",
                    status="active",
                    entry_virtual_sol=entry_virtual_sol,
                )
                recovered += 1
                asyncio.create_task(self._monitor_single_position(mint))
                
                mode_str = "DRY RUN" if self.dry_run else "LIVE"
                logger.info(
                    f"{Fore.LIGHTYELLOW_EX}[RECOVERED ({mode_str})]{Style.RESET_ALL} "
                    f"Found {amount:,.2f} tokens of {Fore.CYAN}{mint[:16]}...{Style.RESET_ALL} "
                    f"— Baseline price: {entry_price:.12f} SOL | "
                    f"Registered as active position for P&L tracking"
                )

            if recovered > 0:
                logger.info(
                    f"{Fore.LIGHTGREEN_EX}[RECOVERY]{Style.RESET_ALL} "
                    f"Recovered {recovered} existing position(s) from wallet"
                )

        except Exception as e:
            logger.error(f"[RECOVERY] Error scanning wallet: {e}")

    async def run(self):
        """Main entry point — connects to PumpPortal and starts sniping"""
        self.running = True
        mode = f"{Fore.RED}LIVE{Style.RESET_ALL}" if not self.dry_run else f"{Fore.YELLOW}DRY RUN{Style.RESET_ALL}"
        snipe_usd = self.max_snipe_sol * self.sol_price_usd if self.sol_price_usd > 0 else 0

        await self._fetch_sol_price()
        snipe_usd = self.max_snipe_sol * self.sol_price_usd

        print(f"""
{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}========================================================================
              PUMP.FUN TOKEN SNIPER — BONDING CURVE ENGINE
                 cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
Mode:           {mode}
Max snipe:      {self.max_snipe_sol} SOL (~${snipe_usd:.2f})
Take profit:    {self.take_profit_pct}%
Stop loss:      {self.stop_loss_pct}% trailing
Timeout:        {self.timeout_secs}s
Max positions:  {self.max_concurrent}
Daily loss cap: {self.daily_loss_limit} SOL
""")

        # Scan wallet for existing token holdings (recover positions from restarts)
        await self._recover_positions()

        # Hardening Fix: Auto-reclaim dead token accounts on startup to recover locked rent SOL
        if not self.dry_run:
            await self.reclaim_all_dust_accounts()

        # Launch background tasks
        asyncio.create_task(self.tripwire.start())
        asyncio.create_task(self._print_status())

        # Main WebSocket loop with reconnect
        while self.running:
            try:
                logger.info(
                    f"{Fore.LIGHTCYAN_EX}[PUMP-SNIPER]{Style.RESET_ALL} "
                    f"Connecting to PumpPortal WebSocket..."
                )

                async with websockets.connect(
                    PUMPPORTAL_WS,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    # Subscribe to new token creation events
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[PUMP-SNIPER]{Style.RESET_ALL} "
                        f"Subscribed to new token events. Watching for launches..."
                    )

                    async for message in ws:
                        if not self.running:
                            break
                        try:
                            data = json.loads(message)

                            # New token event
                            if "mint" in data and "name" in data:
                                await self._handle_new_token(data)

                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"[PUMP-SNIPER] Handler error: {e}")
                            continue

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"[PUMP-SNIPER] WebSocket disconnected: {e}. Reconnecting in 3s..."
                )
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(
                    f"[PUMP-SNIPER] Connection error: {e}. Reconnecting in 5s..."
                )
                await asyncio.sleep(5)


async def main():
    """Standalone entry point for pump.fun sniper"""
    import colorama
    colorama.init()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("live_single_trade_test.log", mode="w", encoding="utf-8"),
        ],
    )

    sniper = PumpFunSniper(
        max_snipe_sol=0.001,    # Minimum live test: ~$0.17
        take_profit_pct=100.0,
        stop_loss_pct=30.0,
        timeout_secs=300.0,
        max_concurrent=1,       # Single position only
        strict_cabal_mode=False, # Buy ANY token passing all security audits
        dry_run=os.getenv("DRY_RUN", "True").lower() == "true",
    )

    await sniper.run()


if __name__ == "__main__":
    asyncio.run(main())
