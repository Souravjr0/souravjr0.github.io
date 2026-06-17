import asyncio
import sys
import os
import logging
import time

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper

async def run_live_safety_test():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Initialize production PumpFunSniper (Dry-run mode, all real audits active!)
    sniper = PumpFunSniper(
        dry_run=True,
        max_snipe_sol=0.005,
        take_profit_pct=150.0,
        stop_loss_pct=25.0,
        timeout_secs=300.0,
        max_concurrent=1
    )

    print('================================================================================')
    print('  [LIVE SECURITY TEST] Starting Live Sniper with 100% Active On-Chain Audits...')
    print('                      cook45 & clack // Systems & MEV Security                 ')
    print('================================================================================')
    print('  Active Filters:')
    print('    - RugCheck.xyz Risk Audit:      ACTIVE (rejects high-risk tokens)')
    print('    - GoPlus Contract Honeypot:     ACTIVE (detects blacklists & freeze authority)')
    print('    - Helius RPC Dev History:       ACTIVE (flags serial rug launchers)')
    print('    - Strict Concurrency Limit:     MAX 1 active trade')
    print('    - Strict Micro-Sizing Sizer:    0.005 SOL per snipe ($0.80 max risk)')
    print('================================================================================\n')

    # Start sniper background monitor
    sniper.running = True
    monitor_task = asyncio.create_task(sniper.run())
    
    await asyncio.sleep(0.5)
    start_time = time.time()
    
    try:
        while sniper.running:
            await asyncio.sleep(2.0)
            elapsed = time.time() - start_time
            
            # Print live state status updates every 10 seconds
            if int(elapsed) % 10 == 0:
                print(
                    f"[LIVE AUDIT STATE] Elapsed: {elapsed:.0f}s | "
                    f"Launches Watched: {sniper.tokens_seen} | "
                    f"Filtered (Rugs Blocked): {sniper.tokens_filtered} | "
                    f"Safe Entries: {sniper.tokens_bought}"
                )
            
            # Let the test run for 180 seconds (3 minutes) to see real audits in action
            if elapsed >= 180.0:
                print("\n[LIMIT] 3-minute safety demonstration complete. Shutting down.")
                break
                
    except KeyboardInterrupt:
        print("\n[!] Demonstration interrupted.")
    finally:
        sniper.running = False
        if not monitor_task.done():
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        await sniper.http.aclose()
        
        print("\n================================================================================")
        print("                        SECURITY TEST AUDIT REPORT SUMMARY                      ")
        print("================================================================================")
        print(f" Total Tokens Seen on Launch Feed:        {sniper.tokens_seen}")
        print(f" Total High-Risk Scams/Rugs Blocked:     {sniper.tokens_filtered}")
        print(f" Total Safe Snipes Allowed:               {sniper.tokens_bought}")
        
        if sniper.tokens_seen > 0:
            blocked_pct = (sniper.tokens_filtered / sniper.tokens_seen) * 100
            print(f" Security Block Rate:                     {blocked_pct:.1f}% of launches blocked!")
        print("================================================================================\n")

if __name__ == '__main__':
    asyncio.run(run_live_safety_test())
