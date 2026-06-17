import asyncio
import os
import sys
import base64
import logging
import httpx
import random
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.message import MessageV0
from solders.hash import Hash

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("JitoSellAll")

# Verified Active Jito Tip Accounts (queried directly from Jito Block Engine)
JITO_TIP_ACCOUNTS = [
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jcyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt"
]

def b58encode(v: bytes) -> str:
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(v, "big")
    result = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        result.append(alphabet[r])
    for b in v:
        if b == 0:
            result.append(alphabet[0])
        else:
            break
    result.reverse()
    return result.decode("ascii")

async def jito_sell_and_reclaim():
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
            logger.info(f"JITO Processing {label} | Mint: {mint}")
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
                logger.warning(f"Zero balance for mint {mint}. Skipping.")
                continue
                
            logger.info(f"Current balance: {ui_amount:,.2f} tokens (raw: {amount_str})")
            
            # Fetch Quote with retry loop
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
                logger.error(f"Failed to fetch quote for mint {mint}. Skipping.")
                continue
                
            expected_sol = float(quote_data.get("outAmount", 0)) / 1e9
            logger.info(f"Jupiter Quote succeeded! Expected output: {expected_sol:.6f} SOL")
            
            # Fetch Swap Transaction
            swap_tx_b64 = None
            for attempt in range(5):
                logger.info(f"Fetching Jupiter Swap Tx (Attempt {attempt+1}/5)...")
                swap_url = "https://api.jup.ag/swap/v1/swap"
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(keypair.pubkey()),
                    "wrapAndUnwrapSol": True,
                    "prioritizationFeeLamports": 1000 # Keep priority fee low since we tip Jito!
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
                logger.error(f"Failed to fetch swap transaction for mint {mint}. Skipping.")
                continue
                
            # --- Decode and sign Swap Transaction ---
            raw_tx = base64.b64decode(swap_tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            signed_tx = VersionedTransaction(tx.message, [keypair])
            swap_b58 = b58encode(bytes(signed_tx))
            
            # --- Get Latest Blockhash for Jito Tip transaction ---
            resp_bh = await http.post(rpc_url, json={
                "jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash", "params": [{"commitment": "confirmed"}]
            })
            blockhash_str = resp_bh.json().get("result", {}).get("value", {}).get("blockhash")
            if not blockhash_str:
                logger.error("Failed to fetch recent blockhash. Skipping.")
                continue
            recent_blockhash = Hash.from_string(blockhash_str)
            
            # --- Create Jito Tip transaction ---
            tip_account = random.choice(JITO_TIP_ACCOUNTS)
            tip_lamports = 100000 # 0.0001 SOL Jito tip to ensure validator speed delivery
            
            ix = transfer(
                TransferParams(
                    from_pubkey=keypair.pubkey(),
                    to_pubkey=Pubkey.from_string(tip_account),
                    lamports=tip_lamports
                )
            )
            msg = MessageV0.try_compile(
                keypair.pubkey(),
                [ix],
                [],
                recent_blockhash
            )
            tip_tx = VersionedTransaction(msg, [keypair])
            tip_b58 = b58encode(bytes(tip_tx))
            
            # --- Submit Bundle to Jito Block Engine ---
            logger.info(f"Submitting Jito Bundle with Swap + {tip_lamports} Lamport Tip to {tip_account}...")
            
            jito_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendBundle",
                "params": [
                    [swap_b58, tip_b58]
                ]
            }
            
            try:
                jito_resp = await http.post(
                    "https://mainnet.block-engine.jito.wtf/api/v1/bundles",
                    json=jito_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if jito_resp.status_code == 200:
                    bundle_uuid = jito_resp.json().get("result")
                    if bundle_uuid:
                        logger.info(f"[JITO BUNDLE ACCEPTED] UUID: {bundle_uuid}")
                        logger.info("Waiting 12 seconds for bundle to land...")
                        await asyncio.sleep(12.0)
                        
                        # Verify balance changes to confirm success
                        resp_verify = await http.post(rpc_url, json={
                            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
                            "params": [str(keypair.pubkey()), {"mint": mint}, {"encoding": "jsonParsed"}]
                        })
                        v_accounts = resp_verify.json().get("result", {}).get("value", [])
                        
                        if v_accounts:
                            v_amount = float(v_accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount") or 0)
                            if v_amount == 0:
                                logger.info(f"[SUCCESS] Jito swap landed on-chain!")
                                await reclaim_rent_direct(http, rpc_url, keypair, mint, ata_pubkey)
                            else:
                                logger.warning(f"[PENDING/FAILED] Balance still positive: {v_amount}. Jito bundle may have been discarded due to price competition.")
                        else:
                            logger.info(f"[SUCCESS] Token account closed. Bundle landed completely!")
                    else:
                        logger.error(f"[JITO BUNDLE REJECTED] {jito_resp.json().get('error')}")
                else:
                    logger.error(f"[JITO HTTP ERROR] {jito_resp.status_code} - {jito_resp.text}")
                    
            except Exception as e:
                logger.error(f"Jito submission exception: {e}")
                
            logger.info("Sleeping for 4 seconds before next token...")
            await asyncio.sleep(4.0)

async def reclaim_rent_direct(http, rpc_url, keypair, mint, ata_pubkey):
    logger.info(f"Closing empty token account {ata_pubkey} to reclaim rent...")
    try:
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
        tx = VersionedTransaction(MessageV0.try_compile(keypair.pubkey(), [inst], [], Hash.from_string(blockhash_str)), [keypair])
        signed_b64 = base64.b64encode(bytes(tx)).decode("utf-8")
        
        b_resp = await http.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
            "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
        })
        tx_sig = b_resp.json().get("result")
        if tx_sig:
            logger.info(f"[RECLAIM-OK] Rent reclaimed signature: {tx_sig}")
        else:
            logger.error(f"[RECLAIM-FAIL] {b_resp.text}")
    except Exception as e:
        logger.error(f"Rent reclaim error: {e}")

if __name__ == "__main__":
    asyncio.run(jito_sell_and_reclaim())
