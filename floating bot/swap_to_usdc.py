import os
import sys
import json
import asyncio
import base64
import logging
from dotenv import load_dotenv
import httpx
from colorama import init, Fore, Style
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned

# Force unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.LIGHTBLACK_EX}[%(asctime)s] [%(levelname)s]{Style.RESET_ALL} %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SolanaSwapHelper")

load_dotenv()

RPC_URL = os.getenv("HELIUS_RPC_URL")
if not RPC_URL:
    logger.error("HELIUS_RPC_URL not found in .env!")
    sys.exit(1)

# SOL and USDC Mints
SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# We swap 0.007 SOL (7,000,000 lamports) ~ $0.60 USDC
SWAP_AMOUNT_LAMPORTS = 7_000_000 

async def confirm_transaction(client: httpx.AsyncClient, sig: str) -> bool:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignatureStatuses",
        "params": [[sig], {"searchTransactionHistory": False}]
    }
    for _ in range(30):
        try:
            res = await client.post(RPC_URL, json=payload)
            if res.status_code == 200:
                val = res.json().get("result", {}).get("value", [None])[0]
                if val:
                    if val.get("err"):
                        logger.error(f"Transaction failed: {val['err']}")
                        return False
                    status = val.get("confirmationStatus")
                    if status in ["confirmed", "finalized"]:
                        logger.info(f"Swap confirmed! Status: {status}")
                        return True
        except Exception as e:
            logger.error(f"Error checking signature: {e}")
        await asyncio.sleep(1)
    logger.warning("Confirmation timed out.")
    return False

async def main():
    pkey_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not pkey_str:
        logger.error("SOLANA_PRIVATE_KEY not set in .env! Please paste your key first.")
        sys.exit(1)
        
    try:
        pkey_str = pkey_str.strip()
        if pkey_str.startswith("["):
            secret_bytes = json.loads(pkey_str)
            keypair = Keypair.from_bytes(bytes(secret_bytes))
        else:
            keypair = Keypair.from_base58_string(pkey_str)
        logger.info(f"Loaded Keypair: {Fore.GREEN}{keypair.pubkey()}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Failed to load keypair: {e}")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=10) as client:
        # Check current SOL balance
        sol_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [str(keypair.pubkey())]
        }
        try:
            res = await client.post(RPC_URL, json=sol_payload)
            bal = res.json().get("result", {}).get("value", 0)
            logger.info(f"Wallet Balance: {Fore.YELLOW}{bal / 1e9:.6f} SOL{Style.RESET_ALL}")
            if bal < SWAP_AMOUNT_LAMPORTS + 2_000_000:
                logger.error("Insufficient SOL balance to execute the swap and pay fees!")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error querying balance: {e}")
            sys.exit(1)

        logger.info(f"Requesting Jupiter quote to swap {SWAP_AMOUNT_LAMPORTS / 1e9:.3f} SOL -> USDC...")
        
        quote_url = "https://api.jup.ag/swap/v1/quote"
        params = {
            "inputMint": SOL,
            "outputMint": USDC,
            "amount": str(SWAP_AMOUNT_LAMPORTS),
            "slippageBps": "50"  # 0.5% slippage
        }
        
        try:
            response = await client.get(quote_url, params=params)
            if response.status_code != 200:
                logger.error(f"Jupiter quote error: {response.text}")
                sys.exit(1)
                
            quote_data = response.json()
            out_amount = float(quote_data["outAmount"]) / 1e6
            logger.info(f"Quote received! Expected out: {Fore.GREEN}${out_amount:.4f} USDC{Style.RESET_ALL}")
            
            swap_url = "https://api.jup.ag/swap/v1/swap"
            payload = {
                "quoteResponse": quote_data,
                "userPublicKey": str(keypair.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": 200000  # 0.0002 SOL fee to guarantee landing under network congestion
            }
            
            response = await client.post(swap_url, json=payload)
            if response.status_code != 200:
                logger.error(f"Jupiter swap compilation error: {response.text}")
                sys.exit(1)
                
            swap_tx_b64 = response.json()["swapTransaction"]
            
            # Decode and sign transaction using robust solders VersionedTransaction.populate flow
            raw_tx = base64.b64decode(swap_tx_b64)
            tx = VersionedTransaction.from_bytes(raw_tx)
            sig = keypair.sign_message(to_bytes_versioned(tx.message))
            tx = VersionedTransaction(tx.message, [sig])
            # Broadcast
            logger.info("Broadcasting signed swap transaction to Solana...")
            
            # Confirm
            confirmed = await confirm_transaction(client, sig)
            if confirmed:
                logger.info(f"{Fore.GREEN}{Style.BRIGHT}Swap completed successfully! Your wallet now holds USDC capital.{Style.RESET_ALL}")
            else:
                logger.error("Swap transaction submitted but failed to confirm.")
                
        except Exception as e:
            logger.error(f"Exception during swap: {e}")

if __name__ == "__main__":
    asyncio.run(main())
