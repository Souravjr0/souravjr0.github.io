import asyncio
import httpx

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
tx_sig = "54316mR2toM7AjFw4N6vKkFv5zUv6cR2f52x6JkHk9vS8N2dfnZtoMqHZ3vZ4B" # Let's get the full signature from the log or query signatures

async def inspect():
    async with httpx.AsyncClient() as client:
        sig = "3FwBCcLJbNJPTS8vR2iTFBVJhooSvwLGQCMYXz7Xv8eJgAMPu1YRZ3BZJ7koT1dKwJWYcMSRnniA5Xuw6uodxutM"
        resp_tx = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
            "params": [
                sig,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        })
        tx_data = resp_tx.json().get("result")
        if not tx_data:
            print("Transaction not found")
            return
        
        meta = tx_data.get("meta", {})
        account_keys = tx_data["transaction"]["message"]["accountKeys"]
        
        print("Accounts in transaction:")
        for idx, key_info in enumerate(account_keys):
            key = key_info["pubkey"] if isinstance(key_info, dict) else key_info
            print(f"  [{idx}] {key} (signer: {key_info.get('signer') if isinstance(key_info, dict) else '?'})")
            
        instructions = tx_data["transaction"]["message"]["instructions"]
        print("Instructions:")
        for idx, ix in enumerate(instructions):
            program = ix.get("program") or ix.get("programId")
            print(f"  Instruction {idx} | Program: {program}")
            if "accounts" in ix:
                print(f"    Accounts: {ix['accounts']}")
            if "data" in ix:
                print(f"    Data: {ix['data']}")
            if "parsed" in ix:
                print(f"    Parsed: {ix['parsed']}")
                
        # Also check inner instructions
        inner_instructions = meta.get("innerInstructions", [])
        if inner_instructions:
            print("Inner Instructions:")
            for inner in inner_instructions:
                for idx, ix in enumerate(inner.get("instructions", [])):
                    program = ix.get("program") or ix.get("programId")
                    print(f"    Inner Instruction {idx} | Program: {program}")
                    if "parsed" in ix:
                        print(f"      Parsed: {ix['parsed']}")

asyncio.run(inspect())
