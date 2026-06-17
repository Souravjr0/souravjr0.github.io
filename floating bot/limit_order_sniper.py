#!/usr/bin/env python3
"""
Jupiter Limit Order Sniper — Automated Zero-Gas Volatility Strategy
cook45 & clack // Systems & MEV

Monitors the spot price of SOL, cancels stale orders, and places asymmetric 
Buy (low) and Sell (high) limit orders around the market price.
Eliminates gas fee drag for highly optimized capital growth.
"""

import os
import sys
import json
import asyncio
import logging
import time
import base64
import httpx
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add local path to import parsers
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

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
logger = logging.getLogger("LimitOrderSniper")

# Load environment
load_dotenv()

RPC_URL = os.getenv("HELIUS_RPC_URL")
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUP_PRICE_URL = "https://api.jup.ag/price/v3"

class JupiterLimitOrderSniper:
    def __init__(self, spread_offset_pct: float = 0.95, check_interval_secs: int = 120):
        self.spread_offset_pct = spread_offset_pct
        self.check_interval_secs = check_interval_secs
        self.running = False
        self.http_client = httpx.AsyncClient(timeout=15.0)
        
        # Load keypair
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
                logger.info(f"Loaded Wallet for Limit Order Sniper: {Fore.GREEN}{self.keypair.pubkey()}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"Error loading private key: {e}")
        else:
            logger.error("No private key found! Limit Order Sniper requires a configured SOLANA_PRIVATE_KEY in .env.")

    async def get_sol_price(self) -> float:
        """Fetches the current SOL USD price from the Jupiter Price API v3"""
        url = f"{JUP_PRICE_URL}?ids={SOL_MINT}"
        try:
            resp = await self.http_client.get(url)
            if resp.status_code == 200:
                price = resp.json().get(SOL_MINT, {}).get("usdPrice")
                if price:
                    return float(price)
        except Exception as e:
            logger.error(f"Failed to fetch SOL price from Jupiter: {e}")
        return 0.0

    async def get_wallet_balances(self) -> tuple[float, float]:
        """Queries the RPC to fetch SOL and USDC balances for the wallet"""
        if not self.keypair:
            return 0.0, 0.0
        
        pubkey_str = str(self.keypair.pubkey())
        sol_balance = 0.0
        usdc_balance = 0.0
        
        # 1. Fetch SOL Balance
        sol_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [pubkey_str]
        }
        
        # 2. Fetch USDC Balance
        usdc_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getTokenAccountsByOwner",
            "params": [
                pubkey_str,
                {"mint": USDC_MINT},
                {"encoding": "jsonParsed"}
            ]
        }
        
        try:
            # Fetch SOL
            res = await self.http_client.post(RPC_URL, json=sol_payload)
            if res.status_code == 200:
                val = res.json().get("result", {}).get("value", 0)
                sol_balance = val / 1e9
                
            # Fetch USDC
            res = await self.http_client.post(RPC_URL, json=usdc_payload)
            if res.status_code == 200:
                accounts = res.json().get("result", {}).get("value", [])
                if accounts:
                    account_info = accounts[0]["account"]["data"]["parsed"]["info"]
                    usdc_balance = float(account_info["tokenAmount"]["uiAmount"])
        except Exception as e:
            logger.error(f"Error fetching wallet balances: {e}")
            
        return sol_balance, usdc_balance

    async def send_and_confirm(self, signed_tx_b64: str) -> Optional[str]:
        """Submits a raw signed transaction to standard Solana RPC and polls for status"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                signed_tx_b64,
                {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
            ]
        }
        try:
            resp = await self.http_client.post(RPC_URL, json=payload)
            if resp.status_code != 200:
                logger.error(f"RPC Send failed: HTTP {resp.status_code} — {resp.text}")
                return None
            
            sig = resp.json().get("result")
            if not sig:
                err = resp.json().get("error", {})
                logger.error(f"RPC rejected transaction: {err}")
                return None
                
            logger.info(f"Transaction submitted! Signature: {Fore.CYAN}{sig[:16]}...{Style.RESET_ALL}")
            
            # Poll confirmation status
            confirm_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[sig], {"searchTransactionHistory": False}]
            }
            
            for _ in range(20):
                await asyncio.sleep(1.5)
                c_resp = await self.http_client.post(RPC_URL, json=confirm_payload)
                if c_resp.status_code == 200:
                    val = c_resp.json().get("result", {}).get("value", [None])[0]
                    if val:
                        if val.get("err"):
                            logger.error(f"Transaction failed on-chain: {val['err']}")
                            return None
                        status = val.get("confirmationStatus")
                        if status in ("confirmed", "finalized"):
                            logger.info(f"{Fore.GREEN}Transaction successfully confirmed! Status: {status}{Style.RESET_ALL}")
                            return sig
            logger.warning("Transaction confirmation timed out.")
            return None
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return None

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Queries the Jupiter API to fetch all active open limit orders for the loaded wallet"""
        if not self.keypair:
            return []
        
        url = f"https://limit.jup.ag/v1/openOrders?wallet={self.keypair.pubkey()}"
        try:
            resp = await self.http_client.get(url)
            if resp.status_code == 200:
                orders = resp.json()
                if isinstance(orders, list):
                    return orders
        except Exception as e:
            logger.error(f"Failed to fetch open orders from Jupiter: {e}")
        return []

    async def cancel_open_orders(self) -> bool:
        """Fetches and cancels all active limit orders for the loaded keypair"""
        orders = await self.get_open_orders()
        if not orders:
            logger.info("No open limit orders to cancel.")
            return True
            
        order_pubkeys = [o["publicKey"] for o in orders if "publicKey" in o]
        if not order_pubkeys:
            return True
            
        logger.info(f"Cancelling {len(order_pubkeys)} open order(s) on Jupiter...")
        
        payload = {
            "maker": str(self.keypair.pubkey()),
            "orders": order_pubkeys
        }
        
        try:
            resp = await self.http_client.post("https://limit.jup.ag/v1/cancelOrders", json=payload)
            if resp.status_code != 200:
                logger.error(f"Failed to compile cancel transaction: HTTP {resp.status_code} — {resp.text}")
                return False
                
            tx_b64 = resp.json().get("transaction")
            if not tx_b64:
                logger.error("No transaction returned by cancellation API.")
                return False
                
            # Decode and sign
            raw_tx = base64.b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
            signed_tx = VersionedTransaction(tx.message, [sig])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            
            # Submit to Helius RPC
            confirmed_sig = await self.send_and_confirm(signed_b64)
            return confirmed_sig is not None
        except Exception as e:
            logger.error(f"Error during order cancellation: {e}")
            return False

    async def place_limit_order(self, input_mint: str, output_mint: str, in_amount: int, out_amount: int) -> bool:
        """Sends a request to create a limit order, signs the unsigned transaction, and sends to RPC"""
        payload = {
            "owner": str(self.keypair.pubkey()),
            "inAmount": str(in_amount),
            "outAmount": str(out_amount),
            "inputMint": input_mint,
            "outputMint": output_mint
        }
        
        try:
            resp = await self.http_client.post("https://limit.jup.ag/v1/createOrder", json=payload)
            if resp.status_code != 200:
                logger.error(f"Failed to compile createOrder transaction: HTTP {resp.status_code} — {resp.text}")
                return False
            
            resp_data = resp.json()
            tx_b64 = (
                resp_data.get("transaction") or 
                resp_data.get("transactionData") or 
                resp_data.get("transaction_data") or 
                resp_data.get("swapTransaction")
            )
            
            if not tx_b64:
                logger.error(f"No transaction found in createOrder API response: {resp_data}")
                return False
                
            # Decode and sign
            raw_tx = base64.b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = self.keypair.sign_message(to_bytes_versioned(tx.message))
            signed_tx = VersionedTransaction(tx.message, [sig])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            
            # Submit to Helius RPC
            confirmed_sig = await self.send_and_confirm(signed_b64)
            return confirmed_sig is not None
        except Exception as e:
            logger.error(f"Error during order placement: {e}")
            return False

    async def run(self):
        """Starts the main sniper background daemon loop"""
        if not self.keypair:
            logger.error("Abort: Keypair not loaded.")
            return

        logger.info(f"""
{Fore.LIGHTCYAN_EX}{Style.BRIGHT}========================================================================
            JUPITER AUTOMATED LIMIT ORDER SNIPER DAEMON
                Designed by cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
""")

        self.running = True
        
        while self.running:
            try:
                # 1. Fetch live balances and SOL spot price
                sol_bal, usdc_bal = await self.get_wallet_balances()
                sol_price = await self.get_sol_price()
                
                if sol_price <= 0:
                    logger.warning("Stale SOL price. Retrying in 10s...")
                    await asyncio.sleep(10)
                    continue
                    
                total_capital_usd = usdc_bal + (sol_bal * sol_price)
                logger.info(
                    f"[STATUS] Balances: {Fore.YELLOW}{sol_bal:.5f} SOL{Style.RESET_ALL} | "
                    f"{Fore.YELLOW}${usdc_bal:.2f} USDC{Style.RESET_ALL} | "
                    f"SOL Spot Price: {Fore.GREEN}${sol_price:.2f}{Style.RESET_ALL} | "
                    f"Total Assets: {Fore.CYAN}${total_capital_usd:.2f}{Style.RESET_ALL}"
                )

                # 2. Failsafe minimum balance protection
                if total_capital_usd < 10.0:
                    logger.warning(
                        f"{Fore.RED}[MINIMUM BALANCE PROTECTION ACTIVE]{Style.RESET_ALL} "
                        f"Jupiter limit orders require a minimum order size of **$10 USD**.\n"
                        f"Current total assets: {Fore.YELLOW}${total_capital_usd:.2f} USD{Style.RESET_ALL}. "
                        f"Limit Order Sniper is **PAUSED**.\n"
                        f"--> {Fore.LIGHTGREEN_EX}Action Required: Please deposit at least $10 USDC or SOL to activate the zero-gas Sniper!{Style.RESET_ALL}\n"
                        f"--> Defaulting back to the Helius WebSocket high-threshold Spike Arbitrage engine..."
                    )
                    await asyncio.sleep(self.check_interval_secs)
                    continue

                # 3. Clean up existing old orders to free up liquidity
                logger.info("Frees up wallet liquidity by cancelling any stale limit orders...")
                await self.cancel_open_orders()
                
                # Re-fetch balances after cancellation
                await asyncio.sleep(2)
                sol_bal, usdc_bal = await self.get_wallet_balances()

                # 4. Calculate volatility buy/sell pricing limits
                buy_price = sol_price * (1.0 - (self.spread_offset_pct / 100))
                sell_price = sol_price * (1.0 + (self.spread_offset_pct / 100))
                
                logger.info(
                    f"Asymmetric Price Targets:\n"
                    f"   - BUY TARGET:  {Fore.GREEN}${buy_price:.2f}{Style.RESET_ALL} ({self.spread_offset_pct}% below market)\n"
                    f"   - SELL TARGET: {Fore.RED}${sell_price:.2f}{Style.RESET_ALL} ({self.spread_offset_pct}% above market)"
                )

                # 5. Place Buy Order (Sell USDC for SOL) if capital is available in USDC
                if usdc_bal >= 10.0:
                    # Raw USDC amount (6 decimals)
                    usdc_in_raw = int(usdc_bal * 1e6)
                    # Expected SOL output (9 decimals): USDC_in / buy_price
                    sol_out_raw = int((usdc_bal / buy_price) * 1e9)
                    
                    logger.info(f"Placing Buy Order: Sell {usdc_bal:.2f} USDC for SOL at target ${buy_price:.2f}...")
                    success = await self.place_limit_order(
                        input_mint=USDC_MINT,
                        output_mint=SOL_MINT,
                        in_amount=usdc_in_raw,
                        out_amount=sol_out_raw
                    )
                    if success:
                        logger.info(f"{Fore.GREEN}✓ BUY LIMIT ORDER ACTIVE!{Style.RESET_ALL}")
                    else:
                        logger.error("Failed to place Buy Limit Order.")

                # 6. Place Sell Order (Sell SOL for USDC) if capital is available in SOL
                # Reserve a minor safety buffer for signature fees (0.005 SOL)
                tradeable_sol = sol_bal - 0.005
                if tradeable_sol * sol_price >= 10.0:
                    # Raw SOL amount (9 decimals)
                    sol_in_raw = int(tradeable_sol * 1e9)
                    # Expected USDC output (6 decimals): SOL_in * sell_price
                    usdc_out_raw = int((tradeable_sol * sell_price) * 1e6)
                    
                    logger.info(f"Placing Sell Order: Sell {tradeable_sol:.5f} SOL for USDC at target ${sell_price:.2f}...")
                    success = await self.place_limit_order(
                        input_mint=SOL_MINT,
                        output_mint=USDC_MINT,
                        in_amount=sol_in_raw,
                        out_amount=usdc_out_raw
                    )
                    if success:
                        logger.info(f"{Fore.GREEN}✓ SELL LIMIT ORDER ACTIVE!{Style.RESET_ALL}")
                    else:
                        logger.error("Failed to place Sell Limit Order.")

                logger.info(f"Order placement block finalized. Sleeping for {self.check_interval_secs}s before rotation check...")
                
            except Exception as e:
                logger.error(f"Limit order sniper loop encountered crash: {e}")
                
            await asyncio.sleep(self.check_interval_secs)

    def stop(self):
        self.running = False

async def main():
    # Place orders at 0.95% offsets, checking/rebalancing every 120 seconds
    sniper = JupiterLimitOrderSniper(spread_offset_pct=0.95, check_interval_secs=120)
    try:
        await sniper.run()
    except KeyboardInterrupt:
        logger.info("Limit Order Sniper stopped by user.")
        sniper.stop()

if __name__ == "__main__":
    asyncio.run(main())
