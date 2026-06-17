import asyncio
import os
import sys
import base64
import logging
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.hash import Hash
from spl.token.instructions import burn, BurnParams, close_account, CloseAccountParams

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("BurnDustAndReclaim")

async def main():
    load_dotenv()
    
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

    # List of dust accounts to burn and reclaim rent
    dust_targets = [
        ("5H4voZhzySsVvwVYDAKku8MZGuYBC7cXaBKDPW4YHWW1", 9),
        ("poron2X7UwAgsiBCTFvxbjWvkFn5oJuNegMUb4Vnygs", 9),
        ("DvjbEsdca43oQcw2h3HW1CT7N3x5vRcr3QrvTUHnXvgV", 9),
        ("8aQSJYiUn5EC4BSdDSJoNEfKXTaV4WwwcgBp6UuzPdNV", 9)
    ]

    async with httpx.AsyncClient(timeout=30.0) as http:
        for attempt in range(5):
            logger.info(f"Attempting burn + reclaim (Attempt {attempt+1}/5)...")
            
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
            instructions = []
            
            for mint, decimals in dust_targets:
                # Fetch ATA
                payload_token = {
                    "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                    "params": [str(keypair.pubkey()), {"mint": mint}, {"encoding": "jsonParsed"}]
                }
                resp = await http.post(rpc_url, json=payload_token)
                accounts = resp.json().get("result", {}).get("value", [])
                
                if not accounts:
                    continue
                    
                ata_pubkey = accounts[0]["pubkey"]
                info = accounts[0]["account"]["data"]["parsed"]["info"]
                raw_amount = int(info["tokenAmount"].get("amount", "0"))
                
                if raw_amount > 0:
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
                    
                close_inst = close_account(
                    CloseAccountParams(
                        program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                        account=Pubkey.from_string(ata_pubkey),
                        dest=keypair.pubkey(),
                        owner=keypair.pubkey()
                    )
                )
                instructions.append(close_inst)

            if not instructions:
                logger.info("No instructions to execute. All dust cleared!")
                return
                
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
                    logger.info("Transaction confirmed! Rent reclaimed completely!")
                    break
                else:
                    err_msg = status_val.get("err") if status_val else "Not confirmed / dropped"
                    logger.warning(f"Reclaim transaction pending/failed: {err_msg}. Retrying...")
            else:
                logger.warning(f"Broadcast failed: {result.get('error')}. Retrying...")
                
            await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
