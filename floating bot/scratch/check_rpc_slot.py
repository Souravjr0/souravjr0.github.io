import httpx
import json
import asyncio
import websockets

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    wss_url = "wss://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    # 1. Query HTTP Slot
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        http_slot = response.json()["result"]
        print(f"[HTTP] Current slot: {http_slot}")
        
    # 2. Query WS Slot
    print("[WSS] Connecting to check WS slots...")
    async with websockets.connect(wss_url) as ws:
        # Subscribe to slot
        payload_ws = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "slotSubscribe"
        }
        await ws.send(json.dumps(payload_ws))
        
        # Read the subscription confirmation
        conf = await ws.recv()
        print(f"[WSS] Subscribed: {conf}")
        
        # Read the first 3 slot updates
        for i in range(3):
            msg = await ws.recv()
            event = json.loads(msg)
            if "params" in event:
                slot_info = event["params"]["result"]
                print(f"[WSS Slot Update #{i+1}] Slot: {slot_info.get('slot')}, Parent: {slot_info.get('parent')}, Root: {slot_info.get('root')}")

if __name__ == "__main__":
    asyncio.run(main())
