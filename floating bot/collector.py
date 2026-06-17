#!/usr/bin/env python3
"""
Quantitative Data Collector Suite — High-Performance Market & Trade Scraping
cook45 & clack // Systems & MEV

Establishes an optimized SQLite WAL database and collects:
1. Token Launches (Raydium V4, CPMM, Pump.fun)
2. Real-Time Swaps (Log parsed logs for wallet profiling)
"""

import os
import sys
import json
import asyncio
import sqlite3
import time
import logging
import httpx
import websockets
from typing import Dict, Any, Optional, List, Tuple
from colorama import Fore, Style, init

init(autoreset=True)

# Logger
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.LIGHTBLACK_EX}[%(asctime)s] [COLLECTOR]{Style.RESET_ALL} %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Collector")

SOL_MINT = "So11111111111111111111111111111111111111112"
RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

class DatabaseManager:
    """Optimized SQLite WAL Database Manager for High-Frequency Quantitative Data"""
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for high-frequency concurrent writes
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB Cache
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Tokens Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            mint_address TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT,
            creator_wallet TEXT,
            launch_time REAL,
            initial_sol_reserves REAL,
            migrated INTEGER DEFAULT 0,
            peak_market_cap REAL DEFAULT 0,
            final_market_cap REAL DEFAULT 0,
            is_rug INTEGER DEFAULT 0
        );
        """)
        
        # 2. Raw Swaps Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_swaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT,
            mint_address TEXT,
            direction TEXT, -- BUY / SELL
            amount_sol REAL,
            amount_token REAL,
            price_sol_token REAL,
            slot INTEGER,
            timestamp REAL,
            signature TEXT
        );
        """)
        
        # 3. Wallets Intelligence Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets_intel (
            wallet_address TEXT PRIMARY KEY,
            first_seen REAL,
            total_trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            realized_pnl REAL DEFAULT 0,
            avg_roi REAL DEFAULT 0,
            migration_participation REAL DEFAULT 0,
            rug_participation REAL DEFAULT 0,
            wallet_score REAL DEFAULT 0,
            cluster_id TEXT
        );
        """)
        
        # 4. Wallet Clusters Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet_clusters (
            cluster_id TEXT PRIMARY KEY,
            wallets TEXT, -- JSON Array of wallets
            creation_time REAL,
            cabal_score REAL DEFAULT 0
        );
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_swaps_wallet ON raw_swaps(wallet_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_swaps_mint ON raw_swaps(mint_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_swaps_slot ON raw_swaps(slot);")
        
        conn.commit()
        conn.close()
        logger.info(f"SQLite WAL Database initialized: {Fore.GREEN}{self.db_path}{Style.RESET_ALL}")

    def save_token(self, token_data: Dict[str, Any]):
        conn = self.get_connection()
        try:
            conn.execute("""
            INSERT OR REPLACE INTO tokens 
            (mint_address, symbol, name, creator_wallet, launch_time, initial_sol_reserves, migrated)
            VALUES (:mint, :symbol, :name, :creator, :launch_time, :initial_sol, :migrated)
            """, token_data)
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving token to db: {e}")
        finally:
            conn.close()

    def save_swap(self, swap_data: Dict[str, Any]):
        conn = self.get_connection()
        try:
            conn.execute("""
            INSERT INTO raw_swaps 
            (wallet_address, mint_address, direction, amount_sol, amount_token, price_sol_token, slot, timestamp, signature)
            VALUES (:wallet, :mint, :direction, :sol, :token, :price, :slot, :timestamp, :signature)
            """, swap_data)
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving swap to db: {e}")
        finally:
            conn.close()


class DataCollector:
    """Manages Concurrent WebSocket subscriptions for Token Launches & Trade transactions"""
    def __init__(self, rpc_wss: str, rpc_http: str, db_manager: DatabaseManager):
        self.rpc_wss = rpc_wss
        self.rpc_http = rpc_http
        self.db = db_manager
        self.running = False
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def _fetch_transaction_details(self, signature: str) -> Optional[Dict[str, Any]]:
        """Query RPC for detailed JSON parsed transaction state"""
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        try:
            # Let it index for 1s
            await asyncio.sleep(1.0)
            resp = await self.http_client.post(self.rpc_http, json=payload, timeout=8.0)
            if resp.status_code == 200:
                return resp.json().get("result")
        except Exception:
            pass
        return None

    async def launch_collector_loop(self):
        """Websocket monitor subscribing to Raydium pool initialization events"""
        while self.running:
            try:
                async with websockets.connect(self.rpc_wss) as ws:
                    subscribe_payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method": "logsSubscribe",
                        "params": [
                            {"mentions": [RAYDIUM_AMM_PROGRAM]},
                            {"commitment": "processed"}
                        ]
                    }
                    await ws.send(json.dumps(subscribe_payload))
                    logger.info(f"Subscribed to Raydium Pool Log creations. Scanning launches...")

                    async for message in ws:
                        if not self.running:
                            break
                        try:
                            event = json.loads(message)
                            if "params" not in event:
                                continue
                            
                            value = event["params"]["result"]["value"]
                            logs = value.get("logs", [])
                            sig = value.get("signature")
                            slot = value.get("slot")

                            is_init = any("initialize2" in l.lower() for l in logs)
                            if not is_init:
                                continue

                            logger.info(f"New pool log matched: {Fore.YELLOW}{sig[:16]}...{Style.RESET_ALL}")
                            asyncio.create_task(self._process_new_pool(sig, slot))
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Launch collector disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _process_new_pool(self, signature: str, slot: int):
        tx_data = await self._fetch_transaction_details(signature)
        if not tx_data:
            return

        # Extract token mints from balances
        meta = tx_data.get("meta", {})
        token_mints = set()
        for bal in meta.get("postTokenBalances", []):
            mint = bal.get("mint")
            if mint and mint != SOL_MINT:
                token_mints.add(mint)

        for mint in token_mints:
            token_data = {
                "mint": mint,
                "symbol": mint[:6].upper(),
                "name": f"Hormuz_{mint[:4]}",
                "creator": "Unknown",
                "launch_time": time.time(),
                "initial_sol": 1.0,  # Estimated fallback
                "migrated": 0
            }
            self.db.save_token(token_data)
            logger.info(f"Saved launch data for: {Fore.LIGHTCYAN_EX}{mint}{Style.RESET_ALL}")

    async def trade_collector_loop(self):
        """WebSocket monitor subscribing to trade swaps for profiling wallet intelligence"""
        while self.running:
            try:
                async with websockets.connect(self.rpc_wss) as ws:
                    # Mentions pump.fun program to profile meme token traders
                    subscribe_payload = {
                        "jsonrpc": "2.0", "id": 1,
                        "method": "logsSubscribe",
                        "params": [
                            {"mentions": [PUMP_PROGRAM]},
                            {"commitment": "processed"}
                        ]
                    }
                    await ws.send(json.dumps(subscribe_payload))
                    logger.info(f"Subscribed to trade swap logs. Profiling wallet data...")

                    async for message in ws:
                        if not self.running:
                            break
                        try:
                            event = json.loads(message)
                            if "params" not in event:
                                continue
                            
                            value = event["params"]["result"]["value"]
                            logs = value.get("logs", [])
                            sig = value.get("signature")
                            slot = value.get("slot")

                            is_trade = any("buy" in l.lower() or "sell" in l.lower() for l in logs)
                            if not is_trade:
                                continue

                            asyncio.create_task(self._process_trade_log(sig, slot))
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Trade collector disconnected: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _process_trade_log(self, signature: str, slot: int):
        tx_data = await self._fetch_transaction_details(signature)
        if not tx_data:
            return

        meta = tx_data.get("meta", {})
        transaction = tx_data.get("transaction", {})
        message = transaction.get("message", {})
        account_keys = message.get("accountKeys", [])

        # Get Signer (feepayer at 0)
        if not account_keys:
            return
        
        signer = account_keys[0]
        if isinstance(signer, dict):
            signer = signer.get("pubkey")

        # Check token balance differences
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])

        for post in post_balances:
            mint = post.get("mint")
            if not mint or mint == SOL_MINT:
                continue

            owner = post.get("owner")
            if owner != signer:
                continue

            # Find matching pre balance
            pre_amt = 0.0
            for pre in pre_balances:
                if pre.get("mint") == mint and pre.get("owner") == owner:
                    pre_amt = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
                    break
            
            post_amt = float(post.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
            diff_tokens = post_amt - pre_amt

            if diff_tokens == 0:
                continue

            direction = "BUY" if diff_tokens > 0 else "SELL"
            
            # Simple SOL fee/amount extraction from balances
            pre_sol = meta.get("preBalances", [0])[0] / 1e9
            post_sol = meta.get("postBalances", [0])[0] / 1e9
            diff_sol = abs(post_sol - pre_sol)

            price = diff_sol / abs(diff_tokens) if diff_tokens != 0 else 0.0

            swap_data = {
                "wallet": owner,
                "mint": mint,
                "direction": direction,
                "sol": diff_sol,
                "token": abs(diff_tokens),
                "price": price,
                "slot": slot,
                "timestamp": time.time(),
                "signature": signature
            }
            
            self.db.save_swap(swap_data)
            logger.info(
                f"Swap: {Fore.LIGHTBLUE_EX}{owner[:8]}...{Style.RESET_ALL} | "
                f"{Fore.GREEN if direction=='BUY' else Fore.RED}{direction}{Style.RESET_ALL} "
                f"{abs(diff_tokens):,.2f} of {mint[:8]}.. for {diff_sol:.4f} SOL"
            )

    async def run(self):
        self.running = True
        await asyncio.gather(
            self.launch_collector_loop(),
            self.trade_collector_loop()
        )

# CLI tester
if __name__ == "__main__":
    db = DatabaseManager()
    
    # Load settings from workspace .env
    from dotenv import load_dotenv
    load_dotenv()
    
    rpc_http = os.getenv("HELIUS_RPC_URL", "https://api.mainnet-beta.solana.com")
    rpc_wss = os.getenv("HELIUS_WSS_URL", "wss://api.mainnet-beta.solana.com")
    
    collector = DataCollector(rpc_wss, rpc_http, db)
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        logger.info("Collector stopped.")
        collector.running = False
