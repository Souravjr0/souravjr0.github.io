import os
import sys
import time
import asyncio
from dotenv import load_dotenv
from solders.keypair import Keypair
from solana.rpc.api import Client
from colorama import Fore, Style, init

init(autoreset=True)
load_dotenv()

WALLET_PUBKEY = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
REQUIRED_SOL = 0.015  # Minimum threshold indicating the $3 deposit has landed

async def main():
    print("=" * 80)
    print("      [LIVE MAINNET DEPLOYMENT MONITORS] - cook45 & clack")
    print("=" * 80)
    print(f" Target Wallet: {Fore.GREEN}{WALLET_PUBKEY}")
    print(f" Minimum Deposit Threshold: {Fore.YELLOW}{REQUIRED_SOL} SOL (~$3.00)")
    print(" Status: Waiting for your transfer to land on-chain...")
    print("-" * 80)

    client = Client("https://api.mainnet-beta.solana.com")

    while True:
        try:
            bal_resp = client.get_balance(Keypair.from_base58_string(os.getenv("SOLANA_PRIVATE_KEY")).pubkey())
            current_sol = bal_resp.value / 1e9
            
            if current_sol >= REQUIRED_SOL:
                print(f"\n{Fore.GREEN}[DEPOSIT DETECTED] Balance: {current_sol:.5f} SOL! Transfer successful.")
                break
            else:
                sys.stdout.write(f"\rCurrent Balance: {current_sol:.5f} SOL | Checking again in 5s...")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"\r[RPC ERROR] {e}. Retrying...")
            sys.stdout.flush()
            
        await asyncio.sleep(5)

    print(f"\n{Fore.LIGHTCYAN_EX}[PROCEEDING TO LIVE MODE]{Style.RESET_ALL} Rewriting `.env` controls...")
    
    # Rewrite .env to set DRY_RUN=False
    env_path = ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    env_content = env_content.replace("DRY_RUN=True", "DRY_RUN=False")
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    print(f"{Fore.LIGHTGREEN_EX}[LIVE MAINNET ACTIVATED] DRY_RUN is now set to False in .env.")
    print(f"{Fore.RED}[WARNING] Real funds are now active. Max Snipe Size: 0.005 SOL per position.")
    print("Launching trading engines now...\n")
    
    # Launch the live bot
    process = await asyncio.create_subprocess_exec(
        sys.executable, "solana_bot.py",
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    await process.communicate()

if __name__ == "__main__":
    asyncio.run(main())
