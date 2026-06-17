#!/usr/bin/env python3
"""
Profit Tracker — SQLite-backed Trade Logger & Statistics Engine
cook45 & clack // Systems & MEV

Logs every trade attempt (success/fail), tracks cumulative P&L, win rate,
and prints periodic summaries. Integrates as a singleton into the main bot loop.
"""

import os
import sqlite3
import time
import logging
from typing import Optional, Dict, Any, List
from colorama import Fore, Style

logger = logging.getLogger("SolanaArbBot")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.db")


class ProfitTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.last_summary_time = time.time()
        self.summary_interval = 3600  # Print summary every hour

    def _init_db(self):
        """Creates the trades table if it doesn't exist"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                direction TEXT NOT NULL,
                input_amount_usdc REAL NOT NULL,
                output_amount_usdc REAL NOT NULL,
                net_profit_usdc REAL NOT NULL,
                profit_pct REAL NOT NULL,
                spread_pct REAL NOT NULL DEFAULT 0.0,
                tx_sig_1 TEXT,
                tx_sig_2 TEXT,
                status TEXT NOT NULL DEFAULT 'executed',
                balance_before REAL DEFAULT 0.0,
                balance_after REAL DEFAULT 0.0,
                notes TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                sol_balance REAL NOT NULL,
                usdc_balance REAL NOT NULL,
                total_usd REAL NOT NULL
            )
        """)
        self.conn.commit()
        logger.info(f"Profit Tracker initialized. DB: {Fore.CYAN}{self.db_path}{Style.RESET_ALL}")

    def log_trade(
        self,
        direction: str,
        input_amount: float,
        output_amount: float,
        net_profit: float,
        profit_pct: float,
        spread_pct: float = 0.0,
        tx_sig_1: Optional[str] = None,
        tx_sig_2: Optional[str] = None,
        status: str = "executed",
        balance_before: float = 0.0,
        balance_after: float = 0.0,
        notes: Optional[str] = None
    ):
        """Records a single trade execution"""
        self.conn.execute("""
            INSERT INTO trades (
                timestamp, direction, input_amount_usdc, output_amount_usdc,
                net_profit_usdc, profit_pct, spread_pct, tx_sig_1, tx_sig_2,
                status, balance_before, balance_after, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.time(), direction, input_amount, output_amount,
            net_profit, profit_pct, spread_pct, tx_sig_1, tx_sig_2,
            status, balance_before, balance_after, notes
        ))
        self.conn.commit()

        status_color = Fore.GREEN if status == "executed" else Fore.RED
        profit_color = Fore.GREEN if net_profit >= 0 else Fore.RED
        logger.info(
            f"{Fore.LIGHTMAGENTA_EX}[TRADE-LOG]{Style.RESET_ALL} "
            f"Status: {status_color}{status}{Style.RESET_ALL} | "
            f"Dir: {Fore.YELLOW}{direction}{Style.RESET_ALL} | "
            f"In: ${input_amount:.4f} → Out: ${output_amount:.4f} | "
            f"P&L: {profit_color}{'+' if net_profit >= 0 else ''}${net_profit:.4f} ({profit_pct:.3f}%){Style.RESET_ALL}"
        )

    def log_skipped_opportunity(
        self,
        direction: str,
        input_amount: float,
        expected_profit: float,
        profit_pct: float,
        spread_pct: float,
        reason: str
    ):
        """Records an opportunity that was detected but skipped (e.g., below threshold)"""
        self.log_trade(
            direction=direction,
            input_amount=input_amount,
            output_amount=input_amount + expected_profit,
            net_profit=expected_profit,
            profit_pct=profit_pct,
            spread_pct=spread_pct,
            status="skipped",
            notes=reason
        )

    def log_balance_snapshot(self, sol_balance: float, usdc_balance: float, sol_price_usd: float):
        """Records a periodic balance snapshot for portfolio tracking"""
        total_usd = usdc_balance + (sol_balance * sol_price_usd)
        self.conn.execute("""
            INSERT INTO snapshots (timestamp, sol_balance, usdc_balance, total_usd)
            VALUES (?, ?, ?, ?)
        """, (time.time(), sol_balance, usdc_balance, total_usd))
        self.conn.commit()

    def get_stats(self, hours: Optional[float] = None) -> Dict[str, Any]:
        """Calculates aggregate statistics, optionally filtered to last N hours"""
        where_clause = ""
        params = []
        if hours is not None:
            cutoff = time.time() - (hours * 3600)
            where_clause = "WHERE timestamp >= ? AND status = 'executed'"
            params = [cutoff]
        else:
            where_clause = "WHERE status = 'executed'"

        row = self.conn.execute(f"""
            SELECT
                COUNT(*) as total_trades,
                COALESCE(SUM(net_profit_usdc), 0) as total_profit,
                COALESCE(AVG(net_profit_usdc), 0) as avg_profit,
                COALESCE(MAX(net_profit_usdc), 0) as best_trade,
                COALESCE(MIN(net_profit_usdc), 0) as worst_trade,
                COALESCE(SUM(CASE WHEN net_profit_usdc > 0 THEN 1 ELSE 0 END), 0) as wins,
                COALESCE(SUM(CASE WHEN net_profit_usdc <= 0 THEN 1 ELSE 0 END), 0) as losses,
                COALESCE(AVG(profit_pct), 0) as avg_profit_pct,
                COALESCE(AVG(spread_pct), 0) as avg_spread_pct
            FROM trades {where_clause}
        """, params).fetchone()

        skipped = self.conn.execute(f"""
            SELECT COUNT(*) as cnt FROM trades
            WHERE status = 'skipped' {'AND timestamp >= ?' if hours else ''}
        """, params if hours else []).fetchone()

        total = row["total_trades"]
        win_rate = (row["wins"] / total * 100) if total > 0 else 0.0

        return {
            "total_trades": total,
            "total_profit": row["total_profit"],
            "avg_profit": row["avg_profit"],
            "best_trade": row["best_trade"],
            "worst_trade": row["worst_trade"],
            "wins": row["wins"],
            "losses": row["losses"],
            "win_rate": win_rate,
            "avg_profit_pct": row["avg_profit_pct"],
            "avg_spread_pct": row["avg_spread_pct"],
            "skipped_opportunities": skipped["cnt"]
        }

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent N trades"""
        rows = self.conn.execute("""
            SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_daily_pnl(self) -> Dict[str, Any]:
        """Returns P&L statistics for the current calendar day (UTC)"""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = day_start.timestamp()
        row = self.conn.execute("""
            SELECT
                COUNT(*) as total_trades,
                COALESCE(SUM(net_profit_usdc), 0) as total_profit,
                COALESCE(AVG(net_profit_usdc), 0) as avg_profit,
                COALESCE(SUM(CASE WHEN net_profit_usdc > 0 THEN 1 ELSE 0 END), 0) as wins,
                COALESCE(SUM(CASE WHEN net_profit_usdc <= 0 THEN 1 ELSE 0 END), 0) as losses
            FROM trades
            WHERE timestamp >= ? AND status = 'executed'
        """, (cutoff,)).fetchone()
        total = row["total_trades"]
        win_rate = (row["wins"] / total * 100) if total > 0 else 0.0
        return {
            "date": day_start.strftime("%Y-%m-%d"),
            "total_trades": total,
            "total_profit": row["total_profit"],
            "avg_profit": row["avg_profit"],
            "wins": row["wins"],
            "losses": row["losses"],
            "win_rate": win_rate,
        }

    def should_halt_trading(self, daily_loss_limit_usd: float = 50.0) -> bool:
        """Circuit breaker: returns True if daily losses exceed the limit"""
        daily = self.get_daily_pnl()
        if daily["total_profit"] < -abs(daily_loss_limit_usd):
            logger.warning(
                f"{Fore.RED}[CIRCUIT-BREAKER]{Style.RESET_ALL} "
                f"Daily loss limit hit: ${daily['total_profit']:.4f} < -${daily_loss_limit_usd:.2f}"
            )
            return True
        return False

    def print_summary(self, force: bool = False):
        """Prints a formatted statistics summary if the interval has elapsed"""
        now = time.time()
        if not force and (now - self.last_summary_time) < self.summary_interval:
            return

        self.last_summary_time = now

        all_time = self.get_stats()
        last_24h = self.get_stats(hours=24)
        last_1h = self.get_stats(hours=1)

        profit_color = Fore.GREEN if all_time["total_profit"] >= 0 else Fore.RED

        print(f"""
{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}╔══════════════════════════════════════════════════════════╗
║              📊 PROFIT TRACKER SUMMARY                   ║
╠══════════════════════════════════════════════════════════╣{Style.RESET_ALL}
{Fore.CYAN}  ALL-TIME:{Style.RESET_ALL}
    Trades: {Fore.WHITE}{all_time['total_trades']}{Style.RESET_ALL} | Win Rate: {Fore.GREEN}{all_time['win_rate']:.1f}%{Style.RESET_ALL}
    Total P&L: {profit_color}${all_time['total_profit']:.4f}{Style.RESET_ALL} | Avg: ${all_time['avg_profit']:.4f}
    Best: {Fore.GREEN}+${all_time['best_trade']:.4f}{Style.RESET_ALL} | Worst: {Fore.RED}${all_time['worst_trade']:.4f}{Style.RESET_ALL}
    Skipped Opportunities: {Fore.YELLOW}{all_time['skipped_opportunities']}{Style.RESET_ALL}

{Fore.CYAN}  LAST 24H:{Style.RESET_ALL}
    Trades: {last_24h['total_trades']} | P&L: ${last_24h['total_profit']:.4f}

{Fore.CYAN}  LAST 1H:{Style.RESET_ALL}
    Trades: {last_1h['total_trades']} | P&L: ${last_1h['total_profit']:.4f}
{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")

    def close(self):
        self.conn.close()
