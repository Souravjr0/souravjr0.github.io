import os
import sys
import json
import base64
import asyncio
from dotenv import load_dotenv
import websockets
import httpx

WORKSPACE_DIR = r"c:\Users\Sourav Biswas\Souravjr0\floating bot"
sys.path.append(WORKSPACE_DIR)

from pool_parsers import parse_raydium_clmm, parse_orca_whirlpool

load_dotenv(dotenv_path=os.path.join(WORKSPACE_DIR, ".env"))
WSS_URL = os.getenv("HELIUS_WSS_URL")
RPC_URL = os.getenv("HELIUS_RPC_URL")

# The highly active SOL/USDC pools on mainnet:
# Raydium CLMM SOL/USDC 0.05% fee tier:
# Address: 3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv
# Orca concentrated Whirlpool SOL/USDC 0.05% fee tier:
# Address: Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE
RAYDIUM_ACTIVE_POOL = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv"
ORCA_ACTIVE_POOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

async def get_initial_states():
    client = httpx.AsyncClient(timeout=10)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [
            [RAYDIUM_ACTIVE_POOL, ORCA_ACTIVE_POOL],
            {"encoding": "base64"}
        ]
    }
    response = await client.post(RPC_URL, json=payload)
    result = response.json().get("result")
    value = result["value"]
    
    r_state = parse_raydium_clmm(base64.b64decode(value[0]["data"][0]))
    o_state = parse_orca_whirlpool(base64.b64decode(value[1]["data"][0]))
    await client.aclose()
    return r_state, o_state

async def main():
    print("[+] Fetching initial states...")
    r_state, o_state = await get_initial_states()
    
    # Note: Raydium and Orca layouts define Token 0 and Token 1:
    # Token 0 (A) is SOL (9 decimals) and Token 1 (B) is USDC (6 decimals)
    # The sqrt_price represents the ratio of token_1 to token_0:
    # price = (sqrt_price / 2^64)^2 * (10^9 / 10^6) = (sqrt_price / 2^64)^2 * 1000
    
    r_price = (r_state["sqrt_price"] / (2**64)) ** 2 * 1000
    o_price = (o_state["sqrt_price"] / (2**64)) ** 2 * 1000
    print(f"Initial Raydium Active SOL Price: ${r_price:.4f} (sqrt_price: {r_state['sqrt_price']})")
    print(f"Initial Orca Active SOL Price:    ${o_price:.4f} (sqrt_price: {o_state['sqrt_price']})")
    
    print("[+] Connecting to Helius WebSocket...")
    async with websockets.connect(WSS_URL) as ws:
        print("[+] Connected!")
        
        subscribe_accounts = [RAYDIUM_ACTIVE_POOL, ORCA_ACTIVE_POOL]
        
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
            
        print("\n[+] Listening for updates for 30 seconds...")
        
        r_updates = 0
        o_updates = 0
        
        try:
            async with asyncio.timeout(30):
                async for message in ws:
                    event = json.loads(message)
                    if "params" not in event:
                        print(f"Sub confirmation: {message}")
                        continue
                    
                    params = event["params"]
                    value = params["result"]["value"]
                    data_b64 = value["data"][0]
                    raw_bytes = base64.b64decode(data_b64)
                    data_len = len(raw_bytes)
                    
                    if data_len == 1544:
                        r_updates += 1
                        new_r = parse_raydium_clmm(raw_bytes)
                        diff_price = new_r['sqrt_price'] - r_state['sqrt_price']
                        diff_liq = new_r['liquidity'] - r_state['liquidity']
                        
                        r_price = (new_r["sqrt_price"] / (2**64)) ** 2 * 1000
                        print(f"[Raydium #{r_updates}] Price: ${r_price:.4f} (diff: {diff_price}), Liquidity diff: {diff_liq}")
                        if diff_price != 0 or diff_liq != 0:
                            r_state = new_r
                    elif data_len == 653:
                        o_updates += 1
                        new_o = parse_orca_whirlpool(raw_bytes)
                        diff_price = new_o['sqrt_price'] - o_state['sqrt_price']
                        diff_liq = new_o['liquidity'] - o_state['liquidity']
                        
                        o_price = (new_o["sqrt_price"] / (2**64)) ** 2 * 1000
                        print(f"[Orca #{o_updates}] Price: ${o_price:.4f} (diff: {diff_price}), Liquidity diff: {diff_liq}")
                        if diff_price != 0 or diff_liq != 0:
                            o_state = new_o
                    else:
                        print(f"[Unknown] Received update with length: {data_len} bytes")
        except TimeoutError:
            print("\n[+] 30 seconds observation finished.")

if __name__ == "__main__":
    asyncio.run(main())
