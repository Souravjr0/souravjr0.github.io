import asyncio
import sys
import os
import logging

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper

async def test():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    sniper = PumpFunSniper(dry_run=True, timeout_secs=15.0)
    print(f'[TEST] Sniper initialized, dry_run={sniper.dry_run}')
    print(f'[TEST] max_snipe_sol={sniper.max_snipe_sol}')
    print(f'[TEST] timeout_secs={sniper.timeout_secs}')
    print(f'[TEST] take_profit_pct={sniper.take_profit_pct}%')
    print(f'[TEST] stop_loss_pct={sniper.stop_loss_pct}%')
    print()

    # Test RugCheck API with a known token
    print('[TEST] Testing RugCheck.xyz API...')
    result = await sniper._check_rugcheck('So11111111111111111111111111111111111111112')
    print(f'  RugCheck result: {result}')

    # Test GoPlus API
    print('[TEST] Testing GoPlus Security API...')
    result = await sniper._check_goplus('So11111111111111111111111111111111111111112')
    print(f'  GoPlus result: {result}')

    # Test dev history with a random wallet
    print('[TEST] Testing Dev History check...')
    result = await sniper._check_dev_history('11111111111111111111111111111111')
    print(f'  Dev history result: {result}')

    print()
    print('[TEST] All safety API checks completed successfully!')
    print('[TEST] Starting 45s WebSocket dry run...')

    try:
        # Run the sniper loop for 45 seconds using asyncio.wait_for
        await asyncio.wait_for(sniper.run(), timeout=45.0)
    except asyncio.TimeoutError:
        print('[TEST] 45s timeout reached, exiting cleanly!')
    finally:
        sniper.running = False
        await sniper.http.aclose()
        
        # Premium Performance Presentation Box
        print("\n\033[96m" + "="*80)
        print("               PUMP.FUN SNIPER HIGH-FIDELITY PAPER TRADING REPORT               ")
        print("="*80 + "\033[0m")
        print(f" Total Tokens Discovered (Opportunities):  {sniper.tokens_seen}")
        print(f" Malicious Tokens Filtered Out (Skipped):  {sniper.tokens_filtered}")
        print(f" Safe Tokens Sniped (Simulated Buys):      {sniper.tokens_bought}")
        print("\033[96m" + "-"*80 + "\033[0m")
        
        print(" \033[1mACTIVE & COMPLETED SIMULATED POSITIONS:\033[0m")
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
                # Even if active, count it in spent
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
        
        print(f" CUMULATIVE SIMULATED P&L:                {net_pnl_str}")
        print("\033[96m" + "="*80 + "\033[0m\n")

if __name__ == '__main__':
    asyncio.run(test())
