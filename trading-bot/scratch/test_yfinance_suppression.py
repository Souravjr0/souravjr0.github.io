import contextlib
import io
import sys

print("Attempting to fetch delisted ticker MULN WITH suppression:")
try:
    import yfinance as yf
    
    f_stdout = io.StringIO()
    f_stderr = io.StringIO()
    with contextlib.redirect_stdout(f_stdout), contextlib.redirect_stderr(f_stderr):
        ticker_obj = yf.Ticker("MULN")
        hist = ticker_obj.history(period="max", interval="1d", auto_adjust=True)
        ed = ticker_obj.earnings_dates
    print("Fetch finished. Suppressed output:")
    print("STDOUT:", f_stdout.getvalue())
    print("STDERR:", f_stderr.getvalue())
except Exception as e:
    print("Caught exception:", e)

print("\nAttempting to fetch delisted ticker MULN WITHOUT suppression:")
try:
    import yfinance as yf
    ticker_obj = yf.Ticker("MULN")
    hist = ticker_obj.history(period="max", interval="1d", auto_adjust=True)
    ed = ticker_obj.earnings_dates
except Exception as e:
    print("Caught exception:", e)
