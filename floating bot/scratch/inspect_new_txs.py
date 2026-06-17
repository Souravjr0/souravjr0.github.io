import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

sigs = [
    "3m8sDhGLbYQawSCRK87XADphUwZbtmQNjUzMxDYc6U3D3TBCxZMXKKifyhS6dU5vBHaknRM6DCD3M2GuzWCHGvf7",
    "3RifXnoNUwmcu2CZyJNeu6dLqSeF8cS1bTdCC7uzPw48cDGDFFrUphZpz4YT8EiQRqDFaq22twm1as6eNesGYXmN",
    "5gELYtZauLBizaGWuZF8Jwyv3G2TznNmp8p3vrTNaJCHku8ywWE2Dr6qAYCWsJt6QWtnBaMgMprj4V1myVRruNua",
    "2AvmEKwnDzr927TtpJdRp4aMhhCDcWZvwT8ZxPNYTdjPtZirvUabGZskXiHXqbG1p66VBczSyZh3GSyupLQE3pjh",
    "w4vQA28GjdAcMD8FszsxHdhmt3CZzQySbmMAo6LoLT5TpUmnDwTmnASDH8ee6nhuf8DQBjmDNTCHHkCdf2QChK7",
    "Z1iv8UMf8fN8MLRbiqCez2jWMaGH2zvvsafPxJq8DVw4gb5uVwPAMJEu25SHDga3GEegt5VHXUcxzaCvmtL5zDY",
    "G1jt27WUrDJNJp8qwJLav3y4L5xoVUtzNfqM8SuFVv3hFvT61G454WPiPHGgrcDG8qu3WV6TAg64XF8tWwXBYWo"
]

async def check():
    async with httpx.AsyncClient() as client:
        print(f"{'Index':<5} | {'Signature':<15} | {'Net SOL Change':<18} | {'Success':<8} | {'Details / Logs'}")
        print("-" * 100)
        for idx, sig in enumerate(sigs):
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            resp = await client.post(url, json=payload)
            data = resp.json()
            if "error" in data:
                print(f"{idx+1:<5} | {sig[:12]}... | Error: {data['error'].get('message')}")
                continue
            
            result = data.get("result")
            if not result:
                print(f"{idx+1:<5} | {sig[:12]}... | No transaction result returned")
                continue
            
            meta = result.get("meta", {})
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            account_keys = result.get("transaction", {}).get("message", {}).get("accountKeys", [])
            
            wallet_idx = -1
            for k_idx, acc in enumerate(account_keys):
                pub = acc.get("pubkey") if isinstance(acc, dict) else acc
                if pub == wallet_addr:
                    wallet_idx = k_idx
                    break
            
            err = meta.get("err")
            success = "SUCCESS" if err is None else f"FAILED ({str(err)[:15]})"
            
            sol_change = 0.0
            if wallet_idx != -1 and len(pre_balances) > wallet_idx and len(post_balances) > wallet_idx:
                sol_change = (post_balances[wallet_idx] - pre_balances[wallet_idx]) / 1e9
            
            logs = meta.get("logMessages", [])
            action_desc = "Unknown"
            log_str = " ".join(logs)
            if "Program 6EF8rrect" in log_str or "6EF8rre1uTC1z6mthjgz6bxx9WRraH52wP4951479854" in log_str:
                if "buy" in log_str.lower() or "swap" in log_str.lower() or "execute" in log_str.lower():
                    action_desc = "Pump.fun Snipe / Swap"
                else:
                    action_desc = "Pump.fun interaction"
            elif "Program TokenkegQfe" in log_str or "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb" in log_str:
                if "closeaccount" in log_str.lower() or "close account" in log_str.lower():
                    action_desc = "Close Token Account (Rent Reclaim)"
                elif "burn" in log_str.lower():
                    action_desc = "Burn Tokens"
                else:
                    action_desc = "Token Program instruction"
            elif "Jito" in log_str or "JitoTip" in log_str or any("Jito" in str(x) for x in account_keys):
                action_desc = "Jito Bundle Tip"
            
            pre_token_bals = meta.get("preTokenBalances", [])
            post_token_bals = meta.get("postTokenBalances", [])
            token_mints = set()
            for tb in pre_token_bals + post_token_bals:
                if tb.get("owner") == wallet_addr:
                    token_mints.add(tb.get("mint"))
            
            mint_summary = ""
            if token_mints:
                mint_summary = "Tokens: " + ", ".join([m[:6] + ".." for m in token_mints])
            
            print(f"{idx+1:<5} | {sig[:12]}... | {sol_change:+.8f} SOL | {success:<15} | {action_desc} | {mint_summary}")

asyncio.run(check())
