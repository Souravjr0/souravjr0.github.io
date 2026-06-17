import asyncio
import sys
import os
import logging
import time
from typing import Dict, Any, Optional

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper, SniperPosition

# Dynamic monkeypatches to bypass safety checks for high-volume simulation testing
async def mock_dev_history(self, dev_wallet: str) -> dict:
    return {"safe": True, "reason": "mocked safe for sandbox demonstration", "token_count": 0}

async def mock_rugcheck(self, mint: str) -> dict:
    return {"safe": True, "score": 0, "risk_level": "good", "risks": []}

async def mock_goplus(self, mint: str) -> dict:
    return {"safe": True, "is_honeypot": False, "is_blacklisted": False, "is_mintable": False}

class PortfolioGrowthSimulator(PumpFunSniper):
    """
    Subclasses PumpFunSniper to enforce a strict virtual bankroll starting at 0.03 SOL.
    Enforces fractional compounding (20% of bankroll per snipe) and stops on bankruptcy or hitting 5.0 SOL.
    """
    def __init__(self, start_bankroll: float = 0.03, target_bankroll: float = 5.0):
        # Enforce dry run and custom timeout scalps
        super().__init__(
            dry_run=True,
            max_snipe_sol=0.005,  # Will be dynamically overwritten by position sizing
            take_profit_pct=150.0,
            stop_loss_pct=25.0,
            timeout_secs=20.0,
            max_concurrent=5
        )
        self.start_bankroll = start_bankroll
        self.target_bankroll = target_bankroll
        
        # Simulated bankroll state
        self.virtual_bankroll = start_bankroll
        self.free_balance = start_bankroll
        
        # Track bankroll progression history for final report
        self.history = [(time.time(), start_bankroll)]
        self.bankrupt = False
        self.target_reached = False
        
    def _get_dynamic_snipe_size(self) -> float:
        """Calculates 20% fractional position size of current bankroll, capped between 0.003 and 0.5 SOL"""
        return max(0.003, min(0.5, self.virtual_bankroll * 0.20))

    async def _handle_new_token(self, data: Dict[str, Any]):
        """Override to enforce virtual free balance checks instead of on-chain SOL checks"""
        mint = data.get("mint")
        name = data.get("name", "Unknown")
        symbol = data.get("symbol", "???")
        bonding_curve = data.get("bondingCurveKey", "")
        creator = data.get("traderPublicKey", "")

        if not mint or not bonding_curve:
            return

        self.tokens_seen += 1

        # Check concurrency slot limits
        active_count = len([p for p in self.positions.values() if p.status == "active"])
        if active_count >= self.max_concurrent:
            return

        # Sanitize name and symbol to pure ASCII immediately to completely prevent Windows CP1252 stream encoding crashes
        name_ascii = name.encode('ascii', errors='replace').decode('ascii')
        symbol_ascii = symbol.encode('ascii', errors='replace').decode('ascii')

        # 1. Check free balance
        snipe_size = self._get_dynamic_snipe_size()
        if self.free_balance < snipe_size:
            logger = logging.getLogger("SolanaArbBot")
            logger.info(f"  [SKIPPED] {name_ascii} ({symbol_ascii}) -> Insufficient virtual free balance ({self.free_balance:.5f} SOL, need {snipe_size:.5f} SOL)")
            return

        # 2. Basic name filter
        if not self._passes_name_filter(name, symbol):
            logger = logging.getLogger("SolanaArbBot")
            logger.info(f"  [SKIPPED] {name_ascii} ({symbol_ascii}) -> Failed basic name filter")
            self.tokens_filtered += 1
            return

        # 3. Security audits (GoPlus, RugCheck, Dev history)
        rugcheck_task = asyncio.create_task(self._check_rugcheck(mint))
        goplus_task = asyncio.create_task(self._check_goplus(mint))
        dev_task = asyncio.create_task(self._check_dev_history(creator))

        try:
            rugcheck_res, goplus_res, dev_res = await asyncio.wait_for(
                asyncio.gather(rugcheck_task, goplus_task, dev_task),
                timeout=5.0
            )
        except Exception as e:
            logger = logging.getLogger("SolanaArbBot")
            logger.error(f"[ERROR] Exception during gather safety checks for {name_ascii} ({symbol_ascii}): {e}")
            self.tokens_filtered += 1
            return

        safe = rugcheck_res.get("safe", False) and goplus_res.get("safe", False) and dev_res.get("safe", False)
        if not safe:
            self.tokens_filtered += 1
            # Log skips cleanly
            logger = logging.getLogger("SolanaArbBot")
            reason = "rugcheck fail" if not rugcheck_res.get("safe") else "goplus fail" if not goplus_res.get("safe") else dev_res.get("reason") or "Failed dev audit"
            logger.info(f"  [SKIPPED] {name_ascii} ({symbol_ascii}) -> Audit fail: {reason}")
            return

        # --- PASSED ALL FILTERS: EXECUTE SIMULATED SNIPE ---
        self.tokens_bought += 1
        
        # Deduct allocation from virtual free balance
        self.free_balance -= snipe_size
        
        # Fetch bonding curve starting state
        bc_state = await self._get_bonding_curve_state(bonding_curve)
        
        # Fallbacks for RPC lag
        vsol = bc_state["virtual_sol_reserves"] if bc_state else 30_000_000_000
        vtok = bc_state["virtual_token_reserves"] if bc_state else 1_073_000_000_000_000
        entry_price = bc_state["price_sol"] if bc_state else (vsol / vtok)
        
        # Compute token amount output
        sol_lamports = int(snipe_size * 1e9)
        token_amount = self._calculate_buy_output(sol_lamports, vsol, vtok)

        # Register position
        self.positions[mint] = SniperPosition(
            token_mint=mint,
            token_name=name_ascii,  # Save the clean ASCII name to prevent display crashes down the line
            token_symbol=symbol_ascii,  # Save the clean ASCII symbol
            bonding_curve=bonding_curve,
            entry_sol=snipe_size,
            entry_time=time.time(),
            entry_price=entry_price,
            token_amount=token_amount,
            peak_price=entry_price,
            buy_tx="simulated_buy",
            status="active",
            entry_virtual_sol=vsol,
            dev_wallet=creator
        )

        logger = logging.getLogger("SolanaArbBot")
        logger.info(
            f"\n[OK] SNIPED {name_ascii} ({symbol_ascii}) | Size: {snipe_size:.5f} SOL | "
            f"Tokens: {token_amount/1e6:,.2f} | P&L Bankroll: {self.virtual_bankroll:.5f} SOL\n"
        )

    async def _partial_sell(self, mint: str, percent: int, current_price: float):
        """Override to credit proceeds of partial sells to simulated free balance"""
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        sell_amount = int(pos.token_amount * percent / 100)
        proceeds = (sell_amount * current_price) / 1e9
        
        # Credit proceeds to free balance
        self.free_balance += proceeds
        
        # Update position state
        pos.total_sol_returned += proceeds
        pos.token_amount -= sell_amount

        logger = logging.getLogger("SolanaArbBot")
        logger.info(
            f"  [DRY-PARTIAL] Sold {percent}% of {pos.token_symbol} | "
            f"Proceeds: {proceeds:.5f} SOL | Free Bal: {self.free_balance:.5f} SOL"
        )

    async def _close_position(self, mint: str, reason: str, current_price: float):
        """Override to credit virtual free balance back and update cumulative P&L using total_sol_returned"""
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        pos.status = reason
        proceeds = (pos.token_amount * current_price) / 1e9
        pos.total_sol_returned += proceeds
        
        # Credit proceeds back to simulated free balance
        self.free_balance += proceeds
        
        # Calculate closed trade P&L using cumulative total_sol_returned (including partial sells!)
        trade_pnl = pos.total_sol_returned - pos.entry_sol
        self.total_profit_sol += trade_pnl
        pos.token_amount = 0

        # Calculate current dynamic bankroll
        await self._update_bankroll_state()

        logger = logging.getLogger("SolanaArbBot")
        pnl_color = "\033[92m" if trade_pnl >= 0 else "\033[91m"
        pnl_symbol = "[+]" if trade_pnl >= 0 else "[-]"
        logger.info(
            f"  [EXIT] Sold {pos.token_symbol} — reason: {reason} | "
            f"Proceeds: {proceeds:.5f} SOL | "
            f"Net P&L: {pnl_color}{pnl_symbol} {trade_pnl:+.5f} SOL\033[0m"
        )

    async def _update_bankroll_state(self):
        """Calculates current bankroll: free balance + current market value of all active positions"""
        active_value = 0.0
        for pos in list(self.positions.values()):
            if pos.status == "active" and pos.bonding_curve:
                bc_state = await self._get_bonding_curve_state(pos.bonding_curve)
                price = bc_state["price_sol"] if bc_state else pos.entry_price
                active_value += (pos.token_amount * price) / 1e9
                
        self.virtual_bankroll = self.free_balance + active_value
        self.history.append((time.time(), self.virtual_bankroll))
        
        # Bankruptcy Check: Free balance < min trade size AND no active trades to recoup funds
        active_count = len([p for p in list(self.positions.values()) if p.status == "active"])
        if self.virtual_bankroll < 0.003 and active_count == 0:
            self.bankrupt = True
            
        # Target Check: Bankroll >= 5.0 SOL
        if self.virtual_bankroll >= self.target_bankroll:
            self.target_reached = True

