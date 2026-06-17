import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

signatures = [
    "28nFUhFtRBEaKymwcvvPmwFFQRN32LiuSfR1fHwb3xDz4jPKu5qvEKWoVjevPAZNtS77XmHqwnF2ScpLdMqPhkZQ",
    "9X7qsd8qVK1xC1vrmeijQbSYRXs8Vb5W3kGexkdxuHYqJTcJqtjELNFgUwiq62ATjw3h6udDyj24AXR2umsBLH8",
    "5BbS7qKoUZN5imzAfxDEz9stAqG9uXnBTEb9NpdCz4EvdaE1UzB9MZqQ3yqmyqvt79VQXeX9SUTmtKRqETBstb52",
    "G534Fo2yot55FiDVsmNpVxvGUD8fPKEAwDD3t6nRtuxsriZViSaqdELdpw5479eXWUQCHu8DnHY6uMKToqQwXLT",
    "3sZiCyXhCnskUAqU1W2E3UoSiqPk9FE4XgTEGU3PD9m6m4s7L3CXgqkjSFgvCtBixv5JwUgriPMh5GGcoirWou4j",
    "25DEeetGHv2EYaWyjjphrAuRdRdGGeQoE4Y8wT1bwHeAAEU9BfuCgcUxEiVrXUca1itZgDBEXL2KPsNETNDFv9qZ",
    "33g7cZDB3QsPYrRUFpwMQ3FSSc89nH296HPRT3t6DzS6rpAhNwcXwBFbqYpAdqYBWJSUhj6219kgBTGSREfrexR4",
    "46X7BwhdJu9KBMUkKTPuizsE7b4SArLQ2yKnnRan3FXDrnZ93nXmoPJqoo5uHVSoeY8NVmnsGykXvU6j9mvU8bLF",
    "2pK4RpWX1Wb9JvUWRGnwkUGfYJrx1MBzuS393NC4VUq2WSM7ZSwoJ7j6QPzbco87Wmgn8heiLa65rpr52sFwHvJK",
    "5H16Ds89QVGU8QiRjEc6eUhpq8uRhuvGwi7KwxtWFARdiHU2Zp7vCSnfAiMiVbET7QBjSHoc8EWqryPXwLL18YJK",
    "yZCYRjMZvrEdeaNxkyintDPTdedDQXX55TU9ijBU4a6cowGZ1kzp6mX3Q5Qs3vfcPC12yzafM8QcuD3Nryg322f",
    "2RZeDT2dgSzFYvuUHWhVCpUs4MrhtHALTJZpBfKoEd41xtrVfeGmLcU3i1tDUwGE12bVPwoxnrBN8eWR4VCtDnUm",
    "5YWKUuL8j8hQVjQpvLdzXZcFwt4JHHsrbyjbZGHHzSTFpnfixU5kE2Mdsdqw1cE45ZhgKVx6FsGU3zuBv3PBnpzW",
    "5773XX9TbmPPnAqAvuMP3TQ5pkZAPUsRpKRg9t2pHGanJQqzb4MfN2thPDMneYVm21ea9rUfCgtdMPKadwornP86",
    "3uHdvu2DkvZbu9UsyzZsc1jZEXkBivFukyNNJeqvBQHGNVpBYDp12D94F87QTL2z28MmfUccTDPC8wRUQEfjJ1FG",
    "3sFQgXvaqFrbmtjFpdMzuM8BEjpBp8QQPMoyRKCDhYMEYro2W8ApaAkHQVG2Csk7XSWnUXEMR4Xkahcn8894RS6s",
    "5SFxNc44RMUp7Xjci2ehqzvvimLVS1Z8BH5T8fVmcnomEy9ST2GUtBCuKpG7Ru4uuATQzWERwXizyCpHtUQDjtTD",
    "3m8sDhGLbYQawSCRK87XADphUwZbtmQNjUzMxDYc6U3D3TBCxZMXKKifyhS6dU5vBHaknRM6DCD3M2GuzWCHGvf7",
    "3RifXnoNUwmcu2CZyJNeu6dLqSeF8cS1bTdCC7uzPw48cDGDFFrUphZpz4YT8EiQRqDFaq22twm1as6eNesGYXmN",
    "5gELYtZauLBizaGWuZF8Jwyv3G2TznNmp8p3vrTNaJCHku8ywWE2Dr6qAYCWsJt6QWtnBaMgMprj4V1myVRruNua"
]

async def inspect():
    async with httpx.AsyncClient() as client:
        for sig in signatures:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            resp = await client.post(url, json=payload)
            data = resp.json()
            if "error" in data:
                print(f"Error for {sig[:10]}...: {data['error']}")
                continue
            
            result = data.get("result")
            if not result:
                print(f"No result for {sig[:10]}...")
                continue
            
            meta = result.get("meta", {})
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])
            # Net SOL change for the wallet (index 0 usually, but let's check accountKeys)
            account_keys = result.get("transaction", {}).get("message", {}).get("accountKeys", [])
            wallet_index = -1
            wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
            
            for idx, acc in enumerate(account_keys):
                pub = acc.get("pubkey") if isinstance(acc, dict) else acc
                if pub == wallet_addr:
                    wallet_index = idx
                    break
            
            err = meta.get("err")
            if wallet_index != -1 and len(pre_balances) > wallet_index and len(post_balances) > wallet_index:
                sol_change = (post_balances[wallet_index] - pre_balances[wallet_index]) / 1e9
                print(f"Sig: {sig[:16]}... | Net SOL Change: {sol_change:+.6f} SOL | Slot: {result.get('slot')} | Success: {err is None}")
            else:
                print(f"Sig: {sig[:16]}... | Wallet not found or balance empty | Slot: {result.get('slot')} | Success: {err is None}")

asyncio.run(inspect())
