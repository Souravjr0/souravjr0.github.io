import asyncio
import os
import sys
import base64
import logging
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction, Transaction
from solders.pubkey import Pubkey
from solders.hash import Hash
from spl.token.instructions import close_account, CloseAccountParams

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("ForceSellAll")

async def force_sell_and_reclaim():
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

    mints_to_sell = [
        ("GpcjAYxuH78B7nAWw3vmFktS1xMX7LbCeTKMDWRJpump", "Nietzschean Dog (DOG)"),
        ("EMEFxHBY99GNzQCvo3aY1CzWH9F6yJKBtBnsJgS8pump", "Hakimi"),
        ("EVzkPwrdcxyYudz8NqfT83EgfAcvgCHSMkFPx8f6pump", "$SMACK")
    ]

    async with httpx.AsyncClient(timeout=30.0) as http:
        for mint, label in mints_to_sell:
            logger.info(f"\n==================================================")
            logger.info(f"Processing {label} | Mint: {mint}")
            logger.info(f"==================================================")
            
            # 1. Fetch current token balance
            payload_token = {
                "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                "params": [
                    str(keypair.pubkey()),
                    {"mint": mint},
                    {"encoding": "jsonParsed"}
                ]
            }
            
            resp = await http.post(rpc_url, json=payload_token)
            accounts = resp.json().get("result", {}).get("value", [])
            
            if not accounts:
                logger.warning(f"No token account found for mint {mint}. Skipping.")
                continue
                
            ata_pubkey = accounts[0]["pubkey"]
            info = accounts[0]["account"]["data"]["parsed"]["info"]
            amount_str = info["tokenAmount"].get("amount")
            ui_amount = float(info["tokenAmount"].get("uiAmount") or 0)
            
            if ui_amount <= 0:
                logger.warning(f"Zero balance for mint {mint}. Attempting rent reclaim directly...")
                await reclaim_rent(http, rpc_url, keypair, mint, ata_pubkey)
                continue
                
            logger.info(f"Current balance: {ui_amount:,.2f} tokens (raw: {amount_str})")
            
            # Fetch Quote with retry loop for 429s
            quote_data = None
            for attempt in range(5):
                logger.info(f"Fetching Jupiter Quote (Attempt {attempt+1}/5, 99% Slippage)...")
                quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint={mint}&outputMint=So11111111111111111111111111111111111111112&amount={amount_str}&slippageBps=9900"
                
                try:
                    q_resp = await http.get(quote_url)
                    if q_resp.status_code == 200:
                        quote_data = q_resp.json()
                        break
                    elif q_resp.status_code == 429:
                        logger.warning("Jupiter Quote API returned 429. Sleeping for 4 seconds...")
                        await asyncio.sleep(4.0)
                    else:
                        logger.warning(f"Jupiter Quote error: {q_resp.text}")
                        break
                except Exception as e:
                    logger.error(f"Quote exception: {e}")
                    await asyncio.sleep(2.0)
            
            if not quote_data:
                logger.error(f"Failed to fetch quote for mint {mint}. Skipping swap, trying PumpPortal fallback...")
                await try_pumpportal_sell(http, rpc_url, keypair, mint, amount_str)
                continue
                
            expected_sol = float(quote_data.get("outAmount", 0)) / 1e9
            logger.info(f"Jupiter Quote succeeded! Expected output: {expected_sol:.6f} SOL")
            
            # Fetch Swap Transaction with retry loop for 429s
            swap_tx_b64 = None
            for attempt in range(5):
                logger.info(f"Fetching Jupiter Swap Tx (Attempt {attempt+1}/5)...")
                swap_url = "https://api.jup.ag/swap/v1/swap"
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(keypair.pubkey()),
                    "wrapAndUnwrapSol": True,
                    "prioritizationFeeLamports": 300000 # High priority fee to force landing
                }
                
                try:
                    s_resp = await http.post(swap_url, json=swap_payload)
                    if s_resp.status_code == 200:
                        swap_tx_b64 = s_resp.json()["swapTransaction"]
                        break
                    elif s_resp.status_code == 429:
                        logger.warning("Jupiter Swap API returned 429. Sleeping for 4 seconds...")
                        await asyncio.sleep(4.0)
                    else:
                        logger.error(f"Jupiter Swap error: {s_resp.text}")
                        break
                except Exception as e:
                    logger.error(f"Swap exception: {e}")
                    await asyncio.sleep(2.0)
            
            if not swap_tx_b64:
                logger.error(f"Failed to fetch swap transaction for mint {mint}. Trying PumpPortal fallback...")
                await try_pumpportal_sell(http, rpc_url, keypair, mint, amount_str)
                continue
                
            # Decode and sign
            raw_tx = base64.b64decode(swap_tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            signed_tx = VersionedTransaction(tx.message, [keypair])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            
            # Submit and wait
            logger.info("Broadcasting swap transaction...")
            broadcast_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
            }
            
            b_resp = await http.post(rpc_url, json=broadcast_payload)
            tx_sig = b_resp.json().get("result")
            
            if tx_sig:
                logger.info(f"Transaction Broadcasted! Signature: {tx_sig}")
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
                    logger.info("[SUCCESS] Token sold successfully!")
                    # Reclaim rent immediately!
                    await reclaim_rent(http, rpc_url, keypair, mint, ata_pubkey)
                else:
                    err_msg = status_val.get("err") if status_val else "Not confirmed / dropped"
                    logger.error(f"[FAILED] Swap transaction failed or dropped: {err_msg}")
            else:
                logger.error(f"Broadcast failed: {b_resp.text}")
                
            logger.info("Sleeping for 5 seconds before next token...")
            await asyncio.sleep(5.0)

