import os
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    wallet_address = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
    
    print(f"Connecting to RPC: {rpc_url}")
    client = AsyncClient(rpc_url)
    pubkey = Pubkey.from_string(wallet_address)
    
    # 1. Get SOL Balance
    sol_resp = await client.get_balance(pubkey)
    sol_bal = sol_resp.value / 1e9
    print(f"SOL Balance: {sol_bal:.6f} SOL")
    
    # 2. Get SPL Token Accounts using TokenAccountOpts
    token_resp = await client.get_token_accounts_by_owner(
        pubkey,
        TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
    )
    
    print("\nToken Accounts:")
    for acc in token_resp.value:
        bal_resp = await client.get_token_account_balance(acc.pubkey)
        val = bal_resp.value
        # Let's get the token mint from the account info
        acc_info = await client.get_account_info(acc.pubkey)
        # The mint is typically in the first 32 bytes of the account data
        data = acc_info.value.data
        mint = ""
        if data:
            mint = str(Pubkey(data[:32]))
        print(f"  Account {acc.pubkey}:\n    Mint: {mint}\n    Amount: {val.amount}, Decimals: {val.decimals}, UI Amount: {val.ui_amount}")
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
