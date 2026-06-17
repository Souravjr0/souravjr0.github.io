import os
import sys
import json
import asyncio
import base64
import logging
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import websockets
import httpx
from colorama import init, Fore, Style

# Force unbuffered output for real-time console streaming
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)


# Add local path to import parsers
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from pool_parsers import parse_raydium_clmm, parse_orca_whirlpool, parse_raydium_amm_v4, parse_spl_token_account
from arbitrage_engine import (
    check_arbitrage,
    check_arbitrage_sol_native,
    check_arbitrage_mixed,
    check_arbitrage_sol_native_mixed
)
from micro_strategy import evaluate_opportunity, SpikeDetector, get_balance_tier
from profit_tracker import ProfitTracker
from jup_arb_engine import JupiterArbEngine, TRIANGLE_TOKENS
from pumpfun_sniper import PumpFunSniper
from copy_trader import CopyTrader
from collector import DatabaseManager, DataCollector
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned


# Initialize colorama
init(autoreset=True)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.LIGHTBLACK_EX}[%(asctime)s] [%(levelname)s]{Style.RESET_ALL} %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SolanaArbBot")

# Load environment
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


WSS_URL = os.getenv("HELIUS_WSS_URL")
RPC_URL = os.getenv("HELIUS_RPC_URL")
JITO_URL = os.getenv("JITO_BLOCK_ENGINE_URL", "https://mainnet.block-engine.jito.wtf/api/v1/bundles")

# Parse backup RPCs from env or use defaults
backup_rpcs_raw = os.getenv("BACKUP_RPC_URLS", "")
BACKUP_RPCS = [r.strip() for r in backup_rpcs_raw.split(",") if r.strip()]
if not BACKUP_RPCS:
    BACKUP_RPCS = [
        "https://api.mainnet-beta.solana.com",
        "https://rpc.ankr.com/solana",
        "https://solana-api.projectserum.com"
    ]

# Parse backup WSS from env or use defaults
backup_wss_raw = os.getenv("BACKUP_WSS_URLS", "")
BACKUP_WSS = [w.strip() for w in backup_wss_raw.split(",") if w.strip()]
if not BACKUP_WSS:
    BACKUP_WSS = [
        "wss://api.mainnet-beta.solana.com",
        "wss://rpc.ankr.com/solana/ws"
    ]

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

RAYDIUM_API_MINT_URL = "https://api-v3.raydium.io/pools/info/mint"
ORCA_WHIRLPOOL_LIST_URLS = [
    "https://api.mainnet.orca.so/v1/whirlpool/list",
    "https://api.orca.so/v1/whirlpool/list"
]

JUP_TOKEN_LIST_URLS = [
    "https://token.jup.ag/strict",
    "https://token.jup.ag/all"
]
JUP_PRICE_URL = "https://api.jup.ag/price/v3"

PAIR_QUOTE_SYMBOLS = ["USDC", "USDT", "JTO", "BONK", "JUP"]

# Fallback SOL/USDC Concentrated Liquidity Pools (0.05% fee tiers)
RAYDIUM_CLMM_POOL = "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq"
ORCA_WHIRLPOOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

async def fetch_jupiter_token_list() -> Dict[str, Dict[str, Any]]:
    for url in JUP_TOKEN_LIST_URLS:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Jupiter token list HTTP {resp.status_code}: {resp.text}")
                continue
            tokens = resp.json()
            if not isinstance(tokens, list):
                continue
            token_map: Dict[str, Dict[str, Any]] = {}
            for token in tokens:
                symbol = token.get("symbol")
                address = token.get("address")
                decimals = token.get("decimals")
                if not symbol or not address or decimals is None:
                    continue
                token_map[symbol.upper()] = {
                    "address": address,
                    "decimals": int(decimals)
                }
            if token_map:
                return token_map
        except Exception as e:
            logger.warning(f"Failed to fetch Jupiter token list: {e}")

    return {}

