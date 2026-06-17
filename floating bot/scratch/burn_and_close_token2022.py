import asyncio
import os
import base64
import logging
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.hash import Hash
from spl.token.instructions import burn, BurnParams, close_account, CloseAccountParams
from solders.compute_budget import set_compute_unit_price

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("BurnAndCloseToken2022")

# Custom ATA derivation
def derive_ata(wallet: Pubkey, mint: Pubkey, program_id: Pubkey) -> Pubkey:
    ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    seeds = [
        bytes(wallet),
        bytes(program_id),
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

    token2022_program = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")

    async with httpx.AsyncClient(timeout=30.0) as http:
        instructions = [set_compute_unit_price(200_000)]
        has_elements = False
        
        for mint_str in mints:
            logger.info(f"\n--- Checking Mint: {mint_str} ---")
            mint_pubkey = Pubkey.from_string(mint_str)
            
            # Derive ATA using Token2022
            ata = derive_ata(keypair.pubkey(), mint_pubkey, token2022_program)
            
            # Query balance
            bal_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountBalance",
                "params": [str(ata)]
            }
            try:
                resp = await http.post(rpc_url, json=bal_payload)
                resp_json = resp.json()
                if "result" in resp_json:
                    val = resp_json["result"]["value"]
                    raw_amount = int(val.get("amount", "0"))
                    ui_amount = float(val.get("uiAmount") or 0)
                    logger.info(f"Found Token2022 ATA: {ata} | Balance: {ui_amount} ({raw_amount} raw)")
                    
                    if raw_amount > 0:
                        logger.info("  Adding Token2022 burn instruction...")
                        burn_inst = burn(
                            BurnParams(
                                program_id=token2022_program,
                                account=ata,
                                mint=mint_pubkey,
                                owner=keypair.pubkey(),
                                amount=raw_amount,
                                signers=[]
                            )
                        )
                        instructions.append(burn_inst)
                        has_elements = True
                        
                    logger.info("  Adding Token2022 close instruction...")
                    close_inst = close_account(
                        CloseAccountParams(
                            program_id=token2022_program,
                            account=ata,
                            dest=keypair.pubkey(),
                            owner=keypair.pubkey()
                        )
                    )
                    instructions.append(close_inst)
                    has_elements = True
            except Exception as e:
                logger.warning(f"Error reading ATA {ata}: {e}")
        
        if not has_elements:
            logger.info("No instructions built. Wiped already?")
            return
            
        logger.info("Broadcasting burn + close batch...")
        for attempt in range(5):
            try:
                resp_bh = await http.post(rpc_url, json={
                    "jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "processed"}]
                })
                blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
                recent_blockhash = Hash.from_string(blockhash_str)
                
                tx = Transaction.new_signed_with_payer(
                    instructions,
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
                    logger.info(f"[SUCCESS] Broadcasted! Sig: {sig}")
                    logger.info("Waiting 10 seconds for confirmation...")
                    await asyncio.sleep(10.0)
                    
                    # Verify status
                    status_payload = {
                        "jsonrpc": "2.0", "id": 1, "method": "getSignatureStatuses",
                        "params": [[sig]]
                    }
                    status_resp = await http.post(rpc_url, json=status_payload)
                    status_val = status_resp.json().get("result", {}).get("value", [None])[0]
                    
                    if status_val and status_val.get("err") is None:
                        logger.info("Transaction confirmed! Both Token2022 accounts burned and closed, rent reclaimed completely!")
                        break
                    else:
                        err_msg = status_val.get("err") if status_val else "Pending/Dropped"
                        logger.warning(f"Failed to confirm close batch: {err_msg}. Retrying...")
                else:
                    logger.error(f"Broadcast failed: {b_resp.json()}")
            except Exception as e:
                logger.error(f"Execution exception: {e}")
            await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
