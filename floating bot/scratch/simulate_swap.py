import asyncio
import os
import sys
import base64
import logging
import httpx
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("SimulateSwap")

async def simulate():
    load_dotenv()
    
    api_key = os.getenv("HELIUS_API_KEY")
    rpc_url = os.getenv("HELIUS_RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={api_key}")
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    
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

    mint = "EMEFxHBY99GNzQCvo3aY1CzWH9F6yJKBtBnsJgS8pump" # Hakimi
    
    async with httpx.AsyncClient(timeout=30.0) as http:
        # Fetch balance
        payload_token = {
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [str(keypair.pubkey()), {"mint": mint}, {"encoding": "jsonParsed"}]
        }
        resp = await http.post(rpc_url, json=payload_token)
        accounts = resp.json().get("result", {}).get("value", [])
        if not accounts:
            logger.error("No token account found!")
            return
            
        info = accounts[0]["account"]["data"]["parsed"]["info"]
        amount_str = info["tokenAmount"].get("amount")
        ui_amount = float(info["tokenAmount"].get("uiAmount") or 0)
        logger.info(f"Balance: {ui_amount} tokens (raw: {amount_str})")
        
        # Fetch Quote
        quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint={mint}&outputMint=So11111111111111111111111111111111111111112&amount={amount_str}&slippageBps=9900"
        q_resp = await http.get(quote_url)
        if q_resp.status_code != 200:
            logger.error(f"Quote failed: {q_resp.text}")
            return
        quote_data = q_resp.json()
        logger.info(f"Quote output: {float(quote_data.get('outAmount', 0)) / 1e9} SOL")
        
        # Fetch Swap Transaction
        swap_payload = {
            "quoteResponse": quote_data,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": 1000
        }
        s_resp = await http.post("https://api.jup.ag/swap/v1/swap", json=swap_payload)
        if s_resp.status_code != 200:
            logger.error(f"Swap failed: {s_resp.text}")
            return
        swap_tx_b64 = s_resp.json()["swapTransaction"]
        
        # Sign
        raw_tx = base64.b64decode(swap_tx_b64)
        tx = VersionedTransaction.from_bytes(raw_tx)
        signed_tx = VersionedTransaction(tx.message, [keypair])
        signed_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")
        
        # Simulate
        logger.info("Simulating transaction...")
        sim_payload = {
            "jsonrpc": "2.0", "id": 1, "method": "simulateTransaction",
            "params": [
                signed_b64,
                {"encoding": "base64", "replaceRecentBlockhash": True, "sigVerify": False}
            ]
        }
        sim_resp = await http.post(rpc_url, json=sim_payload)
        print("\nSimulation Result:")
        print(sim_resp.json())

if __name__ == "__main__":
    asyncio.run(simulate())
