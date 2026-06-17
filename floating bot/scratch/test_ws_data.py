import os
import sys
import json
import base64
import asyncio
from dotenv import load_dotenv
import websockets

WORKSPACE_DIR = r"c:\Users\Sourav Biswas\Souravjr0\floating bot"
sys.path.append(WORKSPACE_DIR)

load_dotenv(dotenv_path=os.path.join(WORKSPACE_DIR, ".env"))
WSS_URL = os.getenv("HELIUS_WSS_URL")

RAYDIUM_CLMM_POOL = "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq"
ORCA_WHIRLPOOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

async def main():
    print("[+] Connecting to Helius WebSocket...")
    async with websockets.connect(WSS_URL) as ws:
        print("[+] Connected!")
        
        subscribe_accounts = [RAYDIUM_CLMM_POOL, ORCA_WHIRLPOOL]
        
        for idx, addr in enumerate(subscribe_accounts):
            payload = {
                "jsonrpc": "2.0",
                "id": idx + 1,
                "method": "accountSubscribe",
                "params": [
                    addr,
                    {"encoding": "base64", "commitment": "processed"}
                ]
            }
            await ws.send(json.dumps(payload))
            print(f"  -> Subscribed to {addr}")
            
        print("\n[+] Waiting for messages to check data length and structure...")
        try:
            # We wait up to 15 seconds and print decoded information
            async with asyncio.timeout(15):
                async for message in ws:
                    event = json.loads(message)
                    if "params" not in event:
                        print(f"Sub confirmation or other message: {message}")
                        continue
                    
                    params = event["params"]
                    sub_id = params["subscription"]
                    value = params["result"]["value"]
                    data_b64 = value["data"][0]
                    raw_bytes = base64.b64decode(data_b64)
                    data_len = len(raw_bytes)
                    
                    # Identify by sub_id or address
                    addr_type = "UNKNOWN"
                    if sub_id == 42123974 or sub_id == 1:
                        addr_type = "RAYDIUM (maybe)"
                    elif sub_id == 42123975 or sub_id == 2:
                        addr_type = "ORCA (maybe)"
                    
                    print(f"Received update: sub={sub_id}, length={data_len} bytes. First 10 bytes: {raw_bytes[:10].hex()}")
        except TimeoutError:
            print("\n[-] Timeout.")

if __name__ == "__main__":
    asyncio.run(main())
