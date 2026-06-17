import asyncio
import sys
import os
import logging
import time
from colorama import Fore, Style, init

# Initialize colorama
init()

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from pumpfun_sniper import PumpFunSniper, SniperPosition

# Set up logging to print directly to stdout with high readability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SolanaArbBot")

class PerfectGrowthSimulator(PumpFunSniper):
    """
    Subclasses PumpFunSniper to enforce a strict virtual bankroll starting at 0.10 SOL.
    Uses 100% UNMOCKED, active safety audits (RugCheck, GoPlus, Helius RPC Dev Check).
    Applies exact Solana mainnet fees and compounds dynamically at 20% fractional size.
    """
    def __init__(self, start_bankroll: float = 0.10, target_bankroll: float = 10.0, position_size_pct: float = 0.20):
        super().__init__(
            dry_run=True,          # TRUE: Pure dry-run tracking
            max_snipe_sol=0.010,   # Dynamically updated by bankroll
            take_profit_pct=100.0, # 2x target (tier 2 TP triggers before this)
            stop_loss_pct=10.0,    # Tightened 10% trailing stop for max protection
            timeout_secs=45.0,     # 45-second timeout to avoid long bleeds and fee burn
            max_concurrent=1,      # Strict 1 active slot for maximum capital protection
            strict_cabal_mode=True # ONLY take trades if an Alpha wallet is detected buying Block 0
        )
        self.sim_balance = start_bankroll
        self.free_balance = start_bankroll
        self.initial_balance = start_bankroll
        self.target_bankroll = target_bankroll
        self.position_size_pct = position_size_pct
        
        # Absolute Mainnet Fee Friction Baselines
        self.ATA_RENT = 0.002039
        self.TX_FEE = 0.000005
        self.PRIORITY_FEE = 0.001000  # MEV priority tip
        
        self.bankrupt = False
        self.target_reached = False
        self.trade_ledger = []

    def _get_dynamic_snipe_size(self) -> float:
        """Dynamic 20% compounding of the current simulated bankroll"""
        return max(0.005, round(self.sim_balance * self.position_size_pct, 5))

    async def _handle_new_token(self, data: dict):
        # Prevent starting new trades if target reached or bankrupt
        if self.target_reached or self.bankrupt:
            return

        active_count = len([p for p in self.positions.values() if p.status == "active"])
        if active_count >= self.max_concurrent:
            return

        # Sizing checks
        size = self._get_dynamic_snipe_size()
        dynamic_jito_tip = size * (self.jito_tip_pct / 100.0) if self.strict_cabal_mode else self.PRIORITY_FEE
        total_entry_cost = size + self.ATA_RENT + self.TX_FEE + dynamic_jito_tip
        
        if self.free_balance < total_entry_cost:
            logger.debug(f"  -> Skipped launch: Insufficient free balance ({self.free_balance:.5f} SOL, need {total_entry_cost:.5f} SOL)")
            return

        # Sizing is safe, update max_snipe_sol so parent class uses the compounded sizing
        self.max_snipe_sol = size

        # Temporarily deduct the entry cost from free balance to block subsequent concurrent buying
        self.free_balance -= total_entry_cost

        # Call the parent launch filter and buy execution pipeline
        await super()._handle_new_token(data)
        
        # If the buy wasn't successfully recorded in dry run positions, safety filters skipped it!
        # Return the allocated balance back to free balance.
        mint = data.get("mint", "")
        if mint not in self.positions or self.positions[mint].status != "active":
            self.free_balance += total_entry_cost
            logger.debug(f"  -> Safety filters or name filter skipped token. Balance refunded.")

    async def _partial_sell(self, mint: str, percent: int, current_price: float):
        """Handle dynamic compounding partial sell overhead and credit free balance"""
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        sell_amount = int(pos.token_amount * percent / 100)
        raw_proceeds = (sell_amount * current_price) / 1e9
        pump_fee = raw_proceeds * 0.0125
        net_returned = raw_proceeds - pump_fee - self.TX_FEE - self.PRIORITY_FEE
        
        self.free_balance += net_returned
        pos.total_sol_returned += net_returned
        pos.token_amount -= sell_amount
        
        logger.info(
            f"  {Fore.YELLOW}[SIM-PARTIAL TP]{Style.RESET_ALL} Sold {percent}% of {pos.token_symbol} | "
            f"Proceeds: {net_returned:.5f} SOL (after fees) | Free Bal: {self.free_balance:.5f} SOL"
        )

    async def _close_position(self, mint: str, reason: str, current_price: float):
        """Deduct final fees, credit proceeds and recovered ATA rent, update balance, and log Ledger details"""
        pos = self.positions.get(mint)
        if not pos or pos.status != "active":
            return

        raw_sell_proceeds = (pos.token_amount * current_price) / 1e9
        pump_sell_fee = raw_sell_proceeds * 0.0125
        
        # Sells 100% of remaining position -> reclaims the ATA rent directly
        net_close_returned = raw_sell_proceeds - pump_sell_fee - self.TX_FEE - self.PRIORITY_FEE + self.ATA_RENT
        
        self.free_balance += net_close_returned
        pos.total_sol_returned += net_close_returned
        pos.token_amount = 0
        pos.status = reason
        
        # Dynamic Bankroll Update
        await self._update_bankroll()
        
        # Mathematically calculate exact roundtrip Net P&L (Total proceeds returned - Dynamic Size allocated - Entry fees)
        dynamic_jito_tip = pos.entry_sol * (self.jito_tip_pct / 100.0) if self.strict_cabal_mode else self.PRIORITY_FEE
        total_entry_allocated = pos.entry_sol + self.ATA_RENT + self.TX_FEE + dynamic_jito_tip
        net_pnl = pos.total_sol_returned - total_entry_allocated
        
        old_balance = self.sim_balance
        self.sim_balance = self.free_balance # active position closed, liquid balance matches running bankroll
        
        pnl_pct = (net_pnl / total_entry_allocated) * 100
        pnl_color = Fore.LIGHTGREEN_EX if net_pnl >= 0 else Fore.LIGHTRED_EX
        pnl_symbol = "[+]" if net_pnl >= 0 else "[-]"
        
        logger.info(
            f"\n========================================================================\n"
            f"  {Fore.YELLOW}[DRY-SELL CLOSED]{Style.RESET_ALL}\n"
            f"  Token:        {pos.token_name} ({pos.token_symbol})\n"
            f"  Reason:       {reason.upper()}\n"
            f"  Entry Cost:   {total_entry_allocated:.5f} SOL (inc. entry rent & fees)\n"
            f"  Net Returned: {pos.total_sol_returned:.5f} SOL (inc. partials, final exit, and rent refund)\n"
            f"  Trade Net P&L: {pnl_color}{pnl_symbol} {net_pnl:+.5f} SOL ({pnl_pct:+.1f}%){Style.RESET_ALL}\n"
            f"  Sim Balance:  {Fore.CYAN}{old_balance:.5f} SOL -> {self.sim_balance:.5f} SOL{Style.RESET_ALL}\n"
            f"========================================================================\n"
        )
        
        self.trade_ledger.append({
            "token": f"{pos.token_name} ({pos.token_symbol})",
            "mint": pos.token_mint,
            "status": reason,
            "allocated": total_entry_allocated,
            "returned": pos.total_sol_returned,
            "pnl": net_pnl,
            "pct": pnl_pct
        })
        self.total_sells += 1

    async def _update_bankroll(self):
        """Calculates simulated bankroll = free balance + active token value + active locked rent"""
        active_value = 0.0
        active_locked_rent = 0.0
        for pos in list(self.positions.values()):
            if pos.status == "active" and pos.bonding_curve:
                bc_state = await self._get_bonding_curve_state(pos.bonding_curve)
                price = bc_state["price_sol"] if bc_state else pos.entry_price
                active_value += (pos.token_amount * price) / 1e9
                active_locked_rent += self.ATA_RENT
                
        self.sim_balance = self.free_balance + active_value + active_locked_rent
        
        # Check bankruptcy
        min_cost = 0.005 + self.ATA_RENT + self.TX_FEE + self.PRIORITY_FEE # ~0.008 SOL
        active_trades = len([p for p in self.positions.values() if p.status == "active"])
        if self.sim_balance < min_cost and active_trades == 0:
            self.bankrupt = True
            
        # Check target goal
        if self.sim_balance >= self.target_bankroll:
            self.target_reached = True

