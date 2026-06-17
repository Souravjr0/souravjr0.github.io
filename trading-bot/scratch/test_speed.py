import urllib.request, json, time

base = 'http://127.0.0.1:8000'

def test(name, url):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(url, timeout=10)
        data = r.read()
        elapsed = time.time() - t0
        print(f"  {name}: OK in {elapsed:.2f}s ({len(data)} bytes)")
        return True
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  {name}: FAILED in {elapsed:.2f}s - {e}")
        return False

# Wait for server to be ready
time.sleep(3)
print("=== API Response Time Test ===\n")

test("Health", f"{base}/health")
test("Dashboard HTML", f"{base}/")
test("Portfolio", f"{base}/api/portfolio")
test("Trades", f"{base}/api/trades?limit=5")
test("Logs", f"{base}/api/logs?limit=10")

print("\n=== All endpoints should complete in < 1 second ===")
