import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

signatures = [
    "5Pndiodn41exPJ2czvkwhFUDTyTQb9rCyoc8xm4jLmcnunUZc8L2Wx8tXgRZLrWMtLhZZyWkZdyau8APyYduGeJV",
    "3wSAZPV2nNF9dUt1zVdMvaad56hxoMPo76YDBW5C2eJoXwbpmqXZbJNZ8U6juCCg7cCNkbfnStLQqW7bsqGEa6m7",
    "53obLmgx3BaXyPn6Z6wvxUDkEkXVsMthh1VmQs3SwNZxb4Y9TjZfWFg2m8xfaLPoWUhgcBuaYNENVuDwN4Y5qAQi",
    "3FK9dKHC7GMxX3z5iv8UpCqwFfX7FczksggYkYoiC7wxm9M8RQnAsM1syKtnqk5QY14tjDZGLNLHEMyM6BTx6gqq",
    "HNMNXXTeWCas9RARVUSA28HC8MyTxFmVfsgzKQY2F9fvM4SGXU5jqUFTKUdSYdj7QRWF5ULWNcSY5deo49kZqbZ",
    "5PNNU3FFmy1qJXgXfma5Q42tmemUfc1gLvNap5XTVtPSkNNDX55DsVNjhXhqAEMmJh3TUNwdBgFxA9p33mnpymF",
    "Y8SioNWGDYHWr7yXS3UMyArsk4z73HWke2bZL1Xvz4QEey43185EULWd57oBDKVBahheSghyN7VzXpBVWiMvJhf",
    "25WTxFrMPrBUrrB25XsgFecEL4SBWL8Bdn6PsoqSa4ejyiJY3hGZfVkKq9vKuATrKv7fZA4Z3LyHQQjnQikdBr48",
    "3dffzkdvEebiYWrgU69cjgiC6321iTzXAoQpuDFVcoiXE77fn2ruaZuhBrjABFKsgtyV1dSffeDzaE3AkCWFRGgK",
    "2QMJMfcrCpqw57V2MmoKYfkVQ4sC8AxtG7JicCx4uqvVuUNramDdoRXxZWRqhQY3bMxfZth8K2fi17qDLH4fEaCP",
    "dGgdeyRJ4HCtTtCsgfyGWcBn3HVf8RpYx2XiDfyKRYmHDCV1X7ewCg32sUqru85d42fFmQmjG17T6W38NKutWpN",
    "QrGbAaL7GBNYUKVwqTFwnqirff3Ps9FBi8HQNb4ouBrT9R6UDHqJGzbdLfELgSoPRiwYFBeQshWkRLXgeripLzb",
    "PMKa2QWdaFQ1hqMyYdScAWb4fZn3kLBtkSpf37hfmb9EWSKhFAbK6o7Bnyf93n5GanrBG6pJPcn74a7P8JDmnpM",
    "2SjG6D91i2FEqbmxZ2c1REWrjJxzc4qf8UaN7rnRvE24KwHEEXrcWTjmt7q6oBchVrmt5WRJ8UitgqjXD8KJ6srB",
    "34qpbHaJZ7VqjnXV75oCg4fLByss75ARS9W74RQu98kaaAjkjTf4p5xqQEPfX5whADft4CPwi9UiGDRoy1reXkQc",
    "m6fNncWGyaeAWguJxAKSznSnHt7FveWgGAYCiCKNkPVP6TdEA8yFQhuHy7GkKhTozZQ78FZADVLNSJMYukaXgid",
    "eYhBeLCJZ3qwEB8RcjpZYmJzs4yr6EDpvMteru18WELJCt2mnv6V7Qt9vthFPxJ1yaKpmDGsiGqqgRiDwJKtybu",
    "3iruTHd3HNPRNHwzwHTLPcSwa3tTkCBBX5q3zAdejCz3LHiqcPpy9M9EtXib3zZWGtohDjJz5eb9BcW2ZnrHjewn",
    "22ZkwuKMKa6nvnvm9kZjBwvKT6WYfMEp7qELKQMpxykoCuhrRiamP7tQDpLxgEmGHdMd1MCrBpNZFNnADUphkVWr",
    "5Yr9s5iz1k5foNm1zeDe6jAmeYvoaMoqGZEcCoGmBDJC9mvPsgPJQNo2kXgihPdsUPXyYJpNhqG931hvY8AWHK2T"
]

async def check():
    async with httpx.AsyncClient() as client:
        print(f"{'Index':<5} | {'Signature':<15} | {'Net SOL Change':<18} | {'Success':<8} | {'Details / Logs'}")
        print("-" * 100)
        for idx, sig in enumerate(signatures):
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
            
            # Extract log messages for quick context
            logs = meta.get("logMessages", [])
            action_desc = "Unknown"
            token_balance_changes = []
            
            # Simple heuristic for action based on logs
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
            
            # Check pre/post token balances for the wallet
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
