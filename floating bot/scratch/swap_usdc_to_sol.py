import os
import asyncio
import httpx
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from dotenv import load_dotenv

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    pkey_str = os.getenv("SOLANA_PRIVATE_KEY")
    
    if not pkey_str:
        print("[-] Private key not found in .env!")
        return
        
    kp = Keypair.from_base58_string(pkey_str)
    wallet_address = str(kp.pubkey())
    print(f"Loaded Wallet: {wallet_address}")
    
    # 0.362363 USDC = 362363 units (6 decimals)
    amount = 362363 
    input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC
    output_mint = "So11111111111111111111111111111111111111112" # SOL
    
    print(f"\n1. Fetching quote from Jupiter Swap v2 with 10% slippage to swap {amount / 1e6:.6f} USDC to SOL...")
    # slippageBps=1000 means 10.0% slippage to ensure transaction lands even with high pool fee ratio on tiny amount
    quote_url = f"https://api.jup.ag/swap/v2/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps=1000"
    
    async with httpx.AsyncClient() as client:
        # Get quote
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        quote_resp = await client.get(quote_url, headers=headers)
        if quote_resp.status_code != 200:
            print(f"[-] Quote failed: {quote_resp.text}")
            return
            
        quote_data = quote_resp.json()
        out_amount = int(quote_data["outAmount"])
        print(f"[+] Quote Success! Expected SOL output: {out_amount / 1e9:.6f} SOL")
        
        # Get swap transaction
        print("\n2. Fetching swap transaction from Jupiter v2...")
        swap_url = "https://api.jup.ag/swap/v2/swap"
        swap_payload = {
            "quoteResponse": quote_data,
            "taker": wallet_address,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": 50000 
        }
        
        swap_resp = await client.post(swap_url, json=swap_payload, headers=headers)
        if swap_resp.status_code != 200:
            print(f"[-] Swap transaction request failed: {swap_resp.text}")
            return
            
        swap_data = swap_resp.json()
        swap_tx_b64 = swap_data["swapTransaction"]
        print("[+] Swap transaction retrieved successfully!")
        
        # Decode and sign transaction
        print("\n3. Decoding and signing transaction...")
        raw_tx = base64.b64decode(swap_tx_b64)
        tx = VersionedTransaction.from_bytes(raw_tx)
        
        # Sign it
        tx = VersionedTransaction(tx.message, [kp])
        
        # Send transaction directly via RPC POST with skipPreflight=True
        print("\n4. Sending transaction to Solana RPC (bypassing preflight simulation)...")
        signed_b64 = base64.b64encode(bytes(tx)).decode("utf-8")
        send_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [
                signed_b64,
                {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}
            ]
        }
        
        send_resp = await client.post(rpc_url, json=send_payload, timeout=15.0)
        if send_resp.status_code != 200:
            print(f"[-] RPC connection failed: {send_resp.text}")
            return
            
        result = send_resp.json()
        if "result" in result:
            tx_sig = result["result"]
            print(f"[+] Transaction sent! Signature: {tx_sig}")
            print(f"Solscan Link: https://solscan.io/tx/{tx_sig}")
            
            # Confirm transaction
            print("Waiting for transaction confirmation...")
            for i in range(10):
                await asyncio.sleep(3)
                confirm_payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[tx_sig]]
                }
                conf_resp = await client.post(rpc_url, json=confirm_payload)
                if conf_resp.status_code == 200:
                    status_data = conf_resp.json().get("result", {}).get("value", [None])[0]
                    if status_data is not None:
                        print(f"[+] Transaction status: {status_data}")
                        if status_data.get("confirmations") is not None or status_data.get("err") is None:
                            if status_data.get("err") is not None:
                                print(f"[-] Transaction confirmed but failed with error: {status_data.get('err')}")
                            else:
                                print("[+] SUCCESS: USDC -> SOL Swap completed!")
                            break
                print("  Retrying confirmation check...")
        else:
            print(f"[-] RPC Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
