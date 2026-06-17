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
logger = logging.getLogger("SellHoldings")

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
        ("Gw75Y2znwcBYZWGmXsByFCmAEKT7ojNQ7VLTf2BxgHFL", "Legacy SPL"),
        ("2eg9bHSdZMWiVwJMBdCiG6G72xhKwiv3sevyAsr5pump", "Pump.fun Token"),
        ("6fmPRN4YW661XXiaeY4cnaNJpMLgvdF9XW6FLvaprnRX", "Legacy SPL")
    ]

    async with httpx.AsyncClient(timeout=30.0) as http:
        for mint, label in mints_to_sell:
            logger.info(f"\nProcessing {label} | Mint: {mint}...")
            
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
                
            info = accounts[0]["account"]["data"]["parsed"]["info"]
            amount_str = info["tokenAmount"].get("amount")
            ui_amount = float(info["tokenAmount"].get("uiAmount") or 0)
            decimals = info["tokenAmount"].get("decimals", 6)
            
            if ui_amount <= 0:
                logger.warning(f"Zero balance for mint {mint}. Skipping.")
                continue
                
            logger.info(f"Current balance: {ui_amount:,.2f} tokens (raw: {amount_str})")
            
            sold_success = False
            
            # 2. Try Jupiter Routing API first
            logger.info("Attempting sale via Jupiter Swap Routing API...")
            quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint={mint}&outputMint=So11111111111111111111111111111111111111112&amount={amount_str}&slippageBps=300"
            
            try:
                q_resp = await http.get(quote_url)
                if q_resp.status_code == 200:
                    quote_data = q_resp.json()
                    expected_sol = float(quote_data.get("outAmount", 0)) / 1e9
                    logger.info(f"Jupiter Quote found! Expected output: {expected_sol:.6f} SOL")
                    
                    # Get swap transaction
                    swap_url = "https://api.jup.ag/swap/v1/swap"
                    swap_payload = {
                        "quoteResponse": quote_data,
                        "userPublicKey": str(keypair.pubkey()),
                        "wrapAndUnwrapSol": True,
                        "prioritizationFeeLamports": 50000
                    }
                    
                    s_resp = await http.post(swap_url, json=swap_payload)
                    if s_resp.status_code == 200:
                        swap_data = s_resp.json()
                        tx_b64 = swap_data["swapTransaction"]
                        
                        # Decode, sign, and broadcast
                        raw_tx = base64.b64decode(tx_b64)
                        tx = VersionedTransaction.from_bytes(raw_tx)
                        
                        # Compile signature
                        # In solders versioned transactions, Keypair can sign directly
                        # but we can import to_bytes_versioned to make sure signature is exact
                        from solders.message import to_bytes_versioned
                        sig = keypair.sign_message(to_bytes_versioned(tx.message))
                        signed_tx = VersionedTransaction(tx.message, [sig])
                        signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                        
                        # Broadcast
                        logger.info("Broadcasting signed Jupiter swap transaction to RPC...")
                        broadcast_payload = {
                            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                            "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
                        }
                        
                        b_resp = await http.post(rpc_url, json=broadcast_payload)
                        tx_sig = b_resp.json().get("result")
                        if tx_sig:
                            logger.info(f"Jupiter Sale Transaction Broadcasted! Signature: {tx_sig}")
                            sold_success = True
                        else:
                            logger.error(f"Broadcast failed: {b_resp.text}")
                    else:
                        logger.error(f"Jupiter Swap endpoint error: {s_resp.text}")
                else:
                    logger.warning(f"Jupiter Quote failed with status {q_resp.status_code}: {q_resp.text}")
            except Exception as e:
                logger.error(f"Jupiter sale exception: {e}")
                
            # 3. Fallback to PumpPortal API if Jupiter fails and it's a pump token
            if not sold_success:
                logger.info("Jupiter Swap unavailable or failed. Trying PumpPortal Trade API...")
                pumpportal_payload = {
                    "publicKey": str(keypair.pubkey()),
                    "action": "sell",
                    "mint": mint,
                    "amount": "100%",
                    "denominatedInSol": "false",
                    "slippage": 50,
                    "priorityFee": 0.001,
                    "pool": "pump"
                }
                
                try:
                    p_resp = await http.post("https://pumpportal.fun/api/trade-local", json=pumpportal_payload)
                    if p_resp.status_code == 200:
                        tx_bytes = p_resp.content
                        tx = VersionedTransaction.from_bytes(tx_bytes)
                        
                        signed_tx = VersionedTransaction(tx.message, [keypair])
                        signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
                        
                        logger.info("Broadcasting signed PumpPortal transaction to Helius RPC...")
                        broadcast_payload = {
                            "jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                            "params": [signed_b64, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
                        }
                        
                        b_resp = await http.post(rpc_url, json=broadcast_payload)
                        tx_sig = b_resp.json().get("result")
                        if tx_sig:
                            logger.info(f"PumpPortal Sale Transaction Broadcasted! Signature: {tx_sig}")
                            sold_success = True
                        else:
                            logger.error(f"Broadcast failed: {b_resp.text}")
                    else:
                        logger.error(f"PumpPortal API error: {p_resp.status_code} - {p_resp.text}")
                except Exception as e:
                    logger.error(f"PumpPortal sale exception: {e}")
                    
            if not sold_success:
                logger.error(f"Failed to sell mint {mint} through both Jupiter and PumpPortal.")

if __name__ == "__main__":
    asyncio.run(sell_holdings())
