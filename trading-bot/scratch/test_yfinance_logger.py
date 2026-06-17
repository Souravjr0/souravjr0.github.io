import logging
import yfinance as yf

print("Setting yfinance logger to CRITICAL:")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

try:
    ticker_obj = yf.Ticker("MULN")
    print("Calling history...")
    hist = ticker_obj.history(period="max", interval="1d", auto_adjust=True)
    print("Calling earnings_dates...")
    ed = ticker_obj.earnings_dates
except Exception as e:
    print("Caught exception:", e)
