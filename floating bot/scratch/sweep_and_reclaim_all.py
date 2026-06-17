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
logger = logging.getLogger("SweepAndReclaimAll")

async def main():
    # Load .env file from current directory or parent directory
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

    async with httpx.AsyncClient(timeout=30.0) as http:
        # Get all legacy token accounts
        logger.info("Scanning for legacy token accounts...")
        resp = await http.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                str(keypair.pubkey()),
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        })
        
        accounts = resp.json().get("result", {}).get("value", [])
        logger.info(f"Found {len(accounts)} legacy token accounts.")
        
        if not accounts:
            logger.info("No legacy token accounts found. Nothing to reclaim!")
            return
            
        instructions = []
        
        # Add compute unit price instruction for prioritization
        instructions.append(set_compute_unit_price(200_000))
        
        for acc in accounts:
            ata_pubkey = acc["pubkey"]
            info = acc["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            raw_amount = int(info["tokenAmount"].get("amount", "0"))
            decimals = int(info["tokenAmount"].get("decimals", 0))
            ui_amount = float(info["tokenAmount"].get("uiAmount") or 0)
            
            logger.info(f"Processing Account: {ata_pubkey} | Mint: {mint} | UI Balance: {ui_amount}")
            
            if raw_amount > 0:
                logger.info(f"  Adding burn instruction for {raw_amount} raw tokens...")
                burn_inst = burn(
                    BurnParams(
                        program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                        account=Pubkey.from_string(ata_pubkey),
                        mint=Pubkey.from_string(mint),
                        owner=keypair.pubkey(),
                        amount=raw_amount,
                        signers=[]
                    )
                )
                instructions.append(burn_inst)
                
            logger.info(f"  Adding close_account instruction for {ata_pubkey}...")
            close_inst = close_account(
                CloseAccountParams(
                    program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                    account=Pubkey.from_string(ata_pubkey),
                    dest=keypair.pubkey(),
                    owner=keypair.pubkey()
                )
            )
            instructions.append(close_inst)
            
        for attempt in range(5):
            logger.info(f"Attempting broadcast (Attempt {attempt+1}/5)...")
            
            # Fetch absolute freshest blockhash (processed commitment!)
            resp_bh = await http.post(rpc_url, json={
                "jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "processed"}]
            })
            blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash_str:
                logger.error("Failed to fetch blockhash. Retrying...")
                await asyncio.sleep(2.0)
                continue
                
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
                "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
            })
            
            result = b_resp.json()
            tx_sig = result.get("result")
            if tx_sig:
                logger.info(f"[SUCCESS] Reclaim Broadcasted! Sig: {tx_sig}")
                logger.info("Waiting 10 seconds for confirmation...")
                await asyncio.sleep(10.0)
                
                # Check status
                status_payload = {
                    "jsonrpc": "2.0", "id": 1, "method": "getSignatureStatuses",
                    "params": [[tx_sig]]
                }
                status_resp = await http.post(rpc_url, json=status_payload)
                status_val = status_resp.json().get("result", {}).get("value", [None])[0]
                
                if status_val and status_val.get("err") is None:
                    logger.info("Transaction confirmed! All accounts burned and closed, rent reclaimed completely!")
                    break
                else:
                    err_msg = status_val.get("err") if status_val else "Not confirmed / dropped"
                    logger.warning(f"Reclaim transaction pending/failed: {err_msg}. Retrying...")
            else:
                logger.warning(f"Broadcast failed: {result.get('error')}. Retrying...")
                
            await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
