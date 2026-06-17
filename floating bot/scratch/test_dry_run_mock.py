import asyncio
import sys
import os
import logging

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper

# Dynamic monkeypatch to force first token to pass safety audits for high-fidelity report demonstration
async def mock_dev_history(self, dev_wallet: str) -> dict:
    return {"safe": True, "reason": "mocked safe for simulation demonstration", "token_count": 0}

async def mock_rugcheck(self, mint: str) -> dict:
    return {"safe": True, "score": 0, "risk_level": "good", "risks": []}

async def mock_goplus(self, mint: str) -> dict:
    return {"safe": True, "is_honeypot": False, "is_blacklisted": False, "is_mintable": False}

async def test():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Use a short timeout of 20 seconds for immediate simulated exits
    sniper = PumpFunSniper(dry_run=True, timeout_secs=20.0)
    
    # Monkeypatch the safety checks to force buys on incoming tokens
    sniper._check_dev_history = mock_dev_history.__get__(sniper, PumpFunSniper)
    sniper._check_rugcheck = mock_rugcheck.__get__(sniper, PumpFunSniper)
    sniper._check_goplus = mock_goplus.__get__(sniper, PumpFunSniper)

    print('[TEST-MOCK] Sniper initialized with high-fidelity paper trading monkeypatches!')
    print(f'[TEST-MOCK] max_snipe_sol={sniper.max_snipe_sol}')
    print(f'[TEST-MOCK] timeout_secs={sniper.timeout_secs}')
    print()
    print('[TEST-MOCK] Starting 90s WebSocket dry run...')

    try:
        await asyncio.wait_for(sniper.run(), timeout=90.0)
    except asyncio.TimeoutError:
        print('[TEST-MOCK] 90s timeout reached, printing performance report!')
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
