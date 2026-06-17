import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

async def check():
    async with httpx.AsyncClient() as client:
        # Get signatures for the wallet
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [
                wallet_addr,
                {"limit": 20}
            ]
        })
        signatures = resp.json().get("result", [])
        print(f"Recent {len(signatures)} transactions for {wallet_addr}:")
        for idx, sig_info in enumerate(signatures):
            sig = sig_info["signature"]
            err = sig_info.get("err")
            slot = sig_info.get("slot")
            memo = sig_info.get("memo")
            print(f"  {idx+1}. Sig: {sig} | Slot: {slot} | Err: {err} | Memo: {memo}")

asyncio.run(check())
