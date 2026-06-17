#!/usr/bin/env python3
"""
core/evolution_engine.py
Self-Evolution and Reinforcement Learning Engine for the Trading Bot.
Queries the SQLite trade journal, reconstructs round-trips via FIFO matching,
and dynamically adjusts strategy weights, consensus thresholds, ATR SL/TP, and position sizes.
"""

import os
import sys
import json
import sqlite3
import numpy as np
from datetime import datetime, timezone

# Dynamic path resolution to support restructured package layouts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) in ["core", "models", "execution", "discovery", "utils"] else current_dir
sys.path.append(project_root)

from config import JOURNAL_DB_PATH

EVOLVED_PARAMS_PATH = os.path.join(project_root, "evolved_parameters.json")

class SelfEvolutionEngine:
    def __init__(self, db_path: str = JOURNAL_DB_PATH):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_all_trades(self) -> list[dict]:
        """Fetch all trades from the database ordered by timestamp ascending."""
        if not os.path.exists(self.db_path):
            return []
        
        conn = None
        try:
            conn = self._connect()
            # Ensure the trades table exists
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL DEFAULT 0,
                    strategy TEXT,
                    timeframe TEXT,
                    notes TEXT
                )
                """
            )
            rows = conn.execute(
                """
                SELECT ts, symbol, side, qty, price, fee, strategy, timeframe, notes
                FROM trades
                ORDER BY ts ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[Evolution Engine] Failed to fetch trades: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def reconstruct_trade_rounds(self, trades: list[dict]) -> dict[str, list[dict]]:
        """
        Group trades by symbol and match entries/exits using FIFO logic.
        Returns a dict of {symbol: list of closed trade rounds}.
        """
        symbol_trades = {}
        for t in trades:
            sym = t["symbol"].strip().upper()
            symbol_trades.setdefault(sym, []).append(t)

        completed_rounds = {}

        for symbol, t_list in symbol_trades.items():
            open_positions = [] # queue of entries: {"qty", "price", "fee", "strategy", "notes", "ts"}
            rounds = []
            net_position = 0.0

            for t in t_list:
                side = t["side"].strip().upper()
                qty = float(t["qty"])
                price = float(t["price"])
                fee = float(t["fee"] or 0.0)
                strategy = t["strategy"] or ""
                notes = t["notes"] or ""
                ts = t["ts"]

                # Parse sub-strategy votes from notes if available
                # Expected format: [VOTES] EMA_RSI,BREAKOUT,...
                voting_strategies = []
                if "[VOTES]" in notes:
                    try:
                        votes_part = notes.split("[VOTES]")[-1].strip()
                        voting_strategies = [s.strip() for s in votes_part.split(",") if s.strip()]
                    except Exception:
                        pass
                
                # If no [VOTES] found, check if strategy column starts with CONSENSUS
                if not voting_strategies and strategy.startswith("CONSENSUS"):
                    # Fallback to general base indicators
                    voting_strategies = ["EMA_RSI", "BREAKOUT", "MEAN_REV"]

                is_long_action = (side == "BUY")

                if len(open_positions) == 0:
                    # Start a new position direction
                    open_positions.append({
                        "qty": qty, "price": price, "fee": fee,
                        "strategy": strategy, "notes": notes, "ts": ts,
                        "voting_strategies": voting_strategies, "side": side
                    })
                    net_position = qty if is_long_action else -qty
                else:
                    # Check if action is in the same direction
                    current_side = open_positions[0]["side"]
                    if current_side == side:
                        # Adding to position
                        open_positions.append({
                            "qty": qty, "price": price, "fee": fee,
                            "strategy": strategy, "notes": notes, "ts": ts,
                            "voting_strategies": voting_strategies, "side": side
                        })
                        net_position += qty if is_long_action else -qty
                    else:
                        # Closing or reducing position (opposite action)
                        while qty > 0 and len(open_positions) > 0:
                            entry = open_positions[0]
                            matched_qty = min(entry["qty"], qty)

                            # Calculate transaction fees proportional to matched qty
                            entry_fee_share = (matched_qty / entry["qty"]) * entry["fee"] if entry["qty"] > 0 else 0.0
                            exit_fee_share = (matched_qty / t["qty"]) * fee if t["qty"] > 0 else 0.0

                            # Reconstruct PnL
                            if entry["side"] == "BUY": # Long position closed by SELL
                                pnl = (price - entry["price"]) * matched_qty - (entry_fee_share + exit_fee_share)
                            else: # Short position closed by BUY
                                pnl = (entry["price"] - price) * matched_qty - (entry_fee_share + exit_fee_share)

                            rounds.append({
                                "qty": matched_qty,
                                "entry_price": entry["price"],
                                "exit_price": price,
                                "entry_ts": entry["ts"],
                                "exit_ts": ts,
                                "pnl": pnl,
                                "cost": entry["price"] * matched_qty,
                                "voting_strategies": entry["voting_strategies"],
                                "entry_strategy": entry["strategy"]
                            })

                            # Update remaining quantities
                            entry["qty"] -= matched_qty
                            qty -= matched_qty

                            if entry["qty"] <= 0:
                                open_positions.pop(0)

                        if qty > 0:
                            # Opposing action fully closed existing position and started reversed position
                            open_positions.append({
                                "qty": qty, "price": price, "fee": fee,
                                "strategy": strategy, "notes": notes, "ts": ts,
                                "voting_strategies": voting_strategies, "side": side
                            })
                            net_position = qty if is_long_action else -qty
                        else:
                            net_position = sum(p["qty"] for p in open_positions)
                            if current_side == "SELL":
                                net_position = -net_position

            if rounds:
                completed_rounds[symbol] = rounds

        return completed_rounds

    def evolve(self) -> dict:
        """Run the self-evolution engine feedback loop over all historical trades."""
        raw_trades = self.fetch_all_trades()
        if not raw_trades:
            print("[Self-Evolution] No trade journal records found in database. Skipping evolution.")
            return {}

        # Filter out invalid, empty, or failed executions with zero or negative quantity
        trades = [t for t in raw_trades if float(t.get("qty", 0.0) or 0.0) > 0.0]
        if not trades:
            print("[Self-Evolution] No valid trade executions with non-zero quantity found. Skipping evolution.")
            return {}

        rounds_dict = self.reconstruct_trade_rounds(trades)
        if not rounds_dict:
            print("[Self-Evolution] No completed trade round-trips reconstructed. Skipping evolution.")
            return {}

        # Load existing parameter DNA
        evolved_params = load_all_evolved_parameters()

        print(f"[Self-Evolution] Reconstructed trade rounds for {len(rounds_dict)} assets.")

        for symbol, rounds in rounds_dict.items():
            total_rounds = len(rounds)
            wins = [r for r in rounds if r["pnl"] > 0]
            losses = [r for r in rounds if r["pnl"] <= 0]
            win_rate = (len(wins) / total_rounds * 100) if total_rounds > 0 else 0.0

            gross_wins = sum(w["pnl"] for w in wins)
            gross_losses = abs(sum(l["pnl"] for l in losses))
            profit_factor = gross_wins / gross_losses if gross_losses > 0 else (gross_wins * 5.0 if wins else 1.0)

            avg_win = np.mean([w["pnl"] for w in wins]) if wins else 0.0
            avg_loss = abs(np.mean([l["pnl"] for l in losses])) if losses else 0.0

            print(f"\n[Evolving {symbol}] Analyzing {total_rounds} closed rounds:")
            print(f"  * Win Rate: {win_rate:.2f}% | Profit Factor: {profit_factor:.2f}")
            print(f"  * Average Win: ${avg_win:.2f} | Average Loss: ${avg_loss:.2f}")

            # Retrieve baseline/current parameter state
            current = evolved_params.get(symbol, {
                "symbol": symbol,
                "strategy_weights": {
                    "EMA_RSI": 1.0,
                    "BREAKOUT": 1.0,
                    "MEAN_REV": 1.0,
                    "SUPERTREND": 1.0,
                    "ICHIMOKU": 1.0,
                    "SQUEEZE": 1.0,
                    "ML_SIGNAL": 1.0,
                    "TV_RATING": 1.0
                },
                "consensus_threshold": 4.0,
                "atr_multiplier_sl": 2.0,
                "atr_multiplier_tp": 3.0,
                "position_size_multiplier": 1.0
            })

            # 1. Update Strategy Weights using Reinforcement Learning
            # Reward winning votes, penalize losing votes
            weights = current.setdefault("strategy_weights", {
                "EMA_RSI": 1.0, "BREAKOUT": 1.0, "MEAN_REV": 1.0,
                "SUPERTREND": 1.0, "ICHIMOKU": 1.0, "SQUEEZE": 1.0,
                "ML_SIGNAL": 1.0, "TV_RATING": 1.0
            })

            for r in rounds:
                voting_strats = r["voting_strategies"]
                if not voting_strats:
                    continue

                pnl = r["pnl"]
                # Learning step size proportional to trade return magnitude
                cost = r["cost"] if r["cost"] > 0 else 1.0
                return_pct = abs(pnl) / cost
                step = float(np.clip(return_pct * 0.5, 0.02, 0.10))

                if pnl > 0:
                    for s in voting_strats:
                        if s in weights:
                            weights[s] = round(float(np.clip(weights[s] + step, 0.2, 2.0)), 3)
                else:
                    for s in voting_strats:
                        if s in weights:
                            weights[s] = round(float(np.clip(weights[s] - step, 0.2, 2.0)), 3)

            # 2. Adjust Consensus Threshold based on win rate
            # Higher threshold makes entries harder, lower lets more through
            threshold = current.get("consensus_threshold", 4.0)
            if total_rounds >= 3:
                if win_rate < 45.0:
                    threshold = round(float(np.clip(threshold + 0.25, 4.0, 5.0)), 2)
                elif win_rate > 60.0:
                    threshold = round(float(np.clip(threshold - 0.25, 3.0, 4.5)), 2)
            current["consensus_threshold"] = threshold

            # 3. Dynamic Stop Loss and Take Profit adjustment
            sl_mult = current.get("atr_multiplier_sl", 2.0)
            tp_mult = current.get("atr_multiplier_tp", 3.0)
            
            if total_rounds >= 3:
                # If average loss is substantially bigger than average win
                loss_ratio = avg_loss / avg_win if avg_win > 0 else 2.5
                if loss_ratio > 1.5:
                    # Tighten stop loss to safeguard capital, widen take profit
                    sl_mult = round(float(np.clip(sl_mult - 0.15, 1.5, 3.0)), 2)
                    tp_mult = round(float(np.clip(tp_mult + 0.25, 2.5, 4.5)), 2)
                elif loss_ratio < 0.8:
                    # High profit factor, can expand SL slightly to avoid noise hits, and secure wins faster
                    sl_mult = round(float(np.clip(sl_mult + 0.15, 1.5, 3.5)), 2)
                    tp_mult = round(float(np.clip(tp_mult - 0.15, 2.0, 4.0)), 2)
            
            current["atr_multiplier_sl"] = sl_mult
            current["atr_multiplier_tp"] = tp_mult

            # 4. Position Sizing Multiplier (Dynamic Leverage adjustment)
            pos_size_mult = current.get("position_size_multiplier", 1.0)
            if total_rounds >= 3:
                if win_rate > 55.0 and profit_factor > 1.2:
                    pos_size_mult = round(float(np.clip(pos_size_mult + 0.10, 0.2, 2.0)), 2)
                elif win_rate < 45.0 or profit_factor < 0.9:
                    pos_size_mult = round(float(np.clip(pos_size_mult - 0.10, 0.2, 2.0)), 2)
            current["position_size_multiplier"] = pos_size_mult

            # Metadata updates
            current["win_rate"] = round(win_rate, 2)
            current["profit_factor"] = round(profit_factor, 2)
            current["total_trades_analyzed"] = total_rounds
            current["evolved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            evolved_params[symbol] = current

            # Print formatted report card in monochrome console format
            print(f"  --> Evolved Parameter DNA for {symbol}:")
            print(f"      - Consensus Threshold: {threshold}")
            print(f"      - ATR Multipliers: SL={sl_mult} | TP={tp_mult}")
            print(f"      - Position Size Multiplier: {pos_size_mult}x")
            print(f"      - Sub-Strategy Weights: " + ", ".join(f"{k}:{v}" for k, v in weights.items()))

        save_all_evolved_parameters(evolved_params)
        return evolved_params


def load_all_evolved_parameters() -> dict:
    """Load all evolved parameters from the dynamic JSON file."""
    if not os.path.exists(EVOLVED_PARAMS_PATH):
        return {}
    try:
        with open(EVOLVED_PARAMS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Evolution Engine] Failed to load evolved parameters: {e}")
        return {}

def load_evolved_parameters(symbol: str) -> dict | None:
    """Retrieve evolved parameter override block for a specific asset symbol."""
    all_params = load_all_evolved_parameters()
    return all_params.get(symbol.strip().upper())

def save_all_evolved_parameters(params: dict):
    """Write all evolved parameters to disk."""
    try:
        with open(EVOLVED_PARAMS_PATH, "w") as f:
            json.dump(params, f, indent=2)
        print(f"[Self-Evolution] Updated parameters successfully saved to {EVOLVED_PARAMS_PATH}")
    except Exception as e:
        print(f"[Evolution Engine] Failed to save evolved parameters: {e}")

if __name__ == "__main__":
    print("[Evolution Engine] Initiating standalone evolution sweep...")
    engine = SelfEvolutionEngine()
    engine.evolve()
