import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

async def main():
    wallet = "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN"
    print(f"Analyzing wallet: {wallet}")

    async with httpx.AsyncClient() as client:
        # Get recent signatures
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 10}]
        }
        resp = await client.post(RPC_HTTP, json=payload, timeout=10.0)
        signatures = [x["signature"] for x in resp.json().get("result", [])]
        print(f"Found {len(signatures)} recent transactions.\n")

        for i, sig in enumerate(signatures, 1):
            print(f"[{i}] Tx: {sig}")
            payload_tx = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            tx_resp = await client.post(RPC_HTTP, json=payload_tx, timeout=10.0)
            tx_data = tx_resp.json().get("result")
            if not tx_data:
                print("  Failed to get transaction details.")
                continue

            meta = tx_data.get("meta", {})
            if not meta:
                continue
            err = meta.get("err")
            if err:
                print(f"  Status: FAILED ({err})")
                continue

            pre_token_balances = meta.get("preTokenBalances", [])
            post_token_balances = meta.get("postTokenBalances", [])
            
            # Find the token balances that changed for this wallet
            changes = []
            mints = set(b.get("mint") for b in pre_token_balances + post_token_balances)
            
            for mint in mints:
                if mint == "So11111111111111111111111111111111111111112":
                    # SOL/WSOL
                    continue
                pre_amt = 0.0
                post_amt = 0.0
                for b in pre_token_balances:
                    if b.get("owner") == wallet and b.get("mint") == mint:
                        pre_amt = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                for b in post_token_balances:
                    if b.get("owner") == wallet and b.get("mint") == mint:
                        post_amt = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                diff = post_amt - pre_amt
                if diff != 0:
                    changes.append((mint, diff, pre_amt, post_amt))

            # Also check native SOL change
            account_keys = [k.get("pubkey") if isinstance(k, dict) else k for k in tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])]
            if wallet in account_keys:
                idx = account_keys.index(wallet)
                pre_sol = meta.get("preBalances", [])[idx] / 1e9
                post_sol = meta.get("postBalances", [])[idx] / 1e9
                sol_diff = post_sol - pre_sol
                print(f"  SOL Change: {sol_diff:+.6f} SOL (Pre: {pre_sol:.6f}, Post: {post_sol:.6f})")

            for mint, diff, pre, post in changes:
                trade_direction = "BUY/INFLOW" if diff > 0 else "SELL/OUTFLOW"
                print(f"  Token: {mint} | {trade_direction}: {diff:+f} (Pre: {pre}, Post: {post})")

asyncio.run(main())
