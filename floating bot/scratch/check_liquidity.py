import asyncio
import httpx
from solders.pubkey import Pubkey

mints = [
    "GpcjAYxuH78B7nAWw3vmFktS1xMX7LbCeTKMDWRJpump",
    "EMEFxHBY99GNzQCvo3aY1CzWH9F6yJKBtBnsJgS8pump",
    "EVzkPwrdcxyYudz8NqfT83EgfAcvgCHSMkFPx8f6pump"
]

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
PUMPFUN_PROGRAM_ID = "6EF83uocEBtB7Kspn87K5VV34U6JAVm3Ca1AASXMphJj"

async def check():
    async with httpx.AsyncClient() as client:
        for mint in mints:
            print(f"\nMint: {mint}")
            
            # Derive bonding curve PDA
            try:
                mint_pubkey = Pubkey.from_string(mint)
                program_id = Pubkey.from_string(PUMPFUN_PROGRAM_ID)
                pda, _ = Pubkey.find_program_address(
                    [b"bonding-curve", bytes(mint_pubkey)],
                    program_id
                )
                bonding_curve = str(pda)
                print(f"  Bonding Curve PDA: {bonding_curve}")
                
                # Fetch PDA account info
                resp = await client.post(url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
                    "params": [bonding_curve, {"encoding": "base64"}]
                })
                
                result = resp.json().get("result", {}).get("value")
                if not result:
                    print("  PDA Account not found!")
                    continue
                    
                # Query token balance of the bonding curve (to see token reserves)
                # Fetch SOL balance of the bonding curve (reserves)
                resp_sol = await client.post(url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "getBalance",
                    "params": [bonding_curve]
                })
                sol_bal = resp_sol.json().get("result", {}).get("value", 0) / 1e9
                print(f"  SOL Reserves in Bonding Curve: {sol_bal:.6f} SOL")
                
            except Exception as e:
                print(f"  Error: {e}")

asyncio.run(check())
