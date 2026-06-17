import asyncio
import httpx
from solders.pubkey import Pubkey

api_key = "1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
wallet_addr = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
duck_mint = "JDh9gvuWP1FmkJ7t37JXrvVLPQtKajKEs8s2D4rspump"
PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")

async def check():
    async with httpx.AsyncClient() as client:
        # Get SOL Balance
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getBalance",
            "params": [wallet_addr]
        })
        sol_bal = resp.json().get("result", {}).get("value", 0) / 1e9
        print(f"SOL Balance: {sol_bal:.8f} SOL")

        # Get Token-2022 accounts
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                wallet_addr,
                {"programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"},
                {"encoding": "jsonParsed"}
            ]
        })
        t22_accounts = resp.json().get("result", {}).get("value", [])
        duck_bal = 0.0
        for item in t22_accounts:
            info = item["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            print(f"Token-2022 Account | Mint: {mint} | Balance: {amount:,.2f}")
            if mint == duck_mint:
                duck_bal = amount

        # Derive bonding curve PDA
        mint_pubkey = Pubkey.from_string(duck_mint)
        bonding_curve, _ = Pubkey.find_program_address(
            [b"bonding-curve", bytes(mint_pubkey)],
            PUMP_PROGRAM
        )
        print(f"Bonding Curve PDA: {bonding_curve}")

        # Get bonding curve account info
        resp = await client.post(url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [str(bonding_curve), {"encoding": "base64"}]
        })
        acc_info = resp.json().get("result", {}).get("value")
        if not acc_info:
            print("Failed to fetch bonding curve state.")
            return

        import base64
        import struct
        data = base64.b64decode(acc_info["data"][0])
        # Decode pump.fun bonding curve structure:
        # 8 bytes discriminator, then virtualTokenReserves (u64), virtualSolReserves (u64), realTokenReserves (u64), realSolReserves (u64), tokenTotalSupply (u64), complete (bool)
        discriminator = data[:8]
        virtual_token_reserves = struct.unpack("<Q", data[8:16])[0]
        virtual_sol_reserves = struct.unpack("<Q", data[16:24])[0]
        real_token_reserves = struct.unpack("<Q", data[24:32])[0]
        real_sol_reserves = struct.unpack("<Q", data[32:40])[0]
        token_total_supply = struct.unpack("<Q", data[40:48])[0]
        complete = data[48] == 1
        
        # Price in SOL per token = virtual_sol_reserves / virtual_token_reserves
        # But token has 6 decimals, sol has 9 decimals
        price_sol = (virtual_sol_reserves / 1e9) / (virtual_token_reserves / 1e6)
        print(f"Virtual SOL Reserves: {virtual_sol_reserves / 1e9:.3f} SOL")
        print(f"Virtual Token Reserves: {virtual_token_reserves / 1e6:,.2f}")
        print(f"Current Price: {price_sol:.12f} SOL/token")
        
        # Entry calculation
        # Entry price was: 0.001 SOL / 145972.62 tokens = 6.8506e-9 SOL
        entry_price = 0.001 / 145972.62
        print(f"Entry Price:   {entry_price:.12f} SOL/token")
        
        if duck_bal > 0:
            current_value = duck_bal * price_sol
            pnl_pct = ((price_sol - entry_price) / entry_price) * 100
            print(f"Position Value: {current_value:.6f} SOL (P&L: {pnl_pct:+.2f}%)")
        else:
            print("No DUCK balance found in wallet.")

asyncio.run(check())
