import os
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    wallet = Pubkey.from_string("9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb")
    mint = Pubkey.from_string("6o4BHTTo7j9RgaSBWcnamvyzv2RAys8haFKRYBeJpump")
    
    # Deriving Associated Token Account (ATA)
    # ATA program ID: ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL
    # Token program ID: TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
    ata, _ = Pubkey.find_program_address(
        [bytes(wallet), bytes(Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")), bytes(mint)],
        Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    )
    
    print(f"Derived SemanticOS ATA: {ata}")
    client = AsyncClient(rpc_url)
    
    # Check if ATA exists
    info_resp = await client.get_account_info(ata)
    if info_resp.value is not None:
        print(f"ATA Exists!")
        print(f"ATA Lamports (Rent): {info_resp.value.lamports} lamports ({info_resp.value.lamports / 1e9:.6f} SOL)")
        
        # Check token balance
        bal_resp = await client.get_token_account_balance(ata)
        print(f"Token Balance: {bal_resp.value.ui_amount}")
    else:
        print("ATA does not exist!")
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