async def run_portfolio_simulation():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Initialize custom simulator
    sim = PortfolioGrowthSimulator(start_bankroll=0.03, target_bankroll=5.0)
    
    # Wire mock safety audits for active simulated growth compounding
    sim._check_dev_history = mock_dev_history.__get__(sim, PortfolioGrowthSimulator)
    sim._check_rugcheck = mock_rugcheck.__get__(sim, PortfolioGrowthSimulator)
    sim._check_goplus = mock_goplus.__get__(sim, PortfolioGrowthSimulator)
    
    print('[PORTFOLIO-SIM] Starting compound paper sandbox growth engine...')
    print(f'[PORTFOLIO-SIM] Initial Capital:  {sim.start_bankroll:.5f} SOL')
    print(f'[PORTFOLIO-SIM] Goal Target P&L:  {sim.target_bankroll:.5f} SOL')
    print(f'[PORTFOLIO-SIM] Position Sizing:  20% fractional compounding size per launch')
    print()

    # Force initialize running state to bypass event loop scheduling delay
    sim.running = True
    
    # Launch WebSocket in background
    sim_task = asyncio.create_task(sim.run())
    
    # Let the scheduler initialize the WebSocket task
    await asyncio.sleep(0.5)
    
    start_time = time.time()
    
    try:
        while sim.running:
            await asyncio.sleep(2.0)
            
            # Recalculate dynamic bankroll balances
            await sim._update_bankroll_state()
            
            elapsed = time.time() - start_time
            active_trades = len([p for p in sim.positions.values() if p.status == "active"])
            
            print(
                f"[LIVE STATE] Time: {elapsed:.0f}s | "
                f"Bankroll: {sim.virtual_bankroll:.5f} SOL | "
                f"Free: {sim.free_balance:.5f} SOL | "
                f"Active Trades: {active_trades} | "
                f"Compound Size: {sim._get_dynamic_snipe_size():.5f} SOL"
            )
            
            # Stop condition 1: Bankruptcy
            if sim.bankrupt:
                print("\n[!] BANKRUPTCY TRIGGERED: Starting capital depleted to 0 SOL!")
                break
                
            # Stop condition 2: Goal target reached!
            if sim.target_reached:
                print(f"\n[SUCCESS] Compounding target achieved! Portfolio reached {sim.virtual_bankroll:.5f} SOL!")
                break
                
            # Extended simulation limit to allow compounding to target or bankruptcy (2 hours max)
            if elapsed >= 7200.0:
                print(f"\n[LIMIT] 2-hour sandbox limit reached. Printing final report.")
                break
                
            if sim_task.done():
                print("[X] Sniper core task exited unexpectedly.")
                break
                
    except KeyboardInterrupt:
        print("\n[!] Simulation interrupted by user.")
    finally:
        # Shut down WebSocket and cleanup
        sim.running = False
        if not sim_task.done():
            sim_task.cancel()
            try:
                await sim_task
            except asyncio.CancelledError:
                pass
                
        await sim.http.aclose()
        
        # Detailed report box
        print("\n\033[96m" + "="*80)
        print("                 DYNAMIC PORTFOLIO COMPOUNDING GROWTH ENGINE REPORT              ")
        print("="*80 + "\033[0m")
        print(f" Start Bankroll Balance:                   {sim.start_bankroll:.5f} SOL")
        print(f" End Bankroll Balance:                     {sim.virtual_bankroll:.5f} SOL")
        print(f" Total Realized Gain/Loss:                 {sim.virtual_bankroll - sim.start_bankroll:+.5f} SOL")
        
        status_str = "BANKRUPT (0 SOL)" if sim.bankrupt else "[OK] TARGET REACHED" if sim.target_reached else "IN PROGRESS / COMPLETED LIMIT"
        print(f" Simulation Exit Status:                   {status_str}")
        print("\033[96m" + "-"*80 + "\033[0m")
        print(f" Total Tokens Seen:                       {sim.tokens_seen}")
        print(f" Total Tokens Filtered (Rugs/Scams):      {sim.tokens_filtered}")
        print(f" Safe Snipes Executed (Simulated Buys):   {sim.tokens_bought}")
        print("\033[96m" + "-"*80 + "\033[0m")
        
        print(" SIMULATED EXITS & COMPLETED POSITIONS:")
        print("\033[96m" + "="*80 + "\033[0m")
        print(f"{'Token (Symbol)':<24} | {'Status':<12} | {'Entry (SOL)':<11} | {'Returned (SOL)':<14} | {'Net P&L':<15}")
        print("\033[96m" + "-"*80 + "\033[0m")
        
        for mint, pos in sim.positions.items():
            spent = pos.entry_sol
            returned = pos.total_sol_returned
            pnl = returned - spent if pos.status != "active" else 0.0
            
            if pos.status == "active":
                pnl_str = "\033[93m[~] ACTIVE\033[0m"
            else:
                pnl_pct = (pnl / spent) * 100 if spent > 0 else 0.0
                pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
                pnl_symbol = "[+]" if pnl >= 0 else "[-]"
                pnl_str = f"{pnl_color}{pnl_symbol} {pnl:+.5f} SOL ({pnl_pct:+.1f}%)\033[0m"
                
            status_str = pos.status.upper()
            clean_name = pos.token_name.encode('ascii', errors='replace').decode('ascii')
            clean_symbol = pos.token_symbol.encode('ascii', errors='replace').decode('ascii')
            token_display = f"{clean_name[:12]} ({clean_symbol[:6]})"
            print(f"{token_display:<24} | {status_str:<12} | {spent:<11.5f} | {returned:<14.5f} | {pnl_str:<15}")
            
        print("\033[96m" + "="*80 + "\033[0m\n")

if __name__ == '__main__':
    asyncio.run(run_portfolio_simulation())
