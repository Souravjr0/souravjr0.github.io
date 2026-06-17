import asyncio
import httpx
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# Config
api_key = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
rpc_url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
ivy_mint = "9DUH5VBQdi4nzfTfq4ypFWb1TeAg4WTaDy4wGvDUpump"

async def main():
    if not private_key_str:
        print("[X] Error: SOLANA_PRIVATE_KEY not found in .env!")
        return

    # Load Keypair
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solders.pubkey import Pubkey
    try:
        key_bytes = base64.b64decode(private_key_str) if len(private_key_str) > 64 else bytes.fromhex(private_key_str)
        keypair = Keypair.from_bytes(key_bytes) if len(key_bytes) == 64 else Keypair.from_base58_string(private_key_str)
        pubkey = keypair.pubkey()
        print(f"[OK] Keypair loaded. Wallet: {pubkey}")
    except Exception as e:
        print(f"[X] Failed to load keypair: {e}")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch exact IVY token balance from correct Token-2022 program
        token_program_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
        payload_token = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                str(pubkey),
                {"programId": token_program_2022},
                {"encoding": "jsonParsed"}
            ]
        }
        
        resp = await client.post(rpc_url, json=payload_token)
        accounts = resp.json().get("result", {}).get("value", [])
        
        ivy_balance = 0.0
        ata_address = None
        for acc in accounts:
            info = acc["account"]["data"]["parsed"]["info"]
            if info["mint"] == ivy_mint:
                ivy_balance = float(info["tokenAmount"].get("uiAmount") or 0)
                ata_address = acc["pubkey"]
                break
                
        if ivy_balance <= 0 or not ata_address:
            print(f"[X] No IVY tokens found in wallet! Balance: {ivy_balance}")
            return
            
        print(f"[+] Found {ivy_balance:,.6f} IVY tokens in account {ata_address}")
        
        # 2. Build sell transaction via PumpPortal trade-local API
        print("[+] Requesting sell transaction from PumpPortal...")
        payload_sell = {
            "publicKey": str(pubkey),
            "action": "sell",
            "mint": ivy_mint,
            "amount": ivy_balance,
            "denominatedInSol": "false",
            "slippage": 50,
            "pool": "pump"
        }
        
        resp_sell = await client.post(
            "https://pumpportal.fun/api/trade-local",
            json=payload_sell
        )
        if resp_sell.status_code != 200:
            print(f"[X] PumpPortal API error: {resp_sell.status_code} - {resp_sell.text}")
            return
            
        tx_bytes = resp_sell.content
        tx = VersionedTransaction.from_bytes(tx_bytes)
        signed_tx = VersionedTransaction(tx.message, [keypair])
        encoded_tx = base64.b64encode(bytes(signed_tx)).decode("utf-8")
        
        # 3. Submit transaction to RPC
        print("[+] Submitting sell transaction to Helius RPC...")
        send_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [
                encoded_tx,
                {
                    "encoding": "base64",
                    "skipPreflight": True,
                    "maxRetries": 3
                }
            ]
        }
        
        resp_send = await client.post(rpc_url, json=send_payload)
        sig = resp_send.json().get("result")
        if not sig:
            print(f"[X] RPC error: {resp_send.json()}")
            return
            
        print(f"[+] Sell transaction submitted. Signature: {sig}")
        print("[*] Waiting for confirmation...")
        
        confirmed = False
        for attempt in range(15):
            await asyncio.sleep(1.0)
            status_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignatureStatuses",
                "params": [[sig]]
            }
            status_resp = await client.post(rpc_url, json=status_payload)
            status_data = status_resp.json().get("result", {}).get("value", [None])[0]
            if status_data:
                err = status_data.get("err")
                if err is None:
                    print("[OK] Sell transaction confirmed successfully on-chain!")
                    confirmed = True
                    break
                else:
                    print(f"[X] Transaction failed on-chain: {err}")
                    return
                    
        if not confirmed:
            print("[X] Transaction not confirmed after 15 seconds. It might land later.")
            return

        # 4. Close Token-2022 Account to reclaim the 0.002074 SOL rent
        print("[+] Reclaiming Token-2022 ATA rent...")
        from spl.token.instructions import close_account, CloseAccountParams
        
        bh_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getLatestBlockhash",
            "params": [{"commitment": "confirmed"}]
        }
        bh_resp = await client.post(rpc_url, json=bh_payload)
        recent_blockhash_str = bh_resp.json()["result"]["value"]["blockhash"]
        
        from solders.hash import Hash
        from solders.pubkey import Pubkey as SoldersPubkey
        from solders.message import MessageV0
        
        # Build close account instruction
        close_ix = close_account(
            CloseAccountParams(
                program_id=SoldersPubkey.from_string(token_program_2022),
                account=SoldersPubkey.from_string(ata_address),
                dest=pubkey,
                owner=pubkey,
                signers=[]
            )
        )
        
        msg = MessageV0.try_compile(
            pubkey,
            [close_ix],
            [],
            Hash.from_string(recent_blockhash_str)
        )
        
        close_tx = VersionedTransaction(msg, [keypair])
        encoded_close = base64.b64encode(bytes(close_tx)).decode("utf-8")
        
        close_send = await client.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [encoded_close, {"encoding": "base64", "skipPreflight": True}]
        })
        close_sig = close_send.json().get("result")
        if close_sig:
            print(f"[OK] Closed ATA successfully. Rent reclaimed! Sig: {close_sig}")
        else:
            print(f"[X] Failed to close account: {close_send.json()}")

if __name__ == "__main__":
    asyncio.run(main())
