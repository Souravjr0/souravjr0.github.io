import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

IGNORE_TOKENS = {
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
}

async def main():
    wallet = "AVjEtg2ECYKXYeqdRQXvaaAZBjfTjYuSMTR4WLhKoeQN"
    print(f"Profiling historical performance for: {wallet}")

    async with httpx.AsyncClient() as client:
        # Fetch last 200 signatures
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet, {"limit": 200}]
        }
        resp = await client.post(RPC_HTTP, json=payload, timeout=10.0)
        signatures = [x["signature"] for x in resp.json().get("result", [])]
        print(f"Retrieved {len(signatures)} signatures. Parsing trades...")

        token_history = {}
        total_sol_fees = 0.0

        # Process in batches of 10 to avoid overloading RPC
        for k in range(0, len(signatures), 10):
            batch_sigs = signatures[k:k+10]
            tasks = []
            for sig in batch_sigs:
                payload_tx = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
                }
                tasks.append(client.post(RPC_HTTP, json=payload_tx, timeout=15.0))
            
            responses = await asyncio.gather(*tasks)
            
            for r in responses:
                if r.status_code != 200:
                    continue
                tx_data = r.json().get("result")
                if not tx_data:
                    continue
                
                meta = tx_data.get("meta", {})
                if not meta or meta.get("err"):
                    continue
                
                fee = meta.get("fee", 0) / 1e9
                total_sol_fees += fee
                
                account_keys = [key.get("pubkey") if isinstance(key, dict) else key for key in tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])]
                if wallet not in account_keys:
                    continue
                
                wallet_idx = account_keys.index(wallet)
                pre_sol = meta.get("preBalances", [])[wallet_idx] / 1e9
                post_sol = meta.get("postBalances", [])[wallet_idx] / 1e9
                sol_diff = post_sol - pre_sol
                
                pre_token_balances = meta.get("preTokenBalances", [])
                post_token_balances = meta.get("postTokenBalances", [])
                
                mints_in_tx = set(b.get("mint") for b in pre_token_balances + post_token_balances)
                for mint in mints_in_tx:
                    if mint in IGNORE_TOKENS:
                        continue
                    
                    pre_amt = 0.0
                    post_amt = 0.0
                    for b in pre_token_balances:
                        if b.get("owner") == wallet and b.get("mint") == mint:
                            pre_amt = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    for b in post_token_balances:
                        if b.get("owner") == wallet and b.get("mint") == mint:
                            post_amt = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    
                    token_diff = post_amt - pre_amt
                    if token_diff != 0:
                        if mint not in token_history:
                            token_history[mint] = {"sol_spent": 0.0, "token_balance": 0.0, "trades": 0}
                        
                        token_history[mint]["trades"] += 1
                        token_history[mint]["token_balance"] += token_diff
                        
                        if token_diff > 0: # Buy
                            token_history[mint]["sol_spent"] -= sol_diff
                        else: # Sell
                            token_history[mint]["sol_spent"] -= sol_diff

        print("\n--- Trading Report per Token (Approximation from last 200 transactions) ---")
        overall_realized_pnl = 0.0
        
        for mint, stats in token_history.items():
            bal = stats["token_balance"]
            sol_net = -stats["sol_spent"]
            trades = stats["trades"]
            
            if abs(bal) < 1.0e-3:
                status = "CLOSED"
                overall_realized_pnl += sol_net
                pnl_str = f"{sol_net:+.4f} SOL"
            else:
                status = f"OPEN (Bal: {bal:.2f})"
                pnl_str = f"{sol_net:+.4f} SOL net inflow/outflow"
                
            print(f"Token: {mint[:12]}... | Status: {status} | Trades: {trades} | Net PnL: {pnl_str}")
            
        print("\n--- Summary ---")
        print(f"Total Gas/Priority Fees: {total_sol_fees:.6f} SOL")
        print(f"Overall Realized PnL (Closed positions): {overall_realized_pnl:+.4f} SOL")

asyncio.run(main())
