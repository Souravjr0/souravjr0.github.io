import yfinance as yf
import pandas as pd
import numpy as np
import time
from exchange_client import get_spot_client
from config import WATCHLIST

def get_top_crypto_by_volume(limit: int = 10) -> list[str]:
    """Fetch top cryptocurrency symbols from Binance sorted by 24h volume."""
    try:
        client = get_spot_client()
        # Since client might be a custom client, let's see if we can get all tickers
        # Usually it has client.client (python-binance client) or client is custom exchange adapter
        raw_client = getattr(client, "client", client)
        
        # If ccxt is used
        if hasattr(client, "exchange"):
            exchange = client.exchange
            tickers = exchange.fetch_tickers()
            # Filter for USDT pairs
            usdt_tickers = {k: v for k, v in tickers.items() if k.endswith("/USDT") or k.endswith("USDT")}
            # Sort by baseVolume or quoteVolume
            sorted_tickers = sorted(
                usdt_tickers.items(),
                key=lambda x: x[1].get("quoteVolume", x[1].get("baseVolume", 0)) or 0,
                reverse=True
            )
            top_symbols = [t[0].replace("/", "") for t in sorted_tickers[:limit]]
            return top_symbols
        
        # If python-binance REST client is used
        if hasattr(raw_client, "get_ticker"):
            tickers = raw_client.get_ticker()
            # Filter for USDT pairs and sort by volume
            usdt_tickers = [t for t in tickers if t["symbol"].endswith("USDT")]
            sorted_tickers = sorted(
                usdt_tickers,
                key=lambda x: float(x.get("quoteVolume", 0)),
                reverse=True
            )
            top_symbols = [t["symbol"] for t in sorted_tickers[:limit]]
            return top_symbols
            
    except Exception as e:
        print(f"[Discovery] Failed to scan live crypto markets: {e}. Falling back to default watchlist.")
    
    # Fallback
    return WATCHLIST[:limit]

# Curated high-liquidity stock list
STOCK_WATCHLIST = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "COIN", "SPY", "QQQ"]

def fetch_stock_data(symbol: str, interval: str = "1h", period: str = "60d") -> pd.DataFrame:
    """Fetch historical stock candle data from Yahoo Finance."""
    # Convert interval to yfinance format
    # yfinance intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    yf_interval = interval
    if interval == "15m":
        yf_interval = "15m"
        period = "60d" # Max period for 15m is 60d
    elif interval == "1h":
        yf_interval = "1h"
        period = "730d" # Max period for 1h is 730d
    elif interval == "1d":
        yf_interval = "1d"
        period = "max"
        
    symbol_clean = symbol.strip().upper()
    # Map standard 6-character forex pairs to yfinance =X format (e.g. GBPUSD -> GBPUSD=X)
    forex_currencies = {
        "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", 
        "SGD", "HKD", "CNY", "INR", "MXN", "ZAR", "SEK", "NOK", 
        "TRY", "RUB", "BRL", "TWD", "KRW"
    }
    if len(symbol_clean) == 6 and symbol_clean[:3] in forex_currencies and symbol_clean[3:] in forex_currencies:
        yf_symbol = f"{symbol_clean}=X"
    else:
        yf_symbol = symbol_clean
        
    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=yf_interval)
        if df.empty:
            return pd.DataFrame()
            
        # Standardize columns to lowercase to match bot structure
        df = df.reset_index()
        column_mapping = {
            "Datetime": "open_time",
            "Date": "open_time",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
        df = df.rename(columns=column_mapping)
        
        # Ensure standard float conversion
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(float)
                
        # Drop columns not needed
        needed_cols = ["open_time", "open", "high", "low", "close", "volume"]
        df = df[[c for c in needed_cols if c in df.columns]]
        
        # Add timezone-aware UTC datetime
        if "open_time" in df.columns:
            df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
            df["close_time"] = df["open_time"] + pd.Timedelta(seconds=1)
            
        # Add mock column values to match KLINE_COLUMNS format if needed
        df["quote_volume"] = df["volume"] * df["close"]
        df["trade_count"] = 0
        df["taker_buy_base"] = 0
        df["taker_buy_quote"] = 0
        df["ignore"] = 0
        
        return df
    except Exception as e:
        print(f"[Discovery] Failed to fetch stock data for {symbol}: {e}")
        return pd.DataFrame()

def scan_stocks(interval: str = "1h", limit: int = 200) -> dict[str, pd.DataFrame]:
    """Scan stock watchlist and return cleaned DataFrames for each."""
    results = {}
    for symbol in STOCK_WATCHLIST:
        df = fetch_stock_data(symbol, interval=interval)
        if not df.empty and len(df) >= limit:
            results[symbol] = df.tail(limit).copy()
        time.sleep(0.1) # Small rate limiting pause
    return results