async def build_pair_configs() -> List[Dict[str, Any]]:
    token_map = await fetch_jupiter_token_list()
    
    # Fallback profiles in case of network/DNS failures
    STATIC_FALLBACKS = {
        "USDC": {"address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "decimals": 6},
        "USDT": {"address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "decimals": 6},
        "JTO": {"address": "jtoSnE795qyv2wJTxtjZa5hkcz3gJaHAwtLedHsQNrr", "decimals": 9},
        "BONK": {"address": "DezXAZ8z7PnrnRJjz3wX4mPtkoc27DPm759wyB75zPLr", "decimals": 5},
        "JUP": {"address": "JUPyiwrYdGVGgzJABd847LsHWtwYY611L4xg5E184cM", "decimals": 6}
    }
    
    pair_configs: List[Dict[str, Any]] = []

    for symbol in PAIR_QUOTE_SYMBOLS:
        token = token_map.get(symbol)
        if not token:
            token = STATIC_FALLBACKS.get(symbol)
            if token:
                logger.info(f"Using static token profile fallback for: {symbol}")
            else:
                logger.warning(f"Token symbol not found in Jupiter list or static fallbacks: {symbol}")
                continue
                
        pair_configs.append({
            "pair_name": f"SOL/{symbol}",
            "base_mint": SOL_MINT,
            "quote_mint": token["address"],
            "base_decimals": 9,
            "quote_decimals": token["decimals"],
            "quote_symbol": symbol
        })

    return pair_configs

class CapitalAllocator:
    """Simple capital allocator to prevent engines from competing for the same funds."""

    def __init__(self, total_sol: float, total_usdc: float):
        self.total_sol = total_sol
        self.total_usdc = total_usdc
        self.allocated_sol = 0.0
        self.allocated_usdc = 0.0
        self._lock = asyncio.Lock()

    async def reserve(self, sol: float = 0.0, usdc: float = 0.0) -> bool:
        async with self._lock:
            if self.allocated_sol + sol > self.total_sol or self.allocated_usdc + usdc > self.total_usdc:
                return False
            self.allocated_sol += sol
            self.allocated_usdc += usdc
            return True

    async def release(self, sol: float = 0.0, usdc: float = 0.0):
        async with self._lock:
            self.allocated_sol = max(0.0, self.allocated_sol - sol)
            self.allocated_usdc = max(0.0, self.allocated_usdc - usdc)

    async def get_available(self) -> tuple[float, float]:
        async with self._lock:
            return self.total_sol - self.allocated_sol, self.total_usdc - self.allocated_usdc


class SolanaArbBot:
    def __init__(
        self,
        quote_mint: str = USDC_MINT,
        quote_symbol: str = "USDC",
        quote_decimals: int = 6,
        pair_name: str = "SOL/USDC",
        profit_db_path: Optional[str] = None,
        profit_tracker: Optional[ProfitTracker] = None
    ):
        self.base_mint = SOL_MINT
        self.quote_mint = quote_mint
        self.quote_symbol = quote_symbol
        self.quote_decimals = quote_decimals
        self.pair_name = pair_name

        # Setup failover RPC list and active index
        self.rpc_urls = [RPC_URL] + [url for url in BACKUP_RPCS if url]
        self.current_rpc_idx = 0

        # Setup failover WSS list and active index
        self.wss_urls = [WSS_URL] + [url for url in BACKUP_WSS if url]
        self.current_wss_idx = 0

        self.raydium_state = {"sqrt_price": 0, "liquidity": 0}
        self.orca_state = {"sqrt_price": 0, "liquidity": 0}
        if quote_mint == USDC_MINT:
            self.raydium_pool_ids: List[str] = [RAYDIUM_CLMM_POOL]
            self.orca_pool_ids: List[str] = [ORCA_WHIRLPOOL]
        else:
            self.raydium_pool_ids = []
            self.orca_pool_ids = []
        self.raydium_pools: Dict[str, Dict[str, Any]] = {}
        self.orca_pools: Dict[str, Dict[str, Any]] = {}
        self.raydium_pool_meta_by_id: Dict[str, Dict[str, Any]] = {}
        self.raydium_pool_kind_by_id: Dict[str, str] = {}
        self.raydium_amm_vault_map: Dict[str, Dict[str, str]] = {}
        self.raydium_active_pool: Optional[str] = None
        self.orca_active_pool: Optional[str] = None
        self.raydium_active_kind: Optional[str] = None
        self.pool_type_by_id: Dict[str, str] = {}
        self.running = False
        self.http_client = httpx.AsyncClient(timeout=10)
        
        # Balance cache to prevent RPC rate-limits
        self.cached_sol_bal = 0.0
        self.cached_usdc_bal = 0.0
        self.last_balance_update = 0.0
        
        # Phase 6: Micro-Strategy components
        self.spike_detector = SpikeDetector(window_size=120, spike_multiplier=3.0)
        if profit_tracker:
            self.profit_tracker = profit_tracker
        elif profit_db_path:
            self.profit_tracker = ProfitTracker(db_path=profit_db_path)
        else:
            self.profit_tracker = ProfitTracker()
        self.current_sol_price = 0.0  # SOL USD price
        self.pair_price = 0.0  # Quote per SOL from pools
        self.quote_usd_price = 1.0
        self.token_price_last_update = 0.0
        self.trade_count = 0
        self.opportunity_count = 0
        
        # Phase 7: Jupiter Quote-Based Arbitrage Engine
        self.jup_arb = JupiterArbEngine(self.http_client, sol_price=0.0)
        self.jup_scan_interval = 8.0  # Seconds between Jupiter scan cycles
        self.jup_enabled = True  # Master toggle for Jupiter scanning
        
        # Load live keypair if configured for Public Mempool Execution
        self.keypair = None
        pkey_str = os.getenv("SOLANA_PRIVATE_KEY")
        if pkey_str:
            try:
                pkey_str = pkey_str.strip()
                if pkey_str.startswith("["):
                    secret_bytes = json.loads(pkey_str)
                    self.keypair = Keypair.from_bytes(bytes(secret_bytes))
                else:
                    self.keypair = Keypair.from_base58_string(pkey_str)
                logger.info(f"Loaded Wallet Public Key: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Error loading private key: {e}")

    @staticmethod
    def _chunk_list(items: List[str], chunk_size: int = 100) -> List[List[str]]:
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    async def post_rpc(self, payload: Dict[str, Any], timeout: float = 15.0) -> httpx.Response:
        """Sends a JSON-RPC payload to the RPC endpoint with automatic failover rotation"""
        last_exception = None
        for _ in range(len(self.rpc_urls)):
            url = self.rpc_urls[self.current_rpc_idx]
            try:
                resp = await self.http_client.post(url, json=payload, timeout=timeout)
                if resp.status_code == 429 or resp.status_code >= 500:
                    logger.warning(
                        f"[{self.pair_name}] RPC {url[:35]}.. returned HTTP {resp.status_code}. Rotating to backup..."
                    )
                    self.current_rpc_idx = (self.current_rpc_idx + 1) % len(self.rpc_urls)
                    continue
                return resp
            except Exception as e:
                logger.warning(
                    f"[{self.pair_name}] RPC {url[:35]}.. request failed: {e}. Rotating to backup..."
                )
                self.current_rpc_idx = (self.current_rpc_idx + 1) % len(self.rpc_urls)
                last_exception = e
        if last_exception:
            raise last_exception
        raise RuntimeError(f"[{self.pair_name}] All RPC failover endpoints exhausted.")

    @staticmethod
    def _mints_match(mint_a: Optional[str], mint_b: Optional[str], target_a: str, target_b: str) -> bool:
        if not mint_a or not mint_b:
            return False
        return mint_a == target_a and mint_b == target_b

    @staticmethod
    def _select_best_pool(
        pool_states: Dict[str, Dict[str, Any]],
        pool_meta: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Optional[str]:
        if not pool_states:
            return None
        def score(pid: str) -> float:
            if pool_meta and pid in pool_meta:
                tvl = pool_meta[pid].get("tvl")
                if isinstance(tvl, (int, float)):
                    return float(tvl)
            return float(pool_states[pid].get("liquidity", 0))

        return max(pool_states, key=score)

    @staticmethod
    def _hex_to_pubkey(hex_str: str) -> str:
        return str(Pubkey(bytes.fromhex(hex_str)))

    @staticmethod
    def _amm_price(state: Dict[str, Any]) -> float:
        reserve_base = state.get("reserve_base", 0)
        reserve_quote = state.get("reserve_quote", 0)
        base_decimals = state.get("base_decimal", 9)
        quote_decimals = state.get("quote_decimal", 6)
        if reserve_base <= 0 or reserve_quote <= 0:
            return 0.0
        base = reserve_base / (10 ** base_decimals)
        quote = reserve_quote / (10 ** quote_decimals)
        if base <= 0:
            return 0.0
        return quote / base

    def _apply_pool_update(self, dex: str, pool_id: str, new_state: Dict[str, Any]) -> bool:
        if dex == "raydium":
            pool_map = self.raydium_pools
            active_id = self.raydium_active_pool
            active_kind = self.raydium_active_kind
            new_kind = self.raydium_pool_kind_by_id.get(pool_id)
        else:
            pool_map = self.orca_pools
            active_id = self.orca_active_pool
            active_kind = None
            new_kind = None

        prev_state = pool_map.get(pool_id)
        pool_map[pool_id] = new_state

        active_changed = False
        if active_id is None or pool_id == active_id:
            active_changed = True
        elif dex == "raydium" and active_kind and new_kind and active_kind != new_kind:
            active_changed = False
        else:
            active_liq = pool_map.get(active_id, {}).get("liquidity", 0)
            if new_state.get("liquidity", 0) >= active_liq:
                active_changed = True

        if active_changed:
            if dex == "raydium":
                self.raydium_active_pool = pool_id
                self.raydium_state = new_state
                self.raydium_active_kind = new_kind
            else:
                self.orca_active_pool = pool_id
                self.orca_state = new_state

            if active_id and active_id != pool_id:
                logger.info(
                    f"Active {dex} pool switched: {active_id[:12]}.. -> {pool_id[:12]}.."
                )

        if not active_changed:
            return False
        if prev_state is None or active_id != pool_id:
            return True
        return new_state.get("sqrt_price") != prev_state.get("sqrt_price")

    def _get_raydium_price(self) -> float:
        """Returns the current Raydium price, handling both CLMM and AMM v4 pool types"""
        if self.raydium_active_kind == "amm_v4":
            return self._amm_price(self.raydium_state)
        else:
            sqrt_price = self.raydium_state.get("sqrt_price", 0)
            if sqrt_price <= 0:
                return 0.0
            return (sqrt_price / (2**64)) ** 2 * 1000

    def _apply_amm_vault_update(self, pool_id: str, side: str, amount_raw: int) -> bool:
        state = self.raydium_pools.get(pool_id)
        if not state:
            return False

        key = "reserve_base" if side == "base" else "reserve_quote"
        prev_amount = state.get(key)
        state[key] = amount_raw

        # Use quote reserve for rough liquidity ordering among AMM pools
        state["liquidity"] = state.get("reserve_quote", 0)

        price_changed = False
        if pool_id == self.raydium_active_pool:
            self.raydium_state = state
            if prev_amount is None or prev_amount != amount_raw:
                price_changed = True

        return price_changed

    async def discover_pools(self) -> None:
        raydium_ids = await self.fetch_raydium_pools(self.base_mint, self.quote_mint)
        orca_ids = await self.fetch_orca_pools(self.base_mint, self.quote_mint)

        if raydium_ids:
            self.raydium_pool_ids = raydium_ids
        else:
            if self.quote_mint == USDC_MINT:
                self.raydium_pool_ids = [RAYDIUM_CLMM_POOL]
                logger.warning("Raydium pool discovery failed; using fallback pool list.")
            else:
                self.raydium_pool_ids = []
                logger.warning("Raydium pool discovery failed; no fallback pools for this pair.")

        if orca_ids:
            self.orca_pool_ids = orca_ids
        else:
            if self.quote_mint == USDC_MINT:
                self.orca_pool_ids = [ORCA_WHIRLPOOL]
                logger.warning("Orca pool discovery failed; using fallback pool list.")
            else:
                self.orca_pool_ids = []
                logger.warning("Orca pool discovery failed; no fallback pools for this pair.")

        self.pool_type_by_id = {pid: "raydium" for pid in self.raydium_pool_ids}
        self.pool_type_by_id.update({pid: "orca" for pid in self.orca_pool_ids})

        logger.info(
            f"Discovered {len(self.raydium_pool_ids)} Raydium CLMM pool(s) and "
            f"{len(self.orca_pool_ids)} Orca whirlpool(s)."
        )

    async def fetch_raydium_pools(self, mint_a: str, mint_b: str) -> List[str]:
        pool_ids: List[str] = []
        page = 1
        page_size = 100
        self.raydium_pool_meta_by_id = {}
        self.raydium_pool_kind_by_id = {}

        while True:
            params = {
                "mint1": mint_a,
                "mint2": mint_b,
                "poolType": "all",
                "poolSortField": "liquidity",
                "sortType": "desc",
                "pageSize": page_size,
                "page": page
            }
            try:
                resp = await self.http_client.get(RAYDIUM_API_MINT_URL, params=params, timeout=10.0)
            except Exception as e:
                logger.warning(f"Raydium pool discovery request failed: {e}")
                break

            if resp.status_code != 200:
                logger.warning(f"Raydium pool discovery HTTP {resp.status_code}: {resp.text}")
                break

            data = resp.json()
            pools = data.get("data", {}).get("data", [])
            if not pools:
                break

            for pool in pools:
                mint_a_addr = (pool.get("mintA") or {}).get("address") or pool.get("mintAAddress") or pool.get("mintA")
                mint_b_addr = (pool.get("mintB") or {}).get("address") or pool.get("mintBAddress") or pool.get("mintB")

                if not self._mints_match(mint_a_addr, mint_b_addr, mint_a, mint_b):
                    continue

                pool_kind_raw = str(pool.get("type") or pool.get("poolType") or "").lower()
                pool_kind: Optional[str] = None
                if "clmm" in pool_kind_raw or "concentrated" in pool_kind_raw:
                    pool_kind = "clmm"
                elif "amm" in pool_kind_raw or "standard" in pool_kind_raw or "cpmm" in pool_kind_raw:
                    pool_kind = "amm_v4"

                if pool_kind is None:
                    continue

                pool_id = pool.get("id")
                if pool_id:
                    pool_ids.append(pool_id)
                    self.raydium_pool_meta_by_id[pool_id] = {
                        "tvl": pool.get("tvl", 0),
                        "kind": pool_kind
                    }
                    self.raydium_pool_kind_by_id[pool_id] = pool_kind

            if len(pools) < page_size:
                break
            page += 1

        return list(dict.fromkeys(pool_ids))

    async def fetch_orca_pools(self, mint_a: str, mint_b: str) -> List[str]:
        pool_ids: List[str] = []

        for url in ORCA_WHIRLPOOL_LIST_URLS:
            try:
                resp = await self.http_client.get(url, timeout=10.0)
            except Exception as e:
                logger.warning(f"Orca pool discovery request failed: {e}")
                continue

            if resp.status_code != 200:
                logger.warning(f"Orca pool discovery HTTP {resp.status_code}: {resp.text}")
                continue

            data = resp.json()
            pools = data.get("whirlpools") or data.get("data") or data
            if not isinstance(pools, list):
                continue

            for pool in pools:
                mint_a_addr = (pool.get("tokenA") or {}).get("mint") or pool.get("tokenMintA") or pool.get("tokenA")
                mint_b_addr = (pool.get("tokenB") or {}).get("mint") or pool.get("tokenMintB") or pool.get("tokenB")

                if not self._mints_match(mint_a_addr, mint_b_addr, mint_a, mint_b):
                    continue

                if pool.get("isActive") is False:
                    continue

                pool_id = pool.get("address") or pool.get("whirlpoolAddress") or pool.get("id")
                if pool_id:
                    pool_ids.append(pool_id)

            if pool_ids:
                break

        return list(dict.fromkeys(pool_ids))

    async def fetch_token_account_amounts(self, accounts: List[str]) -> Dict[str, int]:
        balances: Dict[str, int] = {}
        if not accounts:
            return balances

        for chunk in self._chunk_list(accounts, 100):
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getMultipleAccounts",
                "params": [
                    chunk,
                    {"encoding": "base64"}
                ]
            }
            try:
                response = await self.post_rpc(payload)
                result = response.json().get("result")
                if not result or not result.get("value"):
                    logger.warning(f"Failed to fetch vault balances: {response.text}")
                    continue

                value = result["value"]
                for idx, account in enumerate(value):
                    if not account:
                        continue
                    raw = base64.b64decode(account["data"][0])
                    balances[chunk[idx]] = parse_spl_token_account(raw)
            except Exception as e:
                logger.warning(f"Failed to fetch vault balances: {e}")

        return balances

    async def update_token_prices(self) -> None:
        """Updates SOL and quote token USD prices. Skips for stablecoin pairs since pool price = USD price."""
        # For USDC/USDT pairs, pool price IS the USD price — no API needed
        if self.quote_symbol.upper() in ("USDC", "USDT"):
            if self.pair_price > 0:
                self.current_sol_price = self.pair_price
                self.quote_usd_price = 1.0
            return

        now = time.time()
        if (now - self.token_price_last_update) < 60:
            return

        # Update timestamp FIRST to prevent retry spam on failure
        self.token_price_last_update = now

        mints = [SOL_MINT, self.quote_mint]
        url = f"{JUP_PRICE_URL}?ids={','.join(mints)}"
        try:
            resp = await self.http_client.get(url, timeout=10.0)
            if resp.status_code != 200:
                logger.warning(f"Jupiter price API HTTP {resp.status_code}")
                return
            resp_json = resp.json()
            sol_price = resp_json.get(SOL_MINT, {}).get("usdPrice")
            quote_price = resp_json.get(self.quote_mint, {}).get("usdPrice")

            if isinstance(sol_price, (int, float)):
                self.current_sol_price = float(sol_price)
            if isinstance(quote_price, (int, float)):
                self.quote_usd_price = float(quote_price)
        except Exception as e:
            logger.warning(f"Failed to update token prices: {e}")

    async def get_initial_states(self):
        """Pre-populates our concentrated liquidity state caches from mainnet"""
        logger.info("Initializing Raydium CLMM and Orca state caches from chain...")

        await self.discover_pools()
        all_pools = self.raydium_pool_ids + self.orca_pool_ids
        if not all_pools:
            logger.error("No pools available for initialization.")
            return False

        self.raydium_pools = {}
        self.orca_pools = {}
        self.raydium_amm_vault_map = {}
        amm_vaults: List[str] = []

        try:
            for chunk in self._chunk_list(all_pools, 100):
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getMultipleAccounts",
                    "params": [
                        chunk,
                        {"encoding": "base64"}
                    ]
                }

                response = await self.post_rpc(payload)
                result = response.json().get("result")
                if not result or not result.get("value"):
                    logger.error(f"Failed to load initial account data: {response.text}")
                    continue

                value = result["value"]
                for idx, account in enumerate(value):
                    pool_id = chunk[idx]
                    if not account:
                        continue
                    raw = base64.b64decode(account["data"][0])
                    dex = self.pool_type_by_id.get(pool_id)
                    try:
                        if dex == "raydium":
                            pool_kind = self.raydium_pool_kind_by_id.get(pool_id)
                            if pool_kind == "amm_v4" or len(raw) == 752:
                                amm_state = parse_raydium_amm_v4(raw)
                                base_vault = self._hex_to_pubkey(amm_state["base_vault"])
                                quote_vault = self._hex_to_pubkey(amm_state["quote_vault"])
                                base_mint = self._hex_to_pubkey(amm_state["base_mint"])
                                quote_mint = self._hex_to_pubkey(amm_state["quote_mint"])

                                if not self._mints_match(base_mint, quote_mint, self.base_mint, self.quote_mint):
                                    logger.debug(f"Skipping Raydium AMM pool with mismatched mints: {pool_id[:12]}..")
                                    continue

                                amm_state["base_vault"] = base_vault
                                amm_state["quote_vault"] = quote_vault
                                amm_state["base_mint"] = base_mint
                                amm_state["quote_mint"] = quote_mint

                                self.raydium_pools[pool_id] = amm_state
                                self.raydium_pool_kind_by_id[pool_id] = "amm_v4"
                                self.raydium_amm_vault_map[base_vault] = {"pool_id": pool_id, "side": "base"}
                                self.raydium_amm_vault_map[quote_vault] = {"pool_id": pool_id, "side": "quote"}
                                amm_vaults.extend([base_vault, quote_vault])
                            else:
                                self.raydium_pools[pool_id] = parse_raydium_clmm(raw)
                                self.raydium_pool_kind_by_id[pool_id] = "clmm"
                        elif dex == "orca":
                            self.orca_pools[pool_id] = parse_orca_whirlpool(raw)
                        else:
                            if len(raw) == 1544:
                                self.raydium_pools[pool_id] = parse_raydium_clmm(raw)
                                self.raydium_pool_kind_by_id[pool_id] = "clmm"
                            elif len(raw) == 752:
                                amm_state = parse_raydium_amm_v4(raw)
                                base_vault = self._hex_to_pubkey(amm_state["base_vault"])
                                quote_vault = self._hex_to_pubkey(amm_state["quote_vault"])
                                base_mint = self._hex_to_pubkey(amm_state["base_mint"])
                                quote_mint = self._hex_to_pubkey(amm_state["quote_mint"])

                                if not self._mints_match(base_mint, quote_mint, self.base_mint, self.quote_mint):
                                    logger.debug(f"Skipping Raydium AMM pool with mismatched mints: {pool_id[:12]}..")
                                    continue

                                amm_state["base_vault"] = base_vault
                                amm_state["quote_vault"] = quote_vault
                                amm_state["base_mint"] = base_mint
                                amm_state["quote_mint"] = quote_mint

                                self.raydium_pools[pool_id] = amm_state
                                self.raydium_pool_kind_by_id[pool_id] = "amm_v4"
                                self.raydium_amm_vault_map[base_vault] = {"pool_id": pool_id, "side": "base"}
                                self.raydium_amm_vault_map[quote_vault] = {"pool_id": pool_id, "side": "quote"}
                                amm_vaults.extend([base_vault, quote_vault])
                            elif len(raw) == 653:
                                self.orca_pools[pool_id] = parse_orca_whirlpool(raw)
                    except Exception as e:
                        logger.warning(f"Failed to parse pool {pool_id[:12]}..: {e}")

            if amm_vaults:
                vault_balances = await self.fetch_token_account_amounts(amm_vaults)
                for pool_id, state in self.raydium_pools.items():
                    if self.raydium_pool_kind_by_id.get(pool_id) != "amm_v4":
                        continue
                    base_vault = state.get("base_vault")
                    quote_vault = state.get("quote_vault")
                    state["reserve_base"] = vault_balances.get(base_vault, 0)
                    state["reserve_quote"] = vault_balances.get(quote_vault, 0)
                    state["liquidity"] = state.get("reserve_quote", 0)

            self.raydium_active_pool = self._select_best_pool(self.raydium_pools, self.raydium_pool_meta_by_id)
            self.orca_active_pool = self._select_best_pool(self.orca_pools)
            if not self.raydium_active_pool or not self.orca_active_pool:
                logger.error("Failed to initialize pool states.")
                return False

            self.raydium_state = self.raydium_pools[self.raydium_active_pool]
            self.orca_state = self.orca_pools[self.orca_active_pool]
            self.raydium_active_kind = self.raydium_pool_kind_by_id.get(self.raydium_active_pool, "clmm")

            if self.raydium_active_kind == "amm_v4":
                r_price = self._amm_price(self.raydium_state)
            else:
                r_price = (self.raydium_state["sqrt_price"] / (2**64)) ** 2 * 1000
            o_price = (self.orca_state["sqrt_price"] / (2**64)) ** 2 * 1000
            self.pair_price = r_price
            if self.quote_symbol.upper() in ("USDC", "USDT"):
                self.current_sol_price = r_price
            else:
                await self.update_token_prices()

            logger.info(
                f"Loaded! Raydium {self.raydium_active_kind.upper()} SOL Price: {r_price:.6f} "
                f"(Liquidity: {self.raydium_state.get('liquidity', 0)}) | Pool: {self.raydium_active_pool[:12]}.."
            )
            logger.info(
                f"Loaded! Orca SOL Price:         {o_price:.6f} "
                f"(Liquidity: {self.orca_state['liquidity']}) | Pool: {self.orca_active_pool[:12]}.."
            )

            spread = abs(r_price - o_price)
            spread_pct = (spread / r_price) * 100
            logger.info(f"Initial on-chain price spread: ${spread:.4f} ({spread_pct:.4f}%)")
            return True
        except Exception as e:
            logger.error(f"Failed during initialization: {e}")
            return False

    async def execute_dry_run_arbitrage(self, result: dict):
        """Simulates atomic trade construction and Jito bundle posting"""
        direction = result["direction"]
        amount_in = result["amount_in"] / 1e6
        amount_out = result["amount_out"] / 1e6
        raw_profit = result["raw_profit"] / 1e6
        pct = result["profit_pct"]
        
        print(f"""
{Fore.LIGHTGREEN_EX}{Style.BRIGHT}*** ARBITRAGE OPPORTUNITY FOUND ***
{Fore.GREEN}--------------------------------------------------
Direction:      {Fore.YELLOW}{direction.replace('_', ' -> ')}
USDC Input:     {Fore.WHITE}${amount_in:.2f} USDC
Expected Out:   {Fore.WHITE}${amount_out:.2f} USDC
Gross Profit:   {Fore.GREEN}+${raw_profit:.4f} USDC ({pct:.3f}%)
--------------------------------------------------
{Fore.CYAN}[DRY-RUN SIMULATION DATA]
1. Instruction 1: Swap {amount_in:.2f} USDC for SOL on {'Raydium CLMM' if 'Raydium_CLMM_to_Orca' in direction else 'Orca Whirlpool'}
2. Instruction 2: Swap SOL back to USDC on {'Orca Whirlpool' if 'Raydium_CLMM_to_Orca' in direction else 'Raydium CLMM'}
   - Setting slippage minimum amount out: ${result['amount_out'] / 1e6:.4f} USDC (reverts if yield dips)
3. Instruction 3: Transfer 0.0005 SOL (Jito Tip) to: 96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5
4. Payload Signed & Wrapped in a Jito Bundle.
5. Submitted to Jito Block Engine: {JITO_URL}
{Fore.LIGHTBLACK_EX}Status: Dry-run simulation executed. Real balance unaffected.
""")

    async def submit_jito_bundle(self, signed_txs: list, tip_lamports: int = 1000) -> Optional[str]:
        """
        Submits a bundle of signed transactions to Jito Block Engine.
        Each transaction in the bundle must already include a Jito tip transfer
        instruction to the tip account: 96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5
        
        Args:
            signed_txs: List of base64-encoded signed transaction strings
            tip_lamports: Tip amount in lamports (default 1000 = 0.000001 SOL)
        
        Returns:
            Bundle ID if accepted, None if failed
        """
        if not signed_txs:
            logger.error("No transactions provided for Jito bundle")
            return None
        
        try:
            # Convert base64 signed_txs to base58 for Jito Engine
            signed_txs_b58 = []
            for tx_b64 in signed_txs:
                raw_tx = base64.b64decode(tx_b64)
                tx_b58 = b58encode(raw_tx)
                signed_txs_b58.append(tx_b58)

            # Jito bundle submission via JSON-RPC
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendBundle",
                "params": [signed_txs_b58]
            }
            
            logger.info(
                f"{Fore.LIGHTCYAN_EX}[JITO]{Style.RESET_ALL} Submitting bundle with "
                f"{len(signed_txs)} transaction(s) | Tip: {tip_lamports} lamports"
            )
            
            response = await self.http_client.post(JITO_URL, json=payload, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Jito bundle submission error: HTTP {response.status_code} — {response.text}")
                return None
            
            result = response.json()
            bundle_id = result.get("result")
            
            if bundle_id:
                logger.info(
                    f"{Fore.LIGHTGREEN_EX}[JITO]{Style.RESET_ALL} Bundle accepted! "
                    f"Bundle ID: {Fore.CYAN}{bundle_id}{Style.RESET_ALL}"
                )
            else:
                error = result.get("error", {})
                logger.error(f"Jito bundle rejected: {error}")
            
            return bundle_id
            
        except Exception as e:
            logger.error(f"Jito bundle submission exception: {e}")
            return None

    async def build_jito_swap_bundle(
        self,
        swap1_mint_in: str, swap1_mint_out: str, swap1_amount: int,
        swap2_mint_in: str, swap2_mint_out: str, swap2_amount: int,
        tip_lamports: int = 1000
    ) -> Optional[list]:
        """
        Builds a Jito bundle containing both swap transactions + tip.
        Both swaps are fetched from Jupiter, signed, and bundled together
        for atomic execution via Jito Block Engine.
        
        Returns list of base64-encoded signed transactions, or None on failure.
        """
        JITO_TIP_ACCOUNT = "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5"
        from solders.system_program import TransferParams, transfer
        from solders.message import MessageV0
        from solders.hash import Hash
        
        try:
            # --- Swap 1: Get quote + swap transaction ---
            quote1_url = "https://api.jup.ag/swap/v1/quote"
            params1 = {
                "inputMint": swap1_mint_in,
                "outputMint": swap1_mint_out,
                "amount": str(swap1_amount),
                "slippageBps": "30"
            }
            resp1 = await self.http_client.get(quote1_url, params=params1)
            if resp1.status_code != 200:
                logger.error(f"Jupiter Quote 1 error: {resp1.text}")
                return None
            quote1 = resp1.json()
            
            swap1_url = "https://api.jup.ag/swap/v1/swap"
            payload1 = {
                "quoteResponse": quote1,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 50000
            }
            resp1_swap = await self.http_client.post(swap1_url, json=payload1)
            if resp1_swap.status_code != 200:
                logger.error(f"Jupiter Swap 1 error: {resp1_swap.text}")
                return None
            swap1_b64 = resp1_swap.json()["swapTransaction"]
            
            # --- Swap 2: Get quote + swap transaction ---
            # Use the expected output from quote1 as swap2 input
            out1_amount = quote1.get("outAmount", "0")
            params2 = {
                "inputMint": swap2_mint_in,
                "outputMint": swap2_mint_out,
                "amount": out1_amount,
                "slippageBps": "30"
            }
            resp2 = await self.http_client.get(quote1_url, params=params2)
            if resp2.status_code != 200:
                logger.error(f"Jupiter Quote 2 error: {resp2.text}")
                return None
            quote2 = resp2.json()
            
            payload2 = {
                "quoteResponse": quote2,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 50000
            }
            resp2_swap = await self.http_client.post(swap1_url, json=payload2)
            if resp2_swap.status_code != 200:
                logger.error(f"Jupiter Swap 2 error: {resp2_swap.text}")
                return None
            swap2_b64 = resp2_swap.json()["swapTransaction"]
            
            # --- Sign both transactions ---
            signed_txs = []
            for i, tx_b64 in enumerate([swap1_b64, swap2_b64]):
                raw_tx = base64.b64decode(tx_b64)
                tx = VersionedTransaction.from_bytes(raw_tx)
                sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
                signed_tx = VersionedTransaction(tx.message, [sig])
                signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                sim = await self.simulate_transaction(signed_b64)
                if not sim["ok"]:
                    logger.warning(
                        f"{Fore.YELLOW}[SIM-FAIL]{Style.RESET_ALL} "
                        f"Jito bundle leg {i+1} failed sim | Error: {sim['error']}"
                    )
                    return None
                logger.debug(
                    f"{Fore.GREEN}[SIM-OK]{Style.RESET_ALL} "
                    f"Jito bundle leg {i+1} sim passed | Units: {sim['units_consumed']}"
                )
                signed_txs.append(signed_b64)
            
            # --- Leg 3: Generate and Append physical Jito Tip Transaction ---
            blockhash_resp = await self.post_rpc({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "confirmed"}]
            })
            recent_blockhash_str = blockhash_resp.json()["result"]["value"]["blockhash"]
            recent_blockhash = Hash.from_string(recent_blockhash_str)

            ix = transfer(
                TransferParams(
                    from_pubkey=self.keypair.pubkey(),
                    to_pubkey=Pubkey.from_string(JITO_TIP_ACCOUNT),
                    lamports=tip_lamports
                )
            )
            msg = MessageV0.try_compile(
                self.keypair.pubkey(),
                [ix],
                [],
                recent_blockhash
            )
            tip_tx = VersionedTransaction(msg, [self.keypair])
            tip_sig = self.keypair.sign_message(to_bytes_versioned(tip_tx.message))
            signed_tip_tx = VersionedTransaction(tip_tx.message, [tip_sig])
            signed_tip_b64 = base64.b64encode(bytes(signed_tip_tx)).decode("utf-8")
            
            signed_txs.append(signed_tip_b64)
            
            logger.info(
                f"{Fore.LIGHTCYAN_EX}[JITO]{Style.RESET_ALL} Built bundle: "
                f"2 signed swaps + 1 Jito Tip ({tip_lamports} lamports)"
            )
            return signed_txs
            
        except Exception as e:
            logger.error(f"Error building Jito swap bundle: {e}")
            return None

    async def simulate_transaction(self, signed_tx_b64: str) -> Dict[str, Any]:
        """Simulates a signed transaction via RPC simulateTransaction before submission.
        Returns dict with keys: ok (bool), error (str|None), units_consumed (int), logs (list)
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "simulateTransaction",
            "params": [
                signed_tx_b64,
                {"encoding": "base64", "replaceRecentBlockhash": True, "sigVerify": False}
            ]
        }
        try:
            resp = await self.post_rpc(payload, timeout=15.0)
            if resp.status_code != 200:
                return {"ok": False, "error": f"HTTP {resp.status_code}", "units_consumed": 0, "logs": []}
            result = resp.json().get("result", {})
            if not result:
                err = resp.json().get("error", {}).get("message", "unknown")
                return {"ok": False, "error": err, "units_consumed": 0, "logs": []}
            sim_value = result.get("value", {})
            err = sim_value.get("err")
            if err:
                logs = sim_value.get("logs", [])
                return {"ok": False, "error": str(err), "units_consumed": sim_value.get("unitsConsumed", 0), "logs": logs}
            units = sim_value.get("unitsConsumed", 0)
            logs = sim_value.get("logs", [])
            return {"ok": True, "error": None, "units_consumed": units, "logs": logs}
        except Exception as e:
            return {"ok": False, "error": str(e), "units_consumed": 0, "logs": []}

    async def execute_live_swap(self, input_mint: str, output_mint: str, amount_raw: int) -> Optional[str]:
        """Queries Jupiter Routing API to compile, sign, and submit the swap transaction directly to Helius RPC"""
        if not self.keypair:
            logger.warning("No private key configured. Skipping live swap.")
            return None
            
        try:
            # 1. Fetch Quote
            quote_url = "https://api.jup.ag/swap/v1/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_raw),
                "slippageBps": "30"  # Tight 0.3% slippage to prevent losses from frontrunning/price drift
            }
            
            response = await self.http_client.get(quote_url, params=params)
            if response.status_code != 200:
                logger.error(f"Jupiter Quote error: {response.text}")
                return None
                
            quote_data = response.json()
            
            # 2. Get Swap Transaction Bytes
            swap_url = "https://api.jup.ag/swap/v1/swap"
            payload = {
                "quoteResponse": quote_data,
                "userPublicKey": str(self.keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 50000  # Tiny 0.00005 SOL fee to guarantee immediate landing
            }
            
            response = await self.http_client.post(swap_url, json=payload)
            if response.status_code != 200:
                logger.error(f"Jupiter Swap error: {response.text}")
                return None
                
            swap_data = response.json()
            swap_tx_b64 = swap_data["swapTransaction"]
            
            # 3. Decode & Sign Transaction
            raw_tx = base64.b64decode(swap_tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
            tx = VersionedTransaction(tx.message, [sig])

            # 3.5 Pre-swap simulation - catch failing txs before wasting gas
            signed_b64 = base64.b64encode(bytes(tx)).decode("utf-8")
            sim = await self.simulate_transaction(signed_b64)
            if not sim["ok"]:
                logger.warning(
                    f"{Fore.YELLOW}[SIM-FAIL]{Style.RESET_ALL} "
                    f"Aborting swap {input_mint[:4]}..->{output_mint[:4]}.. | "
                    f"Error: {sim['error']}"
                )
                return None
            logger.debug(
                f"{Fore.GREEN}[SIM-OK]{Style.RESET_ALL} "
                f"Swap sim passed | Units: {sim['units_consumed']}"
            )

            # 4. Submit raw transaction to public RPC (Direct Mempool execution!)
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    signed_b64,
                    {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
                ]
            }
            
            rpc_response = await self.post_rpc(rpc_payload)
            if rpc_response.status_code != 200:
                logger.error(f"RPC submission error: {rpc_response.text}")
                return None
                
            result = rpc_response.json().get("result")
            return result
        except Exception as e:
            logger.error(f"Error executing live swap: {e}")
            return None

    async def confirm_transaction(self, sig: str) -> bool:
        """Polls the RPC to confirm the transaction status"""
        logger.info(f"Verifying transaction confirmation for signature: {sig[:16]}...")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignatureStatuses",
            "params": [
                [sig],
                {"searchTransactionHistory": False}
            ]
        }
        
        # Poll every 1 second for up to 30 seconds
        for _ in range(30):
            try:
                res = await self.post_rpc(payload)
                if res.status_code == 200:
                    result = res.json().get("result", {})
                    if result and result.get("value"):
                        status = result["value"][0]
                        if status:
                            err = status.get("err")
                            if err:
                                logger.error(f"Transaction failed on-chain: {err}")
                                return False
                            confirmation_status = status.get("confirmationStatus")
                            if confirmation_status in ["confirmed", "finalized"]:
                                logger.info(f"Transaction confirmed! Status: {confirmation_status}")
                                return True
            except Exception as e:
                logger.error(f"Error checking transaction status: {e}")
            await asyncio.sleep(1)
            
        logger.warning("Transaction confirmation timeout.")
        return False

    async def execute_live_arbitrage(self, result: dict):
        """Executes the dual swap loop sequentially with verification, gas reserves, and dynamic capital recovery"""
        direction = result["direction"]
        amount_in = result["amount_in"]
        amount_in_quote = amount_in / (10 ** self.quote_decimals)
        raw_profit_quote = result["raw_profit"] / (10 ** self.quote_decimals)
        raw_profit_usd = raw_profit_quote * self.quote_usd_price
        pct = result["profit_pct"]
        
        logger.info(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}*** PROFITABLE LOOP MATCHED - EXECUTING ON-CHAIN LIVE SWAPS ***{Style.RESET_ALL}")
        logger.info(f"Target Net Profit: +${raw_profit_usd:.4f} USD ({pct:.3f}%)")
        
        QUOTE = self.quote_mint
        SOL = self.base_mint
        
        # Query start balances to verify
        start_sol, start_quote = await self.get_wallet_balances(force_refresh=True)
        logger.info(f"Starting Balances: {start_sol:.5f} SOL | {start_quote:.4f} {self.quote_symbol}")
        
        if start_quote < amount_in_quote:
            logger.error(
                f"Execution aborted: Wallet {self.quote_symbol} balance "
                f"({start_quote:.4f}) is less than required input ({amount_in_quote:.4f} {self.quote_symbol})"
            )
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, status="aborted",
                balance_before=start_quote * self.quote_usd_price, notes="Insufficient quote balance"
            )
            return

        # --- PRIMARY: Jito bundle execution (atomic, MEV-protected) ---
        logger.info(f"{Fore.LIGHTCYAN_EX}[JITO]{Style.RESET_ALL} Attempting atomic bundle execution...")
        signed_txs = await self.build_jito_swap_bundle(
            swap1_mint_in=QUOTE, swap1_mint_out=SOL, swap1_amount=amount_in,
            swap2_mint_in=SOL, swap2_mint_out=QUOTE, swap2_amount=0  # swap2 amount derived from quote1 output
        )
        if signed_txs:
            bundle_id = await self.submit_jito_bundle(signed_txs)
            if bundle_id:
                # Wait for bundle confirmation (poll balance changes)
                logger.info("Waiting for Jito bundle to land on-chain...")
                await asyncio.sleep(3)
                end_sol, end_quote = await self.get_wallet_balances(force_refresh=True)
                net_profit_usd = (end_quote - start_quote) * self.quote_usd_price
                start_quote_usd = start_quote * self.quote_usd_price
                net_pct = (net_profit_usd / start_quote_usd) * 100 if start_quote_usd > 0 else 0
                if net_profit_usd > 0:
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}Jito bundle arbitrage succeeded!{Style.RESET_ALL} "
                        f"+${net_profit_usd:.4f} USD"
                    )
                    self.trade_count += 1
                    self.profit_tracker.log_trade(
                        direction=direction, input_amount=amount_in_quote * self.quote_usd_price,
                        output_amount=end_quote * self.quote_usd_price,
                        net_profit=net_profit_usd, profit_pct=net_pct,
                        tx_sig_1=f"jito:{bundle_id}", status="executed_jito",
                        balance_before=start_quote_usd, balance_after=end_quote * self.quote_usd_price
                    )
                    self.profit_tracker.log_balance_snapshot(
                        end_sol,
                        end_quote * self.quote_usd_price,
                        self.current_sol_price
                    )
                    return
                else:
                    logger.warning(
                        f"Jito bundle landed but no profit detected (${net_profit_usd:.4f}). Falling back to sequential."
                    )
            else:
                logger.warning("Jito bundle submission failed. Falling back to sequential execution.")
        else:
            logger.warning("Jito bundle build failed. Falling back to sequential execution.")

        # --- FALLBACK: Sequential swap execution ---
            
        # Swap 1: Sell quote token for SOL (DEX 1)
        logger.info(
            f"Submitting Swap 1: Swap {amount_in_quote:.4f} {self.quote_symbol} -> SOL..."
        )
        sig1 = await self.execute_live_swap(QUOTE, SOL, amount_in)
        
        if not sig1:
            logger.error("Swap 1 submission failed. Aborting arbitrage sequence to prevent capital loss.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, status="failed",
                balance_before=start_quote * self.quote_usd_price, notes="Swap 1 submission failed"
            )
            return
            
        logger.info(f"Swap 1 submitted. Signature: {Fore.CYAN}{sig1}{Style.RESET_ALL}")
        
        # Verify Swap 1 Confirmation
        confirmed1 = await self.confirm_transaction(sig1)
        if not confirmed1:
            logger.error("Swap 1 failed to confirm on-chain or reverted. Aborting sequence to prevent loss.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, tx_sig_1=sig1, status="reverted",
                balance_before=start_quote * self.quote_usd_price, notes="Swap 1 confirmation failed"
            )
            return
            
        logger.info(f"{Fore.GREEN}Swap 1 successfully confirmed!{Style.RESET_ALL}")
        
        # Query wallet SOL balance dynamically, polling until the RPC indexer replicates Swap 1
        logger.info("Waiting for RPC balance indexer to replicate Swap 1...")
        current_sol = start_sol
        for _ in range(15):
            await asyncio.sleep(1)
            current_sol, _ = await self.get_wallet_balances(force_refresh=True)
            if current_sol > start_sol + 0.001:  # check if the SOL balance has increased
                logger.info(f"RPC balance indexer updated! New SOL balance: {current_sol:.5f} SOL")
                break
        else:
            logger.warning("Indexer sync timed out. Attempting to proceed with current reported balance.")
        
        # Calculate exactly how much SOL we bought in Swap 1 (current SOL minus the starting SOL balance)
        sol_bought = current_sol - start_sol
        # Enforce a tiny safety buffer (e.g., 0.00005 SOL) to cover signature fees without overdrawing
        sol_to_swap_raw = int(sol_bought * 1e9) - 50000
        if sol_to_swap_raw <= 0:
            logger.error(f"Abort Swap 2: SOL bought ({sol_bought:.5f} SOL) is too small to swap.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, tx_sig_1=sig1, status="partial_fail",
                balance_before=start_quote * self.quote_usd_price, notes=f"SOL bought too small: {sol_bought:.5f}"
            )
            return
            
        logger.info(f"Submitting Swap 2: Swap {sol_to_swap_raw / 1e9:.5f} SOL -> {self.quote_symbol}...")
        sig2 = await self.execute_live_swap(SOL, QUOTE, sol_to_swap_raw)
        
        if not sig2:
            logger.error("Swap 2 submission failed. Wallet holding SOL.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, tx_sig_1=sig1, status="partial_fail",
                balance_before=start_quote * self.quote_usd_price, notes="Swap 2 submission failed, holding SOL"
            )
            return
            
        logger.info(f"Swap 2 submitted. Signature: {Fore.CYAN}{sig2}{Style.RESET_ALL}")
        
        # Verify Swap 2 Confirmation
        confirmed2 = await self.confirm_transaction(sig2)
        if confirmed2:
            logger.info(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}Arbitrage sequence completed successfully!{Style.RESET_ALL}")
            # Query final balance and report profit
            end_sol, end_quote = await self.get_wallet_balances(force_refresh=True)
            logger.info(
                f"Final Balances: {end_sol:.5f} SOL | {end_quote:.4f} {self.quote_symbol}"
            )
            net_profit_usd = (end_quote - start_quote) * self.quote_usd_price
            start_quote_usd = start_quote * self.quote_usd_price
            net_pct = (net_profit_usd / start_quote_usd) * 100 if start_quote_usd > 0 else 0
            logger.info(
                f"Achieved Net Arbitrage Profit: {Fore.GREEN}+${net_profit_usd:.4f} USD{Style.RESET_ALL}"
            )
            self.trade_count += 1
            
            # Log successful trade
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price,
                output_amount=end_quote * self.quote_usd_price,
                net_profit=net_profit_usd, profit_pct=net_pct,
                tx_sig_1=sig1, tx_sig_2=sig2, status="executed",
                balance_before=start_quote_usd, balance_after=end_quote * self.quote_usd_price
            )
            # Snapshot balance after trade
            self.profit_tracker.log_balance_snapshot(
                end_sol,
                end_quote * self.quote_usd_price,
                self.current_sol_price
            )
        else:
            logger.error("Swap 2 failed or timed out. Wallet holding SOL.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_quote * self.quote_usd_price, output_amount=0,
                net_profit=0, profit_pct=0, tx_sig_1=sig1, tx_sig_2=sig2, status="swap2_failed",
                balance_before=start_quote * self.quote_usd_price, notes="Swap 2 confirmation failed"
            )


    async def execute_live_arbitrage_sol_native(self, result: dict):
        """SOL-native arbitrage: Start with SOL, swap to quote token on the first DEX, then back to SOL"""
        direction = result["direction"]
        amount_in_lamports = result["amount_in"]
        raw_profit_sol = result["raw_profit"] / 1e9
        pct = result["profit_pct"]

        QUOTE = self.quote_mint
        SOL = self.base_mint

        logger.info(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}*** SOL-NATIVE ARB - EXECUTING ON-CHAIN ***{Style.RESET_ALL}")
        logger.info(f"Direction: {direction} | Input: {amount_in_lamports / 1e9:.5f} SOL | Target Profit: +{raw_profit_sol:.6f} SOL ({pct:.3f}%)")

        start_sol, start_quote = await self.get_wallet_balances(force_refresh=True)
        logger.info(f"Starting Balances: {start_sol:.5f} SOL | {start_quote:.4f} {self.quote_symbol}")

        if start_sol < (amount_in_lamports / 1e9):
            logger.error(f"Execution aborted: Wallet SOL balance ({start_sol:.5f}) is less than required input ({amount_in_lamports / 1e9:.5f})")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                status="aborted", balance_before=start_quote * self.quote_usd_price, notes="Insufficient SOL balance"
            )
            return

        # --- PRIMARY: Jito bundle execution (atomic, MEV-protected) ---
        logger.info(f"{Fore.LIGHTCYAN_EX}[JITO]{Style.RESET_ALL} Attempting atomic SOL-native bundle execution...")
        signed_txs = await self.build_jito_swap_bundle(
            swap1_mint_in=SOL, swap1_mint_out=QUOTE, swap1_amount=amount_in_lamports,
            swap2_mint_in=QUOTE, swap2_mint_out=SOL, swap2_amount=0  # swap2 amount derived from quote1 output
        )
        if signed_txs:
            bundle_id = await self.submit_jito_bundle(signed_txs)
            if bundle_id:
                logger.info("Waiting for Jito bundle to land on-chain...")
                await asyncio.sleep(3)
                end_sol, end_quote = await self.get_wallet_balances(force_refresh=True)
                net_profit_sol = end_sol - start_sol
                net_pct = (net_profit_sol / start_sol) * 100 if start_sol > 0 else 0
                if net_profit_sol > 0:
                    logger.info(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}Jito SOL-native bundle succeeded!{Style.RESET_ALL} +{net_profit_sol:.6f} SOL")
                    self.trade_count += 1
                    self.profit_tracker.log_trade(
                        direction=direction, input_amount=amount_in_lamports / 1e9, output_amount=end_sol,
                        net_profit=net_profit_sol * self.current_sol_price, profit_pct=net_pct,
                        tx_sig_1=f"jito:{bundle_id}", status="executed_jito",
                        balance_before=start_quote * self.quote_usd_price,
                        balance_after=end_quote * self.quote_usd_price
                    )
                    self.profit_tracker.log_balance_snapshot(
                        end_sol,
                        end_quote * self.quote_usd_price,
                        self.current_sol_price
                    )
                    return
                else:
                    logger.warning(f"Jito bundle landed but no SOL profit detected ({net_profit_sol:.6f}). Falling back to sequential.")
            else:
                logger.warning("Jito bundle submission failed. Falling back to sequential execution.")
        else:
            logger.warning("Jito bundle build failed. Falling back to sequential execution.")

        # --- FALLBACK: Sequential swap execution ---
        # Swap 1: SOL -> Quote (sell SOL on the first DEX)
        logger.info(
            f"Submitting Swap 1: Swap {amount_in_lamports / 1e9:.5f} SOL -> {self.quote_symbol}..."
        )
        sig1 = await self.execute_live_swap(SOL, QUOTE, amount_in_lamports)
        if not sig1:
            logger.error("Swap 1 submission failed. Aborting SOL-native arbitrage.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                status="failed", balance_before=start_quote * self.quote_usd_price, notes="Swap 1 submission failed"
            )
            return

        logger.info(f"Swap 1 submitted. Signature: {Fore.CYAN}{sig1}{Style.RESET_ALL}")
        confirmed1 = await self.confirm_transaction(sig1)
        if not confirmed1:
            logger.error("Swap 1 failed to confirm on-chain. Aborting.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                tx_sig_1=sig1, status="reverted", balance_before=start_quote * self.quote_usd_price,
                notes="Swap 1 confirmation failed"
            )
            return

        logger.info(f"{Fore.GREEN}Swap 1 confirmed!{Style.RESET_ALL}")

        # Wait for quote balance to reflect
        logger.info("Waiting for RPC indexer to replicate Swap 1...")
        current_quote = start_quote
        for _ in range(15):
            await asyncio.sleep(1)
            _, current_quote = await self.get_wallet_balances(force_refresh=True)
            if current_quote > start_quote + 0.001:
                logger.info(f"{self.quote_symbol} balance updated! New {self.quote_symbol}: {current_quote:.4f}")
                break
        else:
            logger.warning("Indexer sync timed out. Proceeding with current reported balance.")

        quote_bought = current_quote - start_quote
        if quote_bought <= 0:
            logger.error(f"Abort Swap 2: {self.quote_symbol} bought ({quote_bought:.6f}) is too small to swap back.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                tx_sig_1=sig1, status="partial_fail", balance_before=start_quote * self.quote_usd_price,
                notes=f"{self.quote_symbol} bought too small: {quote_bought:.6f}"
            )
            return

        # Swap 2: Quote -> SOL (buy SOL back on the second DEX)
        quote_to_swap_raw = int(quote_bought * (10 ** self.quote_decimals))
        # Reserve a tiny amount for rounding
        quote_to_swap_raw = max(quote_to_swap_raw - 1, 1)

        logger.info(
            f"Submitting Swap 2: Swap {quote_to_swap_raw / (10 ** self.quote_decimals):.4f} "
            f"{self.quote_symbol} -> SOL..."
        )
        sig2 = await self.execute_live_swap(QUOTE, SOL, quote_to_swap_raw)
        if not sig2:
            logger.error(f"Swap 2 submission failed. Wallet holding {self.quote_symbol}.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                tx_sig_1=sig1, status="partial_fail", balance_before=start_quote * self.quote_usd_price,
                notes=f"Swap 2 submission failed, holding {self.quote_symbol}"
            )
            return

        logger.info(f"Swap 2 submitted. Signature: {Fore.CYAN}{sig2}{Style.RESET_ALL}")
        confirmed2 = await self.confirm_transaction(sig2)
        if confirmed2:
            logger.info(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}SOL-native arbitrage completed!{Style.RESET_ALL}")
            end_sol, end_quote = await self.get_wallet_balances(force_refresh=True)
            net_profit_sol = end_sol - start_sol
            net_pct = (net_profit_sol / start_sol) * 100 if start_sol > 0 else 0
            logger.info(f"Achieved Net Profit: {Fore.GREEN}+{net_profit_sol:.6f} SOL{Style.RESET_ALL} (${net_profit_sol * self.current_sol_price:.4f} USD)")
            self.trade_count += 1
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=end_sol, net_profit=net_profit_sol * self.current_sol_price,
                profit_pct=net_pct, tx_sig_1=sig1, tx_sig_2=sig2,
                status="executed", balance_before=start_quote * self.quote_usd_price,
                balance_after=end_quote * self.quote_usd_price
            )
            self.profit_tracker.log_balance_snapshot(end_sol, end_quote * self.quote_usd_price, self.current_sol_price)
        else:
            logger.error(f"Swap 2 failed or timed out. Wallet holding {self.quote_symbol}.")
            self.profit_tracker.log_trade(
                direction=direction, input_amount=amount_in_lamports / 1e9,
                output_amount=0, net_profit=0, profit_pct=0,
                tx_sig_1=sig1, tx_sig_2=sig2, status="swap2_failed",
                balance_before=start_quote * self.quote_usd_price, notes="Swap 2 confirmation failed"
            )


    async def get_wallet_balances(self, force_refresh: bool = False) -> tuple[float, float]:
        """Queries the RPC to fetch SOL and quote-token balances for the loaded keypair, utilizing caching to prevent RPC rate-limits"""
        if not self.keypair:
            return 0.0, 0.0
        
        now = time.time()
        if force_refresh or (now - self.last_balance_update > 30):
            pubkey_str = str(self.keypair.pubkey())
            sol_balance = 0.0
            quote_balance = 0.0
            
            # 1. Fetch SOL Balance
            sol_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [pubkey_str]
            }
            
            # 2. Fetch USDC Balance
            quote_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "getTokenAccountsByOwner",
                "params": [
                    pubkey_str,
                    {"mint": self.quote_mint},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            try:
                # Fetch SOL
                res = await self.post_rpc(sol_payload)
                if res.status_code == 200:
                    val = res.json().get("result", {}).get("value", 0)
                    sol_balance = val / 1e9  # 9 decimals for SOL
                    
                # Fetch quote token
                res = await self.post_rpc(quote_payload)
                if res.status_code == 200:
                    accounts = res.json().get("result", {}).get("value", [])
                    if accounts:
                        account_info = accounts[0]["account"]["data"]["parsed"]["info"]
                        quote_balance = float(account_info["tokenAmount"]["uiAmount"])
                
                self.cached_sol_bal = sol_balance
                self.cached_usdc_bal = quote_balance
                self.last_balance_update = now
            except Exception as e:
                logger.error(f"Error fetching wallet balances: {e}")
                
        return self.cached_sol_bal, self.cached_usdc_bal

    async def check_for_opportunity(self):
        """Evaluates arbitrage yields with micro-strategy filtering — checks both quote-native and SOL-native paths"""
        await self.update_token_prices()
        if self.keypair:
            sol_bal, quote_bal = await self.get_wallet_balances()
            quote_balance_usd = quote_bal * self.quote_usd_price if self.quote_usd_price > 0 else 0.0
            # Build candidate trade sizes for both paths
            quote_sizes = []
            sol_sizes = []
            if quote_balance_usd >= 0.10:
                quote_sizes.append(int(quote_bal * (10 ** self.quote_decimals)))
            elif self.quote_usd_price > 0:
                min_quote = 0.10 / self.quote_usd_price
                min_quote_raw = int(min_quote * (10 ** self.quote_decimals))
                quote_sizes.append(max(min_quote_raw, 1))
            if sol_bal >= 0.005:  # Need at least 0.005 SOL for fees
                sol_lamports = int(sol_bal * 1e9) - 50000  # Reserve for fees
                if sol_lamports > 0:
                    sol_sizes.append(sol_lamports)
        else:
            quote_sizes = [100_000_000, 500_000_000, 1000_000_000, 5000_000_000]
            sol_sizes = [50_000_000, 200_000_000, 500_000_000, 2000_000_000]

        best_result = None
        best_profit_usd = 0.0

        # --- Quote-native path: Quote -> SOL on DEX1 -> Quote on DEX2 ---
        for test_amount in quote_sizes:
            res = check_arbitrage_mixed(
                self.raydium_state,
                self.raydium_active_kind,
                self.orca_state,
                test_amount
            )
            if res.get("profitable"):
                profit_usd = (res["raw_profit"] / (10 ** self.quote_decimals)) * self.quote_usd_price
                if profit_usd > best_profit_usd:
                    best_profit_usd = profit_usd
                    best_result = res
            break  # Only test the one real size

        # --- SOL-native path: SOL -> USDC on DEX1 -> SOL on DEX2 ---
        for test_amount in sol_sizes:
            res_sol = check_arbitrage_sol_native_mixed(
                self.raydium_state,
                self.raydium_active_kind,
                self.orca_state,
                test_amount
            )
            if res_sol.get("profitable"):
                # Convert SOL profit to USDC equivalent for comparison
                profit_usd_equiv = (res_sol["raw_profit"] / 1e9) * self.current_sol_price
                if profit_usd_equiv > best_profit_usd:
                    best_profit_usd = profit_usd_equiv
                    best_result = res_sol
            break

        if best_result and best_result.get("profitable"):
            self.opportunity_count += 1
            is_sol_native = best_result.get("input_type") == "SOL"

            if self.keypair:
                evaluation = evaluate_opportunity(
                    arb_result=best_result,
                    usdc_balance=quote_balance_usd,
                    sol_balance=sol_bal,
                    sol_price=self.current_sol_price,
                    spike_detector=self.spike_detector,
                    quote_decimals=self.quote_decimals,
                    quote_usd_price=self.quote_usd_price
                )
                if evaluation["should_trade"]:
                    logger.info(f"{Fore.LIGHTGREEN_EX}[APPROVED]{Style.RESET_ALL} {evaluation['reason']}")
                    if is_sol_native:
                        await self.execute_live_arbitrage_sol_native(best_result)
                    else:
                        await self.execute_live_arbitrage(best_result)
                else:
                    if is_sol_native:
                        input_amount_usd = (best_result["amount_in"] / 1e9) * self.current_sol_price
                        expected_profit_usd = (best_result["raw_profit"] / 1e9) * self.current_sol_price
                    else:
                        input_amount_usd = (best_result["amount_in"] / (10 ** self.quote_decimals)) * self.quote_usd_price
                        expected_profit_usd = (best_result["raw_profit"] / (10 ** self.quote_decimals)) * self.quote_usd_price
                    self.profit_tracker.log_skipped_opportunity(
                        direction=best_result.get("direction", "unknown"),
                        input_amount=input_amount_usd,
                        expected_profit=expected_profit_usd,
                        profit_pct=best_result["profit_pct"],
                        spread_pct=best_result["profit_pct"],
                        reason=evaluation["reason"]
                    )
                    logger.info(
                        f"{Fore.YELLOW}[FILTERED]{Style.RESET_ALL} Tier: {Fore.CYAN}{evaluation['tier']}{Style.RESET_ALL} | "
                        f"{evaluation['reason']}"
                    )
            else:
                await self.execute_dry_run_arbitrage(best_result)

    async def run_heartbeat_loop(self):
        """Prints a visual confirmation every 60 seconds showing the socket is alive and tracking prices"""
        while self.running:
            await asyncio.sleep(60)
            if self.orca_state["sqrt_price"] > 0:
                r_price = self._get_raydium_price()
                o_price = (self.orca_state["sqrt_price"] / (2**64)) ** 2 * 1000
                if r_price <= 0:
                    continue
                spread = abs(r_price - o_price)
                spread_pct = (spread / r_price) * 100
                
                # Update cached SOL price for micro-strategy calculations
                self.current_sol_price = r_price
                
                # Get balance tier info for display (include SOL value for accurate tier)
                tier = get_balance_tier(self.cached_usdc_bal, self.cached_sol_bal, self.current_sol_price)
                spike_stats = self.spike_detector.get_stats()
                
                logger.info(
                    f"{Fore.LIGHTBLACK_EX}[WS-HEARTBEAT]{Style.RESET_ALL} Monitoring active... "
                    f"Raydium SOL: {Fore.YELLOW}${r_price:.4f}{Style.RESET_ALL} | "
                    f"Orca SOL: {Fore.YELLOW}${o_price:.4f}{Style.RESET_ALL} | "
                    f"Spread: {Fore.GREEN}{spread_pct:.4f}%{Style.RESET_ALL} | "
                    f"Tier: {Fore.CYAN}{tier}{Style.RESET_ALL} | "
                    f"Opps: {Fore.YELLOW}{self.opportunity_count}{Style.RESET_ALL} | "
                    f"Trades: {Fore.GREEN}{self.trade_count}{Style.RESET_ALL}"
                )
                
                # Print hourly profit summary
                self.profit_tracker.print_summary()

    async def run_ws_listener(self):
        """Subscribes and listens to pool changes in real-time"""
        url = self.wss_urls[self.current_wss_idx]
        logger.info(f"[{self.pair_name}] Connecting to Helius WebSocket Stream at {url[:35]}...")
        
        async with websockets.connect(url) as ws:
            logger.info("Connected! Subscribing to Concentrated Liquidity pools...")

            subscribe_entries: List[Dict[str, Any]] = []
            for pool_id in self.raydium_pool_ids:
                subscribe_entries.append({
                    "address": pool_id,
                    "kind": "pool",
                    "dex": "raydium",
                    "pool_id": pool_id
                })
            for pool_id in self.orca_pool_ids:
                subscribe_entries.append({
                    "address": pool_id,
                    "kind": "pool",
                    "dex": "orca",
                    "pool_id": pool_id
                })
            for vault_addr, meta in self.raydium_amm_vault_map.items():
                subscribe_entries.append({
                    "address": vault_addr,
                    "kind": "vault",
                    "dex": "raydium",
                    "pool_id": meta["pool_id"],
                    "side": meta["side"]
                })

            if not subscribe_entries:
                logger.error("No pools available for WebSocket subscription.")
                return

            pending_subscriptions: Dict[int, Dict[str, Any]] = {}
            subscription_map: Dict[int, Dict[str, Any]] = {}

            for idx, entry in enumerate(subscribe_entries):
                req_id = idx + 1
                pending_subscriptions[req_id] = entry
                payload = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": "accountSubscribe",
                    "params": [
                        entry["address"],
                        {"encoding": "base64", "commitment": "processed"}
                    ]
                }
                await ws.send(json.dumps(payload))
                logger.info(f"Subscribed to: {Fore.YELLOW}{entry['address'][:12]}...{Style.RESET_ALL}")

            # Listen to updates
            async for message in ws:
                event = json.loads(message)
                if "params" not in event:
                    if "id" in event and "result" in event:
                        entry = pending_subscriptions.pop(event["id"], None)
                        if entry:
                            subscription_map[event["result"]] = entry
                    continue

                params = event["params"]
                sub_id = params.get("subscription")
                entry = subscription_map.get(sub_id)
                if not entry:
                    continue

                value = params["result"]["value"]
                data_b64 = value["data"][0]
                raw_bytes = base64.b64decode(data_b64)

                price_changed = False
                try:
                    if entry["kind"] == "vault":
                        amount_raw = parse_spl_token_account(raw_bytes)
                        price_changed = self._apply_amm_vault_update(
                            entry["pool_id"],
                            entry["side"],
                            amount_raw
                        )
                    elif entry["dex"] == "raydium":
                        pool_id = entry["pool_id"]
                        pool_kind = self.raydium_pool_kind_by_id.get(pool_id)
                        if pool_kind == "amm_v4" or len(raw_bytes) == 752:
                            amm_state = parse_raydium_amm_v4(raw_bytes)
                            base_vault = self._hex_to_pubkey(amm_state["base_vault"])
                            quote_vault = self._hex_to_pubkey(amm_state["quote_vault"])
                            base_mint = self._hex_to_pubkey(amm_state["base_mint"])
                            quote_mint = self._hex_to_pubkey(amm_state["quote_mint"])

                            if self._mints_match(base_mint, quote_mint, self.base_mint, self.quote_mint):
                                amm_state["base_vault"] = base_vault
                                amm_state["quote_vault"] = quote_vault
                                amm_state["base_mint"] = base_mint
                                amm_state["quote_mint"] = quote_mint

                                existing = self.raydium_pools.get(pool_id, {})
                                amm_state["reserve_base"] = existing.get("reserve_base", 0)
                                amm_state["reserve_quote"] = existing.get("reserve_quote", 0)
                                amm_state["liquidity"] = existing.get("liquidity", 0)

                                self.raydium_pools[pool_id] = amm_state
                                self.raydium_pool_kind_by_id[pool_id] = "amm_v4"

                                if base_vault not in self.raydium_amm_vault_map:
                                    self.raydium_amm_vault_map[base_vault] = {"pool_id": pool_id, "side": "base"}
                                if quote_vault not in self.raydium_amm_vault_map:
                                    self.raydium_amm_vault_map[quote_vault] = {"pool_id": pool_id, "side": "quote"}

                                price_changed = self._apply_pool_update("raydium", pool_id, amm_state)
                        else:
                            new_state = parse_raydium_clmm(raw_bytes)
                            self.raydium_pool_kind_by_id[pool_id] = "clmm"
                            price_changed = self._apply_pool_update("raydium", pool_id, new_state)
                    elif entry["dex"] == "orca":
                        pool_id = entry["pool_id"]
                        new_state = parse_orca_whirlpool(raw_bytes)
                        price_changed = self._apply_pool_update("orca", pool_id, new_state)
                except Exception as e:
                    logger.debug(f"Failed to parse pool update {entry['address'][:12]}..: {e}")
                    continue

                if price_changed and self.orca_state.get("sqrt_price", 0) > 0:
                    r_price = self._get_raydium_price()
                    o_price = (self.orca_state["sqrt_price"] / (2**64)) ** 2 * 1000
                    if r_price <= 0:
                        continue
                    self.pair_price = r_price
                    if self.quote_symbol.upper() in ("USDC", "USDT"):
                        self.current_sol_price = r_price
                    else:
                        await self.update_token_prices()

                    # Feed spread to spike detector for statistical tracking
                    spread_pct = abs(r_price - o_price) / r_price * 100
                    self.spike_detector.record_spread(spread_pct)

                    logger.debug(
                        f"Pool Price Update ({self.pair_name}) | Raydium SOL: {Fore.CYAN}{r_price:.6f}{Style.RESET_ALL} | "
                        f"Orca SOL: {Fore.CYAN}{o_price:.6f}{Style.RESET_ALL}"
                    )
                    await self.check_for_opportunity()

    async def run_jup_scanner(self):
        """Jupiter Quote-Based Arbitrage Scanner — polls Jupiter every few seconds for round-trip and triangle arb"""
        logger.info(
            f"{Fore.LIGHTCYAN_EX}[JUP-SCANNER]{Style.RESET_ALL} "
            f"Starting Jupiter multi-path arbitrage scanner (interval: {self.jup_scan_interval}s)..."
        )

        # Warmup: let WebSocket connections and token sniper settle first
        await asyncio.sleep(10)

        while self.running and self.jup_enabled:
            try:
                # Update Jupiter engine's SOL price
                self.jup_arb.update_sol_price(self.current_sol_price)

                if not self.keypair:
                    await asyncio.sleep(self.jup_scan_interval)
                    continue

                sol_bal, quote_bal = await self.get_wallet_balances()
                usdc_raw = int(quote_bal * (10 ** self.quote_decimals))
                sol_lamports = int(sol_bal * 1e9)

                # Run the full scan: round-trip + all triangles
                best = await self.jup_arb.scan_all_opportunities(usdc_raw, sol_lamports)

                if best and best.get("profitable"):
                    net_profit_usd = best.get("net_profit_usd", 0)
                    direction = best.get("direction", "unknown")

                    # Gas cost threshold — must exceed gas to be worth executing
                    gas_cost_usd = 0.001  # ~$0.001 per Jupiter swap tx
                    if net_profit_usd < gas_cost_usd:
                        logger.debug(f"[JUP-SCANNER] Profit ${net_profit_usd:.6f} below gas threshold")
                        await asyncio.sleep(self.jup_scan_interval)
                        continue

                    self.opportunity_count += 1
                    logger.info(
                        f"{Fore.LIGHTGREEN_EX}[JUP-OPPORTUNITY]{Style.RESET_ALL} "
                        f"{direction} | Net: {Fore.GREEN}+${net_profit_usd:.6f}{Style.RESET_ALL} | "
                        f"Profit: {best.get('profit_pct', 0):.4f}%"
                    )

                    # Execute the profitable path
                    is_triangle = "_SOL_" in direction and direction.count("_") >= 3
                    is_sol_native = best.get("input_type") == "SOL"

                    if is_triangle:
                        # For triangles, we execute as 3 sequential swaps
                        # Jupiter handles routing — we just need to execute each leg
                        mid_token = best.get("mid_token_mint")
                        if mid_token:
                            logger.info(
                                f"{Fore.LIGHTCYAN_EX}[JUP-EXECUTE]{Style.RESET_ALL} "
                                f"Executing triangle arb: {direction}"
                            )
                            # Leg 1
                            sig1 = await self.execute_live_swap(
                                USDC_MINT, SOL_MINT, best["amount_in"]
                            )
                            if sig1:
                                confirmed = await self.confirm_transaction(sig1)
                                if confirmed:
                                    # Get intermediate SOL balance
                                    await asyncio.sleep(2)
                                    new_sol, _ = await self.get_wallet_balances(force_refresh=True)
                                    sol_for_leg2 = int((new_sol - sol_bal) * 1e9) - 50000
                                    if sol_for_leg2 > 0:
                                        # Leg 2: SOL → TOKEN
                                        sig2 = await self.execute_live_swap(
                                            SOL_MINT, mid_token, sol_for_leg2
                                        )
                                        if sig2:
                                            confirmed2 = await self.confirm_transaction(sig2)
                                            if confirmed2:
                                                await asyncio.sleep(2)
                                                # Leg 3: TOKEN → USDC
                                                # Get token balance
                                                tok_payload = {
                                                    "jsonrpc": "2.0", "id": 1,
                                                    "method": "getTokenAccountsByOwner",
                                                    "params": [
                                                        str(self.keypair.pubkey()),
                                                        {"mint": mid_token},
                                                        {"encoding": "jsonParsed"}
                                                    ]
                                                }
                                                tok_resp = await self.post_rpc(tok_payload)
                                                if tok_resp.status_code == 200:
                                                    tok_accounts = tok_resp.json().get("result", {}).get("value", [])
                                                    if tok_accounts:
                                                        tok_amount = int(tok_accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
                                                        if tok_amount > 0:
                                                            sig3 = await self.execute_live_swap(
                                                                mid_token, USDC_MINT, tok_amount
                                                            )
                                                            if sig3:
                                                                confirmed3 = await self.confirm_transaction(sig3)
                                                                if confirmed3:
                                                                    end_sol, end_usdc = await self.get_wallet_balances(force_refresh=True)
                                                                    actual_profit = (end_usdc - quote_bal) * self.quote_usd_price
                                                                    self.trade_count += 1
                                                                    logger.info(
                                                                        f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}"
                                                                        f"TRIANGLE ARB COMPLETED!{Style.RESET_ALL} "
                                                                        f"Net: {Fore.GREEN}+${actual_profit:.4f}{Style.RESET_ALL}"
                                                                    )
                                                                    self.profit_tracker.log_trade(
                                                                        direction=direction,
                                                                        input_amount=best["amount_in"] / 1e6,
                                                                        output_amount=end_usdc,
                                                                        net_profit=actual_profit,
                                                                        profit_pct=best["profit_pct"],
                                                                        tx_sig_1=sig1,
                                                                        tx_sig_2=sig3,
                                                                        status="executed_triangle",
                                                                        balance_before=quote_bal,
                                                                        balance_after=end_usdc,
                                                                    )
                    elif is_sol_native:
                        await self.execute_live_arbitrage_sol_native(best)
                    else:
                        await self.execute_live_arbitrage(best)

            except Exception as e:
                logger.error(f"[JUP-SCANNER] Error: {e}")

            await asyncio.sleep(self.jup_scan_interval)

    async def start(self):
        """Main runner supervisor with auto-reconnect logic"""
        print(f"""
{Fore.CYAN}{Style.BRIGHT}========================================================================
             SOLANA 24/7 HIGH-FREQUENCY ARBITRAGE BOT
             Jupiter Multi-Path + Pool Monitor + Token Sniper
               Designed by cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