async def try_pumpportal_sell(http, rpc_url, keypair, mint, amount_str):
    logger.info("Triggering PumpPortal Local API Fallback...")
    payload = {
        "publicKey": str(keypair.pubkey()),
        "action": "sell",
        "mint": mint,
        "amount": "100%",
        "denominatedInSol": "false",
        "slippage": 100,
        "priorityFee": 0.003,
        "pool": "pump"
    }
    try:
        p_resp = await http.post("https://pumpportal.fun/api/trade-local", json=payload)
        if p_resp.status_code == 200:
            tx_bytes = p_resp.content
            tx = VersionedTransaction.from_bytes(tx_bytes)
            signed_tx = VersionedTransaction(tx.message, [keypair])
            signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
            
            b_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
            }
            b_resp = await http.post(rpc_url, json=b_payload)
            tx_sig = b_resp.json().get("result")
            if tx_sig:
                logger.info(f"[SUCCESS] PumpPortal trade broadcasted! Sig: {tx_sig}")
                logger.info("Waiting 10 seconds for confirmation...")
                await asyncio.sleep(10.0)
            else:
                logger.error(f"PumpPortal Broadcast failed: {b_resp.text}")
        else:
            logger.error(f"PumpPortal API error: {p_resp.status_code}")
    except Exception as e:
        logger.error(f"PumpPortal fallback error: {e}")

async def reclaim_rent(http, rpc_url, keypair, mint, ata_pubkey):
    logger.info(f"Reclaiming 0.00204 SOL rent from Associated Token Account: {ata_pubkey}")
    try:
        # Fetch blockhash
        resp_bh = await http.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "confirmed"}]
        })
        blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
        if not blockhash_str:
            return
            
        inst = close_account(
            CloseAccountParams(
                program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                account=Pubkey.from_string(ata_pubkey),
                dest=keypair.pubkey(),
                owner=keypair.pubkey()
            )
        )
        tx = Transaction.new_signed_with_payer(
            [inst],
            keypair.pubkey(),
            [keypair],
            Hash.from_string(blockhash_str)
        )
        encoded = base64.b64encode(bytes(tx)).decode("utf-8")
        
        b_payload = {
            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
            "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
        }
        b_resp = await http.post(rpc_url, json=b_payload)
        tx_sig = b_resp.json().get("result")
        if tx_sig:
            logger.info(f"[RECLAIM-OK] Reclaimed rent signature: {tx_sig}")
        else:
            logger.error(f"[RECLAIM-FAIL] {b_resp.text}")
    except Exception as e:
        logger.error(f"Rent reclaim exception: {e}")

if __name__ == "__main__":
    asyncio.run(force_sell_and_reclaim())
