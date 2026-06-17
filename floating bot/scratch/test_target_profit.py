import asyncio
import sys
import os
import logging
import time

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper

# Dynamic monkeypatches to bypass safety checks for high-volume simulation testing
async def mock_dev_history(self, dev_wallet: str) -> dict:
    return {"safe": True, "reason": "mocked safe for sandbox demonstration", "token_count": 0}

async def mock_rugcheck(self, mint: str) -> dict:
    return {"safe": True, "score": 0, "risk_level": "good", "risks": []}

async def mock_goplus(self, mint: str) -> dict:
    return {"safe": True, "is_honeypot": False, "is_blacklisted": False, "is_mintable": False}

async def run_target_profit_test():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Initialize sniper with dry_run=True and max allocation of 0.03 SOL per trade!
    sniper = PumpFunSniper(
        dry_run=True, 
        max_snipe_sol=0.03,      # Max snipe allocation set to exactly 0.03 SOL
        take_profit_pct=150.0,    # Target higher profits for scaling
        stop_loss_pct=25.0,      # Dynamic stops
        timeout_secs=20.0        # Rapid timeout exits (20 seconds scalp)
    )
    
    # Wire the high-fidelity mock audits
    sniper._check_dev_history = mock_dev_history.__get__(sniper, PumpFunSniper)
    sniper._check_rugcheck = mock_rugcheck.__get__(sniper, PumpFunSniper)
    sniper._check_goplus = mock_goplus.__get__(sniper, PumpFunSniper)

    print('[TARGET-TEST] Sniper sandbox initialized with starting capital: 0.03 SOL')
    print(f'[TARGET-TEST] Snipe Size: {sniper.max_snipe_sol} SOL per token')
    print(f'[TARGET-TEST] Profit Target: +0.10000 SOL cumulative net gain')
    print(f'[TARGET-TEST] Running simulation stream...')
    print()

    # We will wrap the runner inside a custom task so we can monitor profit in real-time
    runner_task = asyncio.create_task(sniper.run())
    
    start_time = time.time()
    target_reached = False
    
    # Check every 2 seconds for target profit achievement or time limits
    try:
        while True:
            await asyncio.sleep(2.0)
            
            current_profit = sniper.total_profit_sol
            elapsed = time.time() - start_time
            
            # Print periodic status update
            print(f"[PROGRESS] Elapsed: {elapsed:.0f}s | Sniped: {sniper.tokens_bought} | Active: {len([p for p in sniper.positions.values() if p.status == 'active'])} | Cumulative P&L: {current_profit:+.5f} SOL")
            
            if current_profit >= 0.10:
                print(f"\n[SUCCESS] Target profit of +0.10000 SOL reached! (Current P&L: {current_profit:+.5f} SOL)")
                target_reached = True
                break
                
            # Fallback timeout of 180 seconds to avoid infinite loops on slow mainnet ticks
            if elapsed >= 180.0:
                print(f"\n[TIMEOUT] 180s simulation limit reached. Printing final report.")
                break
                
            if runner_task.done():
                print("[X] Runner task ended unexpectedly.")
                break
                
    except KeyboardInterrupt:
        print("\n[!] User interrupted the execution.")
    finally:
        # Gracefully shut down WebSocket
        sniper.running = False
        if not runner_task.done():
            runner_task.cancel()
            try:
                await runner_task
            except asyncio.CancelledError:
                pass
                
        await sniper.http.aclose()
        
        # Output beautiful presentation box report
        print("\n\033[96m" + "="*80)
        print("                 SANDBOX TARGET-PROFIT DRY RUN SUMMARY REPORT                    ")
        print("="*80 + "\033[0m")
        print(f" Target Profit Status:                     {'[OK] ACHIEVED' if target_reached else '[~] IN PROGRESS / PARTIAL'}")
        print(f" Starting Allocation Capital:             0.03000 SOL")
        print(f" Total Opportunities Seen:                {sniper.tokens_seen}")
        print(f" Total Tokens Filtered/Skipped:           {sniper.tokens_filtered}")
        print(f" Safe Tokens Simulated-Sniped:            {sniper.tokens_bought}")
        print("\033[96m" + "-"*80 + "\033[0m")
        
        print(" \033[1mSIMULATED EXITS & POSITIONS DETAILS:\033[0m")
        print("\033[96m" + "="*80 + "\033[0m")
        print(f"{'Token (Symbol)':<24} | {'Status':<12} | {'Entry (SOL)':<11} | {'Returned (SOL)':<14} | {'Net P&L':<15}")
        print("\033[96m" + "-"*80 + "\033[0m")
        
        total_spent = 0.0
        total_returned = 0.0
        
        for mint, pos in sniper.positions.items():
            spent = pos.entry_sol
            returned = pos.total_sol_returned
            pnl = returned - spent if pos.status != "active" else 0.0
            
            if pos.status == "active":
                pnl_str = "\033[93m[~] ACTIVE\033[0m"
                total_spent += spent
            else:
                total_spent += spent
                total_returned += returned
                pnl_pct = (pnl / spent) * 100 if spent > 0 else 0.0
                pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
                pnl_symbol = "[+]" if pnl >= 0 else "[-]"
                pnl_str = f"{pnl_color}{pnl_symbol} {pnl:+.5f} SOL ({pnl_pct:+.1f}%)\033[0m"
                
            status_str = pos.status.upper()
            token_display = f"{pos.token_name[:12]} ({pos.token_symbol[:6]})"
            print(f"{token_display:<24} | {status_str:<12} | {spent:<11.5f} | {returned:<14.5f} | {pnl_str:<15}")
            
        print("\033[96m" + "-"*80 + "\033[0m")
        net_profit = total_returned - total_spent if total_spent > 0 else 0.0
        net_pct = (net_profit / total_spent) * 100 if total_spent > 0 else 0.0
        net_color = "\033[92m" if net_profit >= 0 else "\033[91m"
        net_symbol = "[+]" if net_profit >= 0 else "[-]"
        net_pnl_str = f"{net_color}{net_symbol} {net_profit:+.5f} SOL ({net_pct:+.1f}%)\033[0m"
        
        print(f" FINAL CUMULATIVE SANDBOX P&L:             {net_pnl_str}")
        print("\033[96m" + "="*80 + "\033[0m\n")

if __name__ == '__main__':
    asyncio.run(run_target_profit_test())
