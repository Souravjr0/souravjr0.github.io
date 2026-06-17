import urllib.request, json, time

# Test portfolio endpoint timing
print("Testing /api/portfolio...")
t0 = time.time()
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/api/portfolio', timeout=120)
    d = json.loads(r.read())
    elapsed = time.time() - t0
    print(f"  Took: {elapsed:.1f}s")
    print(f"  Total trades: {d.get('total_trades')}")
    print(f"  Net PnL: {d.get('net_pnl')}")
    positions = d.get('open_positions', [])
    print(f"  Open positions: {len(positions)}")
    for p in positions:
        sym = p.get('symbol', '?')
        cp = p.get('current_price')
        pnl = p.get('unrealized_pnl')
        print(f"    {sym}: price={cp}, pnl={pnl}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  FAILED after {elapsed:.1f}s: {e}")

# Test trades
print("\nTesting /api/trades...")
t0 = time.time()
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/api/trades?limit=3', timeout=30)
    d = json.loads(r.read())
    elapsed = time.time() - t0
    print(f"  Took: {elapsed:.1f}s, count: {len(d)}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  FAILED after {elapsed:.1f}s: {e}")

# Test logs
print("\nTesting /api/logs...")
t0 = time.time()
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/api/logs?limit=10', timeout=30)
    d = json.loads(r.read())
    elapsed = time.time() - t0
    print(f"  Took: {elapsed:.1f}s, count: {len(d)}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  FAILED after {elapsed:.1f}s: {e}")

# Test dashboard
print("\nTesting / (dashboard)...")
t0 = time.time()
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=30)
    html = r.read()
    elapsed = time.time() - t0
    print(f"  Took: {elapsed:.1f}s, size: {len(html)} bytes")
except Exception as e:
    elapsed = time.time() - t0
    print(f"  FAILED after {elapsed:.1f}s: {e}")
