"""
TradingView Public Scanner API Client.
Fetches real-time price quotes, changes, indicator states, and technical analyst ratings.
Requires zero API keys.
"""

import json
import logging
import urllib.request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Standard global fiat currencies to identify Forex pairs
FOREX_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", 
    "SGD", "HKD", "CNY", "INR", "MXN", "ZAR", "SEK", "NOK", 
    "TRY", "RUB", "BRL", "TWD", "KRW"
}

def resolve_tv_symbol(symbol: str) -> str:
    """
    Resolve a symbol to its standard TradingView ticker prefix format (EXCHANGE:SYMBOL).
    """
    symbol_upper = symbol.strip().upper()
    
    # 1. Forex pairs (6-character combination of fiat currencies)
    if len(symbol_upper) == 6 and symbol_upper[:3] in FOREX_CURRENCIES and symbol_upper[3:] in FOREX_CURRENCIES:
        return f"FX:{symbol_upper}"
    
    # 2. Crypto pairs
    if symbol_upper.endswith("USDT") or symbol_upper.endswith("BTC") or symbol_upper.endswith("ETH"):
        clean_symbol = symbol_upper.replace("/", "")
        return f"BINANCE:{clean_symbol}"
        
    # 3. Known Futures Contracts
    if symbol_upper in {"GC=F", "GC"}:
        return "COMEX:GC1!"
    if symbol_upper in {"SI=F", "SI"}:
        return "COMEX:SI1!"
    if symbol_upper in {"CL=F", "CL"}:
        return "NYMEX:CL1!"
        
    # 4. Standard Watchlist Stocks & ETFs
    if symbol_upper == "SPY":
        return "AMEX:SPY"
    if symbol_upper == "QQQ":
        return "NASDAQ:QQQ"
    if symbol_upper == "GLD":
        return "AMEX:GLD"
    if symbol_upper == "SLV":
        return "AMEX:SLV"
    if symbol_upper == "USO":
        return "AMEX:USO"
        
    if symbol_upper in {"AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "COIN"}:
        return f"NASDAQ:{symbol_upper}"
        
    # Fallback default: treat as NASDAQ stock
    return f"NASDAQ:{symbol_upper}"

def query_tradingview_scanner(ticker: str) -> dict:
    """
    Queries TradingView's public global scanner API to fetch technical summaries,
    indicator values, and real-time close price statistics.
    
    Returns:
        dict: A dictionary containing 'close', 'change', 'recommendation', 'rsi', etc.,
              or an empty dict if the query fails.
    """
    tv_symbol = resolve_tv_symbol(ticker)
    url = "https://scanner.tradingview.com/global/scan"
    
    payload = {
        "symbols": {
            "tickers": [tv_symbol],
            "query": { "types": [] }
        },
        "columns": [
            "close",
            "change",
            "recommendation",
            "RSI",
            "MACD.macd",
            "MACD.signal",
            "Stoch.RSI.K",
            "EMA20",
            "EMA50",
            "volume"
        ]
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("data"):
                d = res_data["data"][0].get("d", [])
                if len(d) >= 10:
                    # Clean up rating format (e.g. STRONG_BUY -> STRONG BUY)
                    rec = d[2]
                    if isinstance(rec, str):
                        rec = rec.replace("_", " ").upper()
                    
                    return {
                        "symbol": ticker,
                        "tv_symbol": tv_symbol,
                        "close": d[0],
                        "change": d[1],
                        "recommendation": rec or "NEUTRAL",
                        "rsi": round(d[3], 2) if d[3] is not None else None,
                        "macd": round(d[4], 4) if d[4] is not None else None,
                        "macd_signal": round(d[5], 4) if d[5] is not None else None,
                        "stoch_rsi": round(d[6], 2) if d[6] is not None else None,
                        "ema20": round(d[7], 4) if d[7] is not None else None,
                        "ema50": round(d[8], 4) if d[8] is not None else None,
                        "volume": d[9]
                    }
    except URLError as e:
        logger.warning(f"Network error querying TradingView scanner for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing TradingView data for {ticker}: {e}")
        
    return {}

if __name__ == "__main__":
    # Self-test block
    import sys
    test_symbols = ["GBPUSD", "AAPL", "BTCUSDT", "GLD", "GC=F"]
    print("--- Running TradingView Public Scanner Self-Test ---")
    for s in test_symbols:
        res = query_tradingview_scanner(s)
        if res:
            print(f"[{s}] TV Ticker: {res['tv_symbol']} | Price: {res['close']} ({res['change']:.3f}%) | Rec: {res['recommendation']} | RSI: {res['rsi']}")
        else:
            print(f"[{s}] Failed to fetch scanner data.")
