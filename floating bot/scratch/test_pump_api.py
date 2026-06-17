import asyncio
import httpx
import websockets
import json

async def test_wss():
    print("Testing Pump Fun WSS (wss://pumpportal.fun/api/data)...")
    try:
        async with websockets.connect("wss://pumpportal.fun/api/data") as ws:
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            print("  [WSS] Subscription sent. Waiting for message...")
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"  [WSS] Response received: {msg[:100]}...")
            return True
    except asyncio.TimeoutError:
        print("  [WSS] Timeout: No new token event in 5 seconds (active but quiet).")
        return True
    except Exception as e:
        print(f"  [WSS] Error: {e}")
        return False

async def test_http():
    print("\nTesting Pump Fun Trade API (https://pumpportal.fun/api/trade-local)...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://pumpportal.fun/api/trade-local", json={})
            print(f"  [HTTP] Status code: {resp.status_code}")
            if resp.status_code == 400:
                print("  [HTTP] Endpoint is alive and actively listening (rejected empty payload properly).")
                return True
            else:
                print(f"  [HTTP] Response: {resp.text[:100]}...")
                return False
    except Exception as e:
        print(f"  [HTTP] Error: {e}")
        return False

async def main():
    print("=========================================")
    print("     PUMP FUN API ALIVE & STATUS AUDIT")
    print("=========================================")
    wss_ok = await test_wss()
    http_ok = await test_http()
    print("\n=========================================")
    if wss_ok and http_ok:
        print("STATUS: BOTH PUMP FUN ENDPOINTS OPERATIONAL!")
    else:
        print("STATUS: DEGRADED PERFORMANCE DETECTED!")
    print("=========================================")

if __name__ == "__main__":
    asyncio.run(main())
