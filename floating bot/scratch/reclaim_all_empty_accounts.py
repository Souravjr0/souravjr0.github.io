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
from spl.token.instructions import close_account, CloseAccountParams

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ReclaimAll")

async def reclaim():
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

    async with httpx.AsyncClient(timeout=30.0) as http:
        # 1. Fetch ALL legacy token accounts
        payload_token = {
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [
                str(keypair.pubkey()),
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        
        resp = await http.post(rpc_url, json=payload_token)
        accounts = resp.json().get("result", {}).get("value", [])
        
        logger.info(f"Found {len(accounts)} total token accounts.")
        
        dead_accounts = []
        for acct in accounts:
            pubkey = acct["pubkey"]
            info = acct["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount = float(info["tokenAmount"].get("uiAmount") or 0)
            
            if amount == 0:
                dead_accounts.append((mint, pubkey))
                logger.info(f"  Empty Account: {pubkey} | Mint: {mint}")
                
        if not dead_accounts:
            logger.info("No empty token accounts found to reclaim!")
            return
            
        logger.info(f"Closing {len(dead_accounts)} empty token accounts to reclaim rent (~{len(dead_accounts) * 0.00204:.5f} SOL)...")
        
        # Get recent blockhash
        payload_bh = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getLatestBlockhash",
            "params": [{"commitment": "confirmed"}]
        }
        resp_bh = await http.post(rpc_url, json=payload_bh)
        blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
        
        if not blockhash_str:
            logger.error("Failed to fetch latest blockhash.")
            return
            
        recent_blockhash = Hash.from_string(blockhash_str)
        
        # Batch closed accounts in chunks of 5 safely
        batch_size = 5
        for i in range(0, len(dead_accounts), batch_size):
            chunk = dead_accounts[i:i+batch_size]
            instructions = []
            
            for mint, ata in chunk:
                inst = close_account(
                    CloseAccountParams(
                        program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                        account=Pubkey.from_string(ata),
                        dest=keypair.pubkey(),
                        owner=keypair.pubkey()
                    )
                )
                instructions.append(inst)
                
            tx = Transaction.new_signed_with_payer(
                instructions,
                keypair.pubkey(),
                [keypair],
                recent_blockhash
            )
            
            encoded = base64.b64encode(bytes(tx)).decode("utf-8")
            
            broadcast_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "sendTransaction",
                "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
            }
            
            b_resp = await http.post(rpc_url, json=broadcast_payload)
            tx_sig = b_resp.json().get("result")
            if tx_sig:
                logger.info(f"Reclaim batch signature: {tx_sig}")
            else:
                logger.error(f"Reclaim batch failed: {b_resp.text}")
                
        logger.info("Reclaim operation completed successfully.")

if __name__ == "__main__":
    asyncio.run(reclaim())
