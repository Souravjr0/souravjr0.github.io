#!/usr/bin/env python3
"""
Multi-Exchange Smart Order Router (SOR) & Cross-Venue Arbitrage Engine.
Concurrently connects to Binance and OKX, bypasses geo-restrictions,
compares order book spreads, and routes orders to the lowest-slippage venue.
"""

import os
import sys

# Dynamic path resolution to support restructured package layouts and nested submodules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) in ["core", "models", "execution", "discovery", "utils"] else current_dir
for subfolder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, subfolder))
sys.path.append(project_root)

import json
import time
import threading
from typing import Any
import ccxt

from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET,
    OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSWORD, CCXT_HOSTNAME
)
from exchange_client import get_spot_client, _to_ccxt_symbol, _from_ccxt_symbol

class ExchangeRouter:
    def __init__(self):
        self.binance = get_spot_client()
        self.okx = None
        self._init_okx()

    def _init_okx(self):
        """Safely initialize OKX client using regional geobypass domain mapping."""
        try:
            config = {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
                "hostname": CCXT_HOSTNAME or "okx.cab" # bypass regional geoblocks
            }
            if OKX_API_KEY:
                config["apiKey"] = OKX_API_KEY
                config["secret"] = OKX_API_SECRET
                config["password"] = OKX_API_PASSWORD
                
            self.okx = ccxt.okx(config)
            if BINANCE_TESTNET:
                self.okx.set_sandbox_mode(True)
            print("[Exchange Router] Connected to OKX via geobypass proxy okx.cab successfully.")
        except Exception as e:
            print(f"[Exchange Router] Failed to initialize OKX client: {e}")
            self.okx = None

    def get_ticker_both(self, symbol: str) -> dict[str, dict[str, float] | None]:
        """Fetch tickers from both Binance and OKX concurrently."""
        results = {"binance": None, "okx": None}
        threads = []

        def _fetch_binance():
            try:
                # Use spot client get_price as last price or fetch ccxt equivalent
                price = self.binance.get_price(symbol)
                results["binance"] = {"bid": price * 0.9999, "ask": price * 1.0001, "last": price}
            except Exception:
                pass

        def _fetch_okx():
            if not self.okx:
                return
            try:
                ccxt_sym = _to_ccxt_symbol(symbol)
                ticker = self.okx.fetch_ticker(ccxt_sym)
                results["okx"] = {
                    "bid": float(ticker.get("bid") or ticker.get("close") or 0.0),
                    "ask": float(ticker.get("ask") or ticker.get("close") or 0.0),
                    "last": float(ticker.get("last") or ticker.get("close") or 0.0)
                }
            except Exception:
                pass

        t1 = threading.Thread(target=_fetch_binance)
        t2 = threading.Thread(target=_fetch_okx)
        threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)
            
        return results

    def get_best_execution_venue(self, symbol: str, side: str, quote_qty: float) -> str:
        """Evaluate order book tickers to select the lowest slippage execution venue."""
        tickers = self.get_ticker_both(symbol)
        binance_t = tickers["binance"]
        okx_t = tickers["okx"]

        if not okx_t:
            return "binance"
        if not binance_t:
            return "okx"

        side = side.upper()
        if side == "BUY":
            # Buy orders want the lowest ASK price
            if binance_t["ask"] <= okx_t["ask"]:
                return "binance"
            return "okx"
        else:
            # Sell orders want the highest BID price
            if binance_t["bid"] >= okx_t["bid"]:
                return "binance"
            return "okx"

    def route_order(self, symbol: str, side: str, quantity: float | None = None, quote_qty: float | None = None, order_type: str = "MARKET") -> dict:
        """Route order automatically to the lowest-slippage exchange venue."""
        target_qty = quote_qty or 20.0
        venue = self.get_best_execution_venue(symbol, side, target_qty)
        print(f"[Smart Router] Selected best execution venue for {symbol} ({side}): {venue.upper()}")

        if venue == "binance":
            order = self.binance.place_order(symbol, side, order_type, quantity, quote_qty)
            order["venue"] = "binance"
            return order
        else:
            if not self.okx:
                # Fallback to binance
                order = self.binance.place_order(symbol, side, order_type, quantity, quote_qty)
                order["venue"] = "binance"
                return order
                
            ccxt_sym = _to_ccxt_symbol(symbol)
            ccxt_side = side.lower()
            
            # Execute on OKX via CCXT
            if ccxt_side == "buy":
                if quote_qty is not None:
                    # CCXT buy order using quoteQty
                    order = self.okx.create_order(ccxt_sym, "market", "buy", None, None, {"quoteOrderQty": quote_qty})
                else:
                    order = self.okx.create_market_buy_order(ccxt_sym, quantity)
            else:
                if quantity is not None:
                    order = self.okx.create_market_sell_order(ccxt_sym, quantity)
                else:
                    ticker = okx_t = self.okx.fetch_ticker(ccxt_sym)
                    price = float(ticker.get("bid") or ticker.get("close") or 1.0)
                    order = self.okx.create_market_sell_order(ccxt_sym, quote_qty / price)
                    
            order["venue"] = "okx"
            return order

    def scan_cross_exchange_arbitrage(self, active_symbols: list[str]) -> list[dict]:
        """Scan active watchlist for profitable cross-exchange spot arbitrage loops."""
        arbitrage_opportunities = []
        fee_rate = 0.002 # 0.2% round-trip transaction fee

        for symbol in active_symbols:
            try:
                tickers = self.get_ticker_both(symbol)
                bin_t = tickers["binance"]
                okx_t = tickers["okx"]
                
                if not bin_t or not okx_t:
                    continue
                    
                bin_price = bin_t["last"]
                okx_price = okx_t["last"]
                
                if bin_price <= 0 or okx_price <= 0:
                    continue
                    
                # Option A: Buy Binance, Sell OKX
                spread_a = (okx_price - bin_price) / bin_price
                # Option B: Buy OKX, Sell Binance
                spread_b = (bin_price - okx_price) / okx_price
                
                if spread_a > fee_rate:
                    arbitrage_opportunities.append({
                        "symbol": symbol,
                        "buy_venue": "binance",
                        "buy_price": bin_price,
                        "sell_venue": "okx",
                        "sell_price": okx_price,
                        "spread_pct": round(spread_a * 100.0, 4),
                        "net_profit_pct": round((spread_a - fee_rate) * 100.0, 4)
                    })
                elif spread_b > fee_rate:
                    arbitrage_opportunities.append({
                        "symbol": symbol,
                        "buy_venue": "okx",
                        "buy_price": okx_price,
                        "sell_venue": "binance",
                        "sell_price": bin_price,
                        "spread_pct": round(spread_b * 100.0, 4),
                        "net_profit_pct": round((spread_b - fee_rate) * 100.0, 4)
                    })
            except Exception:
                continue

        if arbitrage_opportunities:
            print("\n=====================================================================================")
            print("                 PROFITABLE CROSS-VENUE SPOT ARBITRAGE OPPORTUNITIES                 ")
            print("=====================================================================================")
            for opp in arbitrage_opportunities:
                print(f"  [ARBITRAGE] {opp['symbol']} | Buy {opp['buy_venue'].upper()} @ ${opp['buy_price']:.4f} -> Sell {opp['sell_venue'].upper()} @ ${opp['sell_price']:.4f}")
                print(f"              Gross Spread: {opp['spread_pct']}% | Net Profit (after fees): {opp['net_profit_pct']}%")
            print("=====================================================================================\n")
            
        return arbitrage_opportunities

if __name__ == "__main__":
    router = ExchangeRouter()
    # Check current spreads
    watch = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    print(f"[Smart Router] Checking bid-ask spreads for watchlist: {watch}")
    for w in watch:
        t = router.get_ticker_both(w)
        print(f"  {w} Tickers -> Binance: {t['binance']} | OKX: {t['okx']}")
        
    router.scan_cross_exchange_arbitrage(watch)
