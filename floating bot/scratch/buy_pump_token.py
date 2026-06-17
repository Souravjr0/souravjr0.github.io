import os
import asyncio
import json
import base64
import httpx
import websockets
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from dotenv import load_dotenv
from colorama import init, Fore, Style

init(autoreset=True)

PUMPPORTAL_TRADE_API = "https://pumpportal.fun/api/trade-local"
WS_API = "wss://pumpportal.fun/api/data"

async def execute_buy(client, keypair, rpc_url, mint, sol_amount):
    print(f"\n{Fore.YELLOW}[PUMP-BUY]{Style.RESET_ALL} Preparing buy order for {sol_amount} SOL on {mint[:8]}...")
    
    payload = {
        "publicKey": str(keypair.pubkey()),
        "action": "buy",
        "mint": mint,
        "amount": sol_amount,
        "denominatedInSol": "true",
        "slippage": 25,
        "priorityFee": 0.0001,
        "pool": "pump",
    }
    
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(PUMPPORTAL_TRADE_API, json=payload, timeout=10.0)
        if resp.status_code != 200:
            print(f"{Fore.RED}[PUMP-BUY] PumpPortal API error: {resp.text}{Style.RESET_ALL}")
            return None
            
        tx_bytes = resp.content
        tx = VersionedTransaction.from_bytes(tx_bytes)
        signed_tx = VersionedTransaction(tx.message, [keypair])
        
        # Send raw transaction to Solana RPC
        encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
        send_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
        }
        
        send_resp = await http_client.post(rpc_url, json=send_payload, timeout=15.0)
        if send_resp.status_code == 200:
            result = send_resp.json()
            if "result" in result:
                sig = result["result"]
                print(f"{Fore.GREEN}[PUMP-BUY] SUCCESS! TX signature: {sig}{Style.RESET_ALL}")
                print(f"Solscan Link: https://solscan.io/tx/{sig}")
                return sig
            else:
                print(f"{Fore.RED}[PUMP-BUY] RPC error: {result.get('error')}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[PUMP-BUY] Failed to send TX: {send_resp.text}{Style.RESET_ALL}")
            
    return None

async def execute_sell(client, keypair, rpc_url, mint):
    print(f"\n{Fore.YELLOW}[PUMP-SELL]{Style.RESET_ALL} Preparing sell order for 100% of tokens on {mint[:8]}...")
    
    payload = {
        "publicKey": str(keypair.pubkey()),
        "action": "sell",
        "mint": mint,
        "amount": "100%",
        "denominatedInSol": "false",
        "slippage": 25,
        "priorityFee": 0.0001,
        "pool": "pump",
    }
    
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(PUMPPORTAL_TRADE_API, json=payload, timeout=10.0)
        if resp.status_code != 200:
            print(f"{Fore.RED}[PUMP-SELL] PumpPortal API error: {resp.text}{Style.RESET_ALL}")
            return None
            
        tx_bytes = resp.content
        tx = VersionedTransaction.from_bytes(tx_bytes)
        signed_tx = VersionedTransaction(tx.message, [keypair])
        
        encoded = base64.b64encode(bytes(signed_tx)).decode("utf-8")
        send_payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "sendTransaction",
            "params": [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}]
        }
        
        send_resp = await http_client.post(rpc_url, json=send_payload, timeout=15.0)
        if send_resp.status_code == 200:
            result = send_resp.json()
            if "result" in result:
                sig = result["result"]
                print(f"{Fore.GREEN}[PUMP-SELL] SUCCESS! TX signature: {sig}{Style.RESET_ALL}")
                print(f"Solscan Link: https://solscan.io/tx/{sig}")
                return sig
            else:
                print(f"{Fore.RED}[PUMP-SELL] RPC error: {result.get('error')}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[PUMP-SELL] Failed to send TX: {send_resp.text}{Style.RESET_ALL}")
            
    return None

async def main():
    load_dotenv(dotenv_path="../.env")
    rpc_url = os.getenv("HELIUS_RPC_URL")
    pkey_str = os.getenv("SOLANA_PRIVATE_KEY")
    
    if not pkey_str:
        print(f"{Fore.RED}[-] SOLANA_PRIVATE_KEY not found in .env!{Style.RESET_ALL}")
        return
        
    kp = Keypair.from_base58_string(pkey_str)
    wallet = str(kp.pubkey())
    
    print(f"{Fore.CYAN}=== PUMP.FUN LIVE $0.40 TEST TRADE ==={Style.RESET_ALL}")
    print(f"Wallet Address: {Fore.YELLOW}{wallet}{Style.RESET_ALL}")
    
    client = AsyncClient(rpc_url)
    
    # Check balance first
    bal_resp = await client.get_balance(kp.pubkey())
    bal_sol = bal_resp.value / 1e9
    print(f"SOL Balance: {Fore.GREEN}{bal_sol:.6f} SOL{Style.RESET_ALL}")
    
    if bal_sol < 0.005:
        print(f"{Fore.RED}[!] SOL Balance too low! You need at least 0.005 SOL (about $0.80) to cover rent, buy amount, and priority fees.{Style.RESET_ALL}")
        print(f"    Please run the swap script first: {Fore.YELLOW}python swap_usdc_to_sol.py{Style.RESET_ALL}")
        await client.close()
        return
        
    # Listen to WebSocket to find a newly minted token
    print(f"\nConnecting to PumpPortal WebSocket to sniff a new token...")
    async with websockets.connect(WS_API) as websocket:
        # Subscribe to new token creations
        payload = {"method": "subscribeNewToken"}
        await websocket.send(json.dumps(payload))
        print("Subscribed to new tokens. Waiting for a creation event...")
        
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            
            # Check if it's a token creation event
            if "mint" in data:
                mint = data["mint"]
                name = data.get("name", "Unknown")
                symbol = data.get("symbol", "UNK")
                print(f"\n{Fore.GREEN}[FOUND NEW TOKEN]{Style.RESET_ALL} {name} ({symbol})")
                print(f"Mint: {Fore.CYAN}{mint}{Style.RESET_ALL}")
                
                # Execute buy of 0.0025 SOL (~$0.40)
                sol_to_trade = 0.0025
                buy_sig = await execute_buy(client, kp, rpc_url, mint, sol_to_trade)
                
                if buy_sig:
                    # Wait 10 seconds to simulate holding or letting the cycle complete
                    hold_time = 10
                    print(f"\nHolding position for {hold_time} seconds...")
                    await asyncio.sleep(hold_time)
                    
                    # Execute sell
                    await execute_sell(client, kp, rpc_url, mint)
                
                break # Exit after one cycle
                
    await client.close()
    print(f"\n{Fore.CYAN}=== TEST CYCLE COMPLETED ==={Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
