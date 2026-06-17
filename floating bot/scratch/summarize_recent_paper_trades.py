#!/usr/bin/env python3
"""
Recent Paper Trades Quantitative Auditor
cook45 & clack // Systems & MEV

Audits and summarizes all simulated paper trades executed by the bot
in trades.db, calculating win rates, net P&L, and token-by-token performance.
"""

import sqlite3
import os
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

def main():
    db_path = "trades.db"
    if not os.path.exists(db_path):
        print(f"{Fore.RED}[X] Database {db_path} not found! Run the bot first to populate trades.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}       QUANTITATIVE PAPER TRADES PERFORMANCE AUDIT ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")

    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paper_trades';")
        if not cursor.fetchone():
            print(f"{Fore.YELLOW}[!] Table 'paper_trades' does not exist yet. No paper trades have been simulated.")
            conn.close()
            return

        # Query all paper trades
        cursor.execute("SELECT id, timestamp, direction, mint_address, amount_sol, amount_token, price_sol, status, net_pnl_sol FROM paper_trades ORDER BY timestamp DESC;")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"{Fore.YELLOW}[!] No paper trades found in the database. The ML model is scanning, but no trades have triggered yet.")
            conn.close()
            return

        total_trades = len(rows)
        # Unique tokens traded
        mints = set(row[3] for row in rows)
        
        # Calculate P&L and Win Rate
        # For win rate, we look at closed positions with net_pnl_sol > 0
        closed_trades = [row for row in rows if row[7] == 'CLOSED']
        wins = [row for row in closed_trades if row[8] > 0]
        losses = [row for row in closed_trades if row[8] <= 0]
        
        total_pnl = sum(row[8] for row in closed_trades if row[8] is not None)
        
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0

        print(f"[+] Total Simulated Trades: {Fore.CYAN}{total_trades}{Style.RESET_ALL}")
        print(f"[+] Unique Mints Scanned:   {Fore.CYAN}{len(mints)}{Style.RESET_ALL}")
        print(f"[+] Closed Positions:       {Fore.CYAN}{len(closed_trades)}{Style.RESET_ALL}")
        print(f"[+] Wins:                   {Fore.GREEN}{len(wins)}{Style.RESET_ALL} | Losses: {Fore.RED}{len(losses)}{Style.RESET_ALL}")
        print(f"[+] Heuristic Win Rate:     {Fore.LIGHTGREEN_EX}{win_rate:.2f}%{Style.RESET_ALL}")
        print(f"[+] Cumulative Net P&L:     {Fore.GREEN if total_pnl >= 0 else Fore.RED}{total_pnl:+.6f} SOL{Style.RESET_ALL}\n")

        print("--- Transaction History (Newest to Oldest) ---")
        print(f"{'ID':<4} | {'Time':<8} | {'Type':<4} | {'Mint Address':<20} | {'SOL':<8} | {'Status':<8} | {'Net P&L (SOL)':<14}")
        print("-" * 85)

        for row in rows[:15]:  # Show last 15 for brevity
            tid, ts, direction, mint, sol, token, price, status, pnl = row
            time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            mint_short = f"{mint[:10]}...{mint[-8:]}" if len(mint) > 20 else mint
            
            pnl_str = f"{pnl:+.6f}" if pnl is not None and status == 'CLOSED' else "N/A"
            pnl_color = Fore.GREEN if pnl is not None and pnl > 0 else Fore.RED if pnl is not None and pnl < 0 else Style.RESET_ALL
            
            type_color = Fore.LIGHTBLUE_EX if direction == 'BUY' else Fore.LIGHTMAGENTA_EX
            status_color = Fore.GREEN if status == 'CLOSED' else Fore.YELLOW
            
            print(f"{tid:<4} | {time_str:<8} | {type_color}{direction:<4}{Style.RESET_ALL} | {mint_short:<20} | {sol:<8.4f} | {status_color}{status:<8}{Style.RESET_ALL} | {pnl_color}{pnl_str:<14}")

        if len(rows) > 15:
            print(f"\n... and {len(rows) - 15} more historical transactions in database.")

    except Exception as e:
        print(f"{Fore.RED}[X] Error executing performance audit: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
