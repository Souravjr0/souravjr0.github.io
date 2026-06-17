import asyncio
import os
import base64
import logging
import httpx
import random
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction, Transaction
from solders.pubkey import Pubkey
from solders.hash import Hash
from spl.token.instructions import close_account, CloseAccountParams
from solders.compute_budget import set_compute_unit_price

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("SweepHoldings")

# Pure-python PDA derivation for Solana Associated Token Accounts (ATA)
def get_ata_address(wallet: Pubkey, mint: Pubkey) -> Pubkey:
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    seeds = [
        bytes(wallet),
        bytes(TOKEN_PROGRAM_ID),
        bytes(mint)
    ]
    ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
    return ata

async def main():
    load_dotenv(dotenv_path=".env")
    if not os.getenv("SOLANA_PRIVATE_KEY"):
        load_dotenv(dotenv_path="../.env")
        
    api_key = os.getenv("HELIUS_API_KEY")
    rpc_url = os.getenv("HELIUS_RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={api_key}")
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    
    if not private_key_str:
        logger.error("SOLANA_PRIVATE_KEY not found in .env!")
        return
        
    try:
        try:
            keypair = Keypair.from_base58_string(private_key_str)
        except Exception:
            key_bytes = base64.b64decode(private_key_str) if len(private_key_str) > 64 else bytes.fromhex(private_key_str)
            keypair = Keypair.from_bytes(key_bytes)
        logger.info(f"Loaded Wallet: {keypair.pubkey()}")
    except Exception as e:
        logger.error(f"Failed to load keypair: {e}")
        return

    mints = [
        "66ymmMo1ANuVzdcnrbJeAqJBzSM8xmADyF7Ske9Spump", # VEE3
        "84QndCmhnruNaKR5FGREAAjNshWbqd2CVK15Lg4Wpump"  # 1 riyal
    ]

    async with httpx.AsyncClient(timeout=30.0) as http:
        for mint_str in mints:
            logger.info(f"\n--- Sweeping Mint: {mint_str} ---")
            mint_pubkey = Pubkey.from_string(mint_str)
            
            # Derive ATA
            ata = get_ata_address(keypair.pubkey(), mint_pubkey)
            logger.info(f"Derived ATA: {ata}")
            
            # Query direct account balance
            bal_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountBalance",
                "params": [str(ata)]
            }
            try:
                resp = await http.post(rpc_url, json=bal_payload)
                resp_json = resp.json()
                if "error" in resp_json:
                    logger.warning(f"Account does not exist or has no state: {resp_json['error']}")
                    continue
                
                val = resp_json.get("result", {}).get("value", {})
                raw_amount = int(val.get("amount", "0"))
                ui_amount = float(val.get("uiAmount") or 0)
                logger.info(f"Direct Balance: {ui_amount} ({raw_amount} raw)")
                
                if raw_amount > 0:
                    logger.info("Attempting to sell holding via PumpPortal...")
                    sell_payload = {
                        "publicKey": str(keypair.pubkey()),
                        "action": "sell",
                        "mint": mint_str,
                        "amount": raw_amount,
                        "denominatedInSol": "false",
                        "slippage": 99,
                        "pool": "pump"
                    }
                    
                    sell_resp = await http.post("https://pumpportal.fun/api/trade-local", json=sell_payload)
                    if sell_resp.status_code == 200:
                        tx_bytes = sell_resp.content
                        tx = VersionedTransaction.from_bytes(tx_bytes)
                        signed_tx = VersionedTransaction(tx.message, [keypair])
                        encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                        
                        # Broadcast transaction
                        logger.info("Broadcasting sell transaction...")
                        b_resp = await http.post(rpc_url, json={
                            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                            "params": [encoded, {"encoding": "base64", "skipPreflight": True}]
                        })
                        sig = b_resp.json().get("result")
                        if sig:
                            logger.info(f"[SUCCESS] Sell broadcasted! Sig: {sig}")
                            logger.info("Waiting for sell confirmation...")
                            await asyncio.sleep(5.0)
                        else:
                            logger.error(f"Sell broadcast failed: {b_resp.json()}")
                    else:
                        logger.error(f"Failed to fetch sell payload: {sell_resp.text}")
                
            except Exception as e:
                logger.error(f"Error checking balance/selling: {e}")
                
            # Close Account instruction (reclaim rent)
            logger.info("Closing token account to reclaim 0.00204 SOL rent...")
            try:
                resp_bh = await http.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "processed"}]
                })
                blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
                recent_blockhash = Hash.from_string(blockhash_str)
                
                close_inst = close_account(
                    CloseAccountParams(
                        program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                        account=ata,
                        dest=keypair.pubkey(),
                        owner=keypair.pubkey()
                    )
                )
                
                tx = Transaction.new_signed_with_payer(
                    [set_compute_unit_price(200_000), close_inst],
                    keypair.pubkey(),
                    [keypair],
                    recent_blockhash
                )
                
                encoded = base64.b64encode(bytes(tx)).decode("utf-8")
                b_resp = await http.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                    "params": [encoded, {"encoding": "base64", "skipPreflight": True}]
                })
                sig = b_resp.json().get("result")
                if sig:
                    logger.info(f"[SUCCESS] Close Account Sig: {sig}")
                else:
                    logger.error(f"Close Account failed: {b_resp.json()}")
            except Exception as e:
                logger.error(f"Error closing account: {e}")
                
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(main())
