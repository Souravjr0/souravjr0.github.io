import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"

sigs = [
    "3wSAZPV2nNF9dUt1zVdMvaad56hxoMPo76YDBW5C2eJoXwbpmqXZbJNZ8U6juCCg7cCNkbfnStLQqW7bsqGEa6m7",
    "5Pndiodn41exPJ2czvkwhFUDTyTQb9rCyoc8xm4jLmcnunUZc8L2Wx8tXgRZLrWMtLhZZyWkZdyau8APyYduGeJV"
]

async def check():
    async with httpx.AsyncClient() as client:
        # Check current token accounts (including Token2022)
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"},
                {"encoding": "jsonParsed"}
            ]
        })
        tk2022 = resp.json().get("result", {}).get("value", [])
        print(f"Total Token2022 Accounts: {len(tk2022)}")
        for item in tk2022:
            info = item["account"]["data"]["parsed"]["info"]
            print(f"  Token2022 Account: {item['pubkey']} | Mint: {info['mint']} | Balance: {info['tokenAmount'].get('uiAmount')}")

        for sig in sigs:
            print("\n" + "="*80)
            print(f"Transaction: {sig}")
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            })
            tx = resp.json().get("result")
            if not tx:
                print("Transaction not found!")
                continue
            
            meta = tx.get("meta", {})
            print(f"Slot: {tx.get('slot')} | Err: {meta.get('err')}")
            print("Log Messages:")
            for log in meta.get("logMessages", []):
                print(f"  {log}")

asyncio.run(check())