""")
        init_ok = await self.get_initial_states()
        if not init_ok:
            logger.error(f"[{self.pair_name}] Could not fetch initial states. Bot for this pair is stopping.")
            return
            
        if self.keypair:
            sol_bal, usdc_bal = await self.get_wallet_balances()
            logger.info(f"Loaded Wallet: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            logger.info(f"Current Balance: {Fore.YELLOW}{sol_bal:.5f} SOL{Style.RESET_ALL} | {Fore.YELLOW}${usdc_bal:.2f} USDC{Style.RESET_ALL}")
            if usdc_bal < 0.10:
                logger.info(f"{Fore.YELLOW}Low USDC — Jupiter scanner + SOL-native arb will handle this.{Style.RESET_ALL}")
            if sol_bal < 0.005:
                logger.warning(f"{Fore.RED}Very low SOL balance! Need at least ~0.005 SOL for tx fees.{Style.RESET_ALL}")
            
        logger.info("Starting WS monitor + Jupiter scanner...")
        
        # Start the background loops
        self.running = True
        asyncio.create_task(self.run_heartbeat_loop())
        asyncio.create_task(self.run_jup_scanner())
        
        while True:
            try:
                await self.run_ws_listener()
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[{self.pair_name}] WebSocket connection dropped: {e}. Rotating to backup WSS and reconnecting in 5s...")
                self.current_wss_idx = (self.current_wss_idx + 1) % len(self.wss_urls)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[{self.pair_name}] WebSocket supervisor encountered crash: {e}. Rotating to backup WSS and reconnecting in 5s...")
                self.current_wss_idx = (self.current_wss_idx + 1) % len(self.wss_urls)
                await asyncio.sleep(5)

async def run_all_engines():
    """
    Master entry point — runs all three engines concurrently:
    1. SOL/USDC Arb Bot (WebSocket pool monitor + Jupiter scanner)
    2. Token Launch Sniper (new pool detection + micro-buy)
    
    With Jupiter quotes, a single bot instance covers ALL DEX paths.
    No need for multi-pair instances anymore.
    """
    logger.info(
        f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}"
        f"Initializing all trading engines..."
        f"{Style.RESET_ALL}"
    )

    global_profit_tracker = ProfitTracker()

    # Engine 1: Core arb bot (SOL/USDC pool monitor + Jupiter scanner)
    arb_bot = SolanaArbBot(
        quote_mint=USDC_MINT,
        quote_symbol="USDC",
        quote_decimals=6,
        pair_name="SOL/USDC",
        profit_tracker=global_profit_tracker,
    )

    # Engine 2: Pump.fun Token Sniper (PRIMARY PROFIT ENGINE)
    pump_sniper = PumpFunSniper(
        max_snipe_sol=float(os.getenv("MAX_SNIPE_SOL", "0.005")),      # Size per snipe
        take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "100.0")),  # Profit target
        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "30.0")),       # Trailing SL
        timeout_secs=float(os.getenv("TIMEOUT_SECS", "20.0")),         # Timeout scalp
        max_concurrent=int(os.getenv("MAX_CONCURRENT", "1")),          # Strict concurrency limit
        dry_run=os.getenv("DRY_RUN", "True").lower() == "true",        # Live/Dry toggle
    )

    # Engine 3: Copy Trader (mirror profitable wallets)
    copy_engine = CopyTrader(
        max_trade_sol=0.001,      # Micro-size to match balance
        take_profit_pct=50.0,
        stop_loss_pct=25.0,
        timeout_secs=300.0,
        max_concurrent_positions=3,
        dry_run=True,             # Keep dry run — pump sniper is primary
    )

    # Capital allocator: prevents engines from competing for the same funds
    sol_bal = usdc_bal = 0.0
    if arb_bot.keypair:
        sol_bal, usdc_bal = await arb_bot.get_wallet_balances()
    allocator = CapitalAllocator(total_sol=sol_bal, total_usdc=usdc_bal)

    async def run_arb_safe():
        try:
            await arb_bot.start()
        except Exception as e:
            logger.error(f"Arb bot crashed: {e}")

    async def run_pump_sniper_safe():
        try:
            await pump_sniper.run()
        except Exception as e:
            logger.error(f"Pump.fun sniper crashed: {e}")

    async def run_copy_trader_safe():
        try:
            await copy_engine.run()
        except Exception as e:
            logger.error(f"Copy trader crashed: {e}")

    # Engine 4: Quantitative Data Collector Loop
    db_mgr = DatabaseManager()
    collector = DataCollector(
        rpc_wss=os.getenv("HELIUS_WSS_URL", WSS_URL),
        rpc_http=os.getenv("HELIUS_RPC_URL", RPC_URL),
        db_manager=db_mgr
    )
    async def run_collector_safe():
        try:
            logger.info("Starting Quantitative Data Collector Suite in background...")
            await collector.run()
        except Exception as e:
            logger.error(f"Quantitative Data Collector crashed: {e}")

    logger.info(
        f"{Fore.GREEN}Launching engines:{Style.RESET_ALL}\n"
        f" 1. SOL/USDC Pool Monitor + Jupiter Scanner (background)\n"
        f" 2. {Fore.LIGHTMAGENTA_EX}Pump.fun Token Sniper{Style.RESET_ALL} (PRIMARY — dry run)\n"
        f" 3. {Fore.LIGHTBLUE_EX}Copy Trader{Style.RESET_ALL} (wallet mirror — dry run)\n"
    )

    # Top-level circuit breaker: halt all engines if daily loss limit is breached
    async def _circuit_breaker():
        daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT_USD", "50.0"))
        while True:
            await asyncio.sleep(30)
            if global_profit_tracker.should_halt_trading(daily_loss_limit_usd=daily_loss_limit):
                logger.critical(
                    f"{Fore.RED}[CIRCUIT-BREAKER]{Style.RESET_ALL} "
                    f"Daily loss limit breached. Stopping all engines."
                )
                pump_sniper.running = False
                arb_bot.running = False
                copy_engine.running = False
                break

    await asyncio.gather(
        run_arb_safe(),
        run_pump_sniper_safe(),
        run_copy_trader_safe(),
        run_collector_safe(),
        _circuit_breaker(),
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_all_engines())
    except KeyboardInterrupt:
        print("\n[!] Solana Bot stopped cleanly by user.")
