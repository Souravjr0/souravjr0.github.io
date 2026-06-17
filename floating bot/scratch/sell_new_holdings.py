import asyncio
import os
import sys
import base64
import logging
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("SellNewHoldings")

async def sell_holdings():
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
            logger.info(f"\nProcessing {label} | Mint: {mint}...")
            
            # Fetch balance
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
                
            info = accounts[0]["account"]["data"]["parsed"]["info"]
            amount_str = info["tokenAmount"].get("amount")
            ui_amount = float(info["tokenAmount"].get("uiAmount") or 0)
            
            if ui_amount <= 0:
                logger.warning(f"Zero balance for mint {mint}. Skipping.")
                continue
                
            logger.info(f"Current balance: {ui_amount:,.2f} tokens (raw: {amount_str})")
            
            # 2. Try Jupiter Routing API with high slippage
            logger.info("Attempting sale via Jupiter Swap Routing API (30% Slippage)...")
            quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint={mint}&outputMint=So11111111111111111111111111111111111111112&amount={amount_str}&slippageBps=3000"
            
            try:
                q_resp = await http.get(quote_url)
                if q_resp.status_code == 200:
                    quote_data = q_resp.json()
                    expected_sol = float(quote_data.get("outAmount", 0)) / 1e9
                    logger.info(f"Jupiter Quote found! Expected output: {expected_sol:.6f} SOL")
                    
                    swap_url = "https://api.jup.ag/swap/v1/swap"
                    swap_payload = {
                        "quoteResponse": quote_data,
                        "userPublicKey": str(keypair.pubkey()),
                        "wrapAndUnwrapSol": True,
                        "prioritizationFeeLamports": 200000 # High prioritisation fee
                    }
                    
                    s_resp = await http.post(swap_url, json=swap_payload)
                    if s_resp.status_code == 200:
                        swap_data = s_resp.json()
                        tx_b64 = swap_data["swapTransaction"]
                        
                        raw_tx = base64.b64decode(tx_b64)
                        tx = VersionedTransaction.from_bytes(raw_tx)
                        
                        signed_tx = VersionedTransaction(tx.message, [keypair])
                        signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                        
                        logger.info("Broadcasting signed Jupiter swap transaction...")
                        broadcast_payload = {
                            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                            "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 5}]
                        }
                        
                        b_resp = await http.post(rpc_url, json=broadcast_payload)
                        tx_sig = b_resp.json().get("result")
                        if tx_sig:
                            logger.info(f"Jupiter Sale Transaction Broadcasted! Signature: {tx_sig}")
                        else:
                            logger.error(f"Broadcast failed: {b_resp.text}")
                    else:
                        logger.error(f"Jupiter Swap error: {s_resp.text}")
                else:
                    logger.warning(f"Jupiter Quote failed: {q_resp.text}")
            except Exception as e:
                logger.error(f"Jupiter sale exception: {e}")
                
            # Add delay to protect against Jupiter rate limiting
            logger.info("Sleeping for 3 seconds to avoid rate limiting...")
            await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(sell_holdings())