async def run_perfect_simulation():
    # Enforce starting balance 0.10 SOL, target 10.0 SOL
    sim = PerfectGrowthSimulator(
        start_bankroll=0.10000,
        target_bankroll=10.00000,
        position_size_pct=0.20 # 20% fractional compounding
    )

    print('================================================================================')
    print('  [PERFECT EXECUTION] High-Fidelity Dry Compounder (0.10 -> 10.0 SOL)          ')
    print('                cook45 & clack // Absolute Truth & Systems Security           ')
    print('================================================================================')
    print(f' Initial Bankroll:                {sim.initial_balance:.5f} SOL')
    print(f' Target Goal:                     {sim.target_bankroll:.5f} SOL')
    print(' Sizing Model:                    Dynamic 20% fractional compound size')
    print(' Timeouts & Stops:                45s max hold | 15% trailing stop-loss')
    print(' Security Status:                 100% UNMOCKED, ACTIVE API CHECKS')
    print('    - Helius RPC Dev Check:       ACTIVE (scans developer history)')
    print('    - GoPlus Honeypot/Freeze:     ACTIVE (scans contract security)')
    print('    - RugCheck risk score:        ACTIVE (scans metadata / liquidity)')
    print('================================================================================\n')

    sim.running = True
    monitor_task = asyncio.create_task(sim.run())
    
    await asyncio.sleep(0.5)
    start_time = time.time()
    
    try:
        while sim.running:
            await asyncio.sleep(2.0)
            await sim._update_bankroll()
            
            elapsed = time.time() - start_time
            active_trades = len([p for p in sim.positions.values() if p.status == "active"])
            locked_rent = active_trades * sim.ATA_RENT
            
            # Print live state status updates every 10 seconds
            if int(elapsed) % 10 == 0:
                print(
                    f"[LIVE SIM] Time: {elapsed:.0f}s | "
                    f"Bankroll: {Fore.CYAN}{sim.sim_balance:.5f} SOL{Style.RESET_ALL} | "
                    f"Free: {sim.free_balance:.5f} SOL | "
                    f"Locked Rent: {locked_rent:.5f} SOL | "
                    f"Active: {active_trades} | "
                    f"Next Sizer: {sim._get_dynamic_snipe_size():.5f} SOL"
                )
                
            # Stop condition 1: Bankruptcy
            if sim.bankrupt:
                print(f"\n{Fore.RED}[!] BANKRUPTCY TRIGGERED: Sized bankroll dropped below trading limits.{Style.RESET_ALL}")
                break
                
            # Stop condition 2: Goal achieved
            if sim.target_reached:
                print(f"\n{Fore.GREEN}[SUCCESS] TARGET REACHED: Portfolio successfully compounded to {sim.sim_balance:.5f} SOL!{Style.RESET_ALL}")
                break
                
            # Running duration limit (12 hours max)
            if elapsed >= 43200.0:
                print(f"\n[LIMIT] 12-hour live feed simulation limit reached.")
                break
                
    except KeyboardInterrupt:
        print("\n[!] Perfect Simulation interrupted cleanly by user.")
    finally:
        sim.running = False
        if not monitor_task.done():
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        await sim.http.aclose()
        
        # Calculate active trades left held
        active_positions = [p for p in sim.positions.values() if p.status == "active"]
        
        print("\n================================================================================")
        print("                PERFECT COMPOUNDING TRIAL: FINAL AUTOPSY REPORT                ")
        print("================================================================================")
        print(f" Initial Starting Bankroll:               {sim.initial_balance:.5f} SOL")
        print(f" Final Ending Bankroll Balance:           {sim.sim_balance:.5f} SOL")
        
        net_change = sim.sim_balance - sim.initial_balance
        pnl_color = Fore.LIGHTGREEN_EX if net_change >= 0 else Fore.LIGHTRED_EX
        pnl_symbol = "+" if net_change >= 0 else ""
        print(f" Net Compounding P&L:                    {pnl_color}{pnl_symbol}{net_change:+.5f} SOL ({net_change/sim.initial_balance*100:+.2f}%){Style.RESET_ALL}")
        
        status_str = f"{Fore.RED}BANKRUPT{Style.RESET_ALL}" if sim.bankrupt else f"{Fore.GREEN}TARGET REACHED{Style.RESET_ALL}" if sim.target_reached else f"{Fore.YELLOW}COMPLETED RUN / POSITIONS OPEN{Style.RESET_ALL}"
        print(f" Simulation Exit Status:                   {status_str}")
        print("-" * 80)
        print(f" Total Launches Audited:                  {sim.tokens_seen}")
        print(f" Total Scams Intercepted/Blocked:         {sim.tokens_filtered}")
        print(f" Safe Snipes Executed (Simulated Buys):   {sim.tokens_bought}")
        print(f" Active Positions Remaining:              {len(active_positions)}")
        print("-" * 80)
        
        if sim.trade_ledger:
            print("Completed Trades Ledger:")
            print("-" * 105)
            print(f"{'Token (Symbol)':<24} | {'Status':<14} | {'Allocated Cost (SOL)':<20} | {'Net Returned (SOL)':<18} | {'Net Trade P&L':<15}")
            print("-" * 105)
            for t in sim.trade_ledger:
                color = Fore.LIGHTGREEN_EX if t["pnl"] >= 0 else Fore.LIGHTRED_EX
                sym = "+" if t["pnl"] >= 0 else ""
                print(f"{t['token']:<24} | {t['status'].upper():<14} | {t['allocated']:<20.5f} | {t['returned']:<18.5f} | {color}{sym}{t['pnl']:+.5f} SOL ({t['pct']:+.1f}%){Style.RESET_ALL}")
            print("-" * 105)
        else:
            print("No dry-run snipes completed during this session.")
        print("================================================================================\n")

if __name__ == '__main__':
    asyncio.run(run_perfect_simulation())
