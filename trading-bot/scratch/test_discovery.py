import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchange_client import get_spot_client
import ccxt

print("Initializing client...")
client = get_spot_client()
print("Client initialized. Provider:", type(client))

if hasattr(client, "exchange"):
    print("Exchange hasattr: YES")
    exchange = client.exchange
    print("Testing exchange.fetch_tickers()... This might be slow.")
    try:
        tickers = exchange.fetch_tickers()
        print("fetch_tickers() finished. Total tickers:", len(tickers))
    except Exception as e:
        print("Error fetch_tickers:", e)
else:
    print("Exchange hasattr: NO")
