import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

async def main():
    wallet = "CEmeuuZtpfUaoacsneX8yXyuZnaX4tiPNdhXR8zpGMHG"

    async with httpx.AsyncClient() as client:
        # Get recent signatures
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 5}]
        }
        resp = await client.post(RPC_HTTP, json=payload, timeout=10.0)
        signatures = [x["signature"] for x in resp.json().get("result", [])]
        print(f"Found signatures: {signatures}")

        for sig in signatures:
            print(f"\n--- Signature: {sig} ---")
            payload_tx = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            tx_resp = await client.post(RPC_HTTP, json=payload_tx, timeout=10.0)
            tx_data = tx_resp.json().get("result")
            if not tx_data:
                print("Failed to get transaction details.")
                continue

            meta = tx_data.get("meta", {})
            pre_token_balances = meta.get("preTokenBalances", [])
            post_token_balances = meta.get("postTokenBalances", [])
            
            print(f"Number of preTokenBalances: {len(pre_token_balances)}")
            print(f"Number of postTokenBalances: {len(post_token_balances)}")
            
            for b in post_token_balances:
                mint = b.get("mint")
                owner = b.get("owner")
                amount = b.get("uiTokenAmount", {}).get("uiAmount")
                print(f"  Post balance -> Mint: {mint}, Owner: {owner}, Amount: {amount}")

asyncio.run(main())
