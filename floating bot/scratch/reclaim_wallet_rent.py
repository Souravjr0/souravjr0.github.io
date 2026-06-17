#!/usr/bin/env python3
"""
Solana Wallet Rent Reclaimer — Manual Dust Reclaiming Tool
cook45 & clack // Systems & MEV

Scans your wallet for empty pump.fun token accounts and reclaims the locked 0.00204 SOL rent.
"""

import asyncio
import os
import sys
import logging
from colorama import Fore, Style, init

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper

async def main():
    init()
    
    # Configure logging to show clean output
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    print(f"""
{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}========================================================================
              SOLANA WALLET RENT RECLAIMER — DUST CLEANER
                 cook45 & clack // Systems & MEV
========================================================================{Style.RESET_ALL}
""")

    pkey = os.getenv("SOLANA_PRIVATE_KEY")
    if not pkey:
        print(f"{Fore.RED}[ERROR] SOLANA_PRIVATE_KEY not found in your .env file!{Style.RESET_ALL}")
        print("Please ensure your private key is set in .env to sign the reclaim transactions.")
        return

    # Initialize sniper in LIVE mode (dry_run=False) so we can reclaim on-chain
    sniper = PumpFunSniper(
        max_snipe_sol=0.005,
        dry_run=False
    )
    
    if not sniper.keypair:
        print(f"{Fore.RED}[ERROR] Failed to load keypair from SOLANA_PRIVATE_KEY!{Style.RESET_ALL}")
        return

    print(f"Target Wallet:  {Fore.GREEN}{sniper.keypair.pubkey()}{Style.RESET_ALL}")
    print("Initiating scan for empty pump.fun accounts holding locked rent...")
    print()

    # Run the reclaimer
    reclaimed = await sniper.reclaim_all_dust_accounts()
    
    print(f"""
{Fore.LIGHTMAGENTA_EX}========================================================================{Style.RESET_ALL}
{Fore.GREEN}[CLEANUP COMPLETE]{Style.RESET_ALL}
Total SOL Reclaimed & Returned to Wallet:  {Fore.LIGHTGREEN_EX}{reclaimed:.6f} SOL{Style.RESET_ALL}
{Fore.LIGHTMAGENTA_EX}========================================================================{Style.RESET_ALL}
""")
    
    await sniper.http.aclose()

if __name__ == '__main__':
    asyncio.run(main())
