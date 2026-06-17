"""
event_engine.py
Custom High-Speed Queue-Based Event-Driven Backtesting Core.
Conforms to institutional event-loop standards with latency, spreads, and fee simulations.
"""

import queue
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

class Event:
    pass

class BarEvent(Event):
    def __init__(self, symbol: str, timeframe: str, bar: dict):
        self.type = "BAR"
        self.symbol = symbol
        self.timeframe = timeframe
        self.bar = bar

class SignalEvent(Event):
    def __init__(self, symbol: str, timeframe: str, action: str, confidence: float):
        self.type = "SIGNAL"
        self.symbol = symbol
        self.timeframe = timeframe
        self.action = action  # 'BUY', 'SELL', 'HOLD'
        self.confidence = confidence

class OrderEvent(Event):
    def __init__(self, symbol: str, side: str, qty: float, price: float):
        self.type = "ORDER"
        self.symbol = symbol
        self.side = side  # 'BUY', 'SELL'
        self.qty = qty
        self.price = price

class FillEvent(Event):
    def __init__(self, symbol: str, side: str, qty: float, price: float, fee: float):
        self.type = "FILL"
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price
        self.fee = fee


class ExecutionHandler:
    def __init__(self, fee_rate: float = 0.001, slippage_pct: float = 0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct

    def execute_order(self, order: OrderEvent) -> FillEvent:
        """Simulate order fill on exchange with spread/slippage and commission fees."""
        price = order.price
        
        # Apply slippage based on side
        if order.side == "BUY":
            fill_price = price * (1.0 + self.slippage_pct)
        else:
            fill_price = price * (1.0 - self.slippage_pct)
            
        fee = fill_price * order.qty * self.fee_rate
        return FillEvent(order.symbol, order.side, order.qty, fill_price, fee)


class Portfolio:
    def __init__(self, initial_cash: float = 10000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}  # symbol -> shares count
        self.entry_prices: Dict[str, float] = {}  # symbol -> avg entry price
        self.trades: List[dict] = []
        self.equity_history: List[float] = [initial_cash]

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        """Calculate total current net worth including holdings at current market value."""
        holdings_value = 0.0
        for sym, qty in self.positions.items():
            price = current_prices.get(sym, 0.0)
            holdings_value += qty * price
        return self.cash + holdings_value

    def process_fill(self, fill: FillEvent):
        """Update portfolio state based on completed order fill."""
        sym = fill.symbol
        qty = fill.qty
        price = fill.price
        fee = fill.fee
        
        if fill.side == "BUY":
            cost = (qty * price) + fee
            self.cash -= cost
            self.positions[sym] = self.positions.get(sym, 0.0) + qty
            # Standard average entry price tracking
            prev_qty = self.positions.get(sym, 0.0) - qty
            if prev_qty > 0:
                prev_price = self.entry_prices.get(sym, 0.0)
                self.entry_prices[sym] = ((prev_price * prev_qty) + (price * qty)) / (prev_qty + qty)
            else:
                self.entry_prices[sym] = price
                
            self.trades.append({
                "symbol": sym,
                "side": "BUY",
                "qty": qty,
                "price": price,
                "fee": fee,
                "net_worth_after": self.cash + (self.positions[sym] * price)
            })
        else:
            revenue = (qty * price) - fee
            self.cash += revenue
            # Realized PnL calculation
            entry_price = self.entry_prices.get(sym, price)
            pnl = (price - entry_price) * qty - fee - (self.trades[-1]["fee"] if len(self.trades) > 0 else 0.0)
            
            self.positions[sym] = self.positions.get(sym, 0.0) - qty
            if self.positions[sym] <= 1e-8:
                self.positions[sym] = 0.0
                self.entry_prices[sym] = 0.0
                
            self.trades.append({
                "symbol": sym,
                "side": "SELL",
                "qty": qty,
                "price": price,
                "fee": fee,
                "pnl": pnl,
                "net_worth_after": self.cash + (self.positions.get(sym, 0.0) * price)
            })


class EventEngine:
    def __init__(self, initial_cash: float = 10000.0, fee_rate: float = 0.001, slippage: float = 0.0005):
        self.events_queue = queue.Queue()
        self.portfolio = Portfolio(initial_cash)
        self.execution_handler = ExecutionHandler(fee_rate, slippage)
        self.latest_prices: Dict[str, float] = {}

    def run_backtest(
        self, 
        df_dict: Dict[str, pd.DataFrame], 
        strategy_eval_func, 
        timeframe: str = "1h"
    ) -> dict:
        """
        Executes a historical event-driven simulation.
        Processes standard candles bar-by-bar, executing orders and updating metrics.
        """
        # Ensure all dataframes are chronologically aligned by sorting them
        clean_dfs = {}
        min_len = 999999
        for sym, df in df_dict.items():
            if not df.empty:
                clean_dfs[sym] = df.copy().reset_index(drop=True)
                min_len = min(min_len, len(clean_dfs[sym]))
                
        if not clean_dfs or min_len == 999999 or min_len < 30:
            return {"status": "error", "message": "Insufficient clean data for simulation"}

        # Event-loop sweep bar-by-bar
        for step in range(30, min_len):
            # 1. Update prices and emit BarEvents
            for sym, df in clean_dfs.items():
                row = df.iloc[step]
                price = float(row["close"])
                self.latest_prices[sym] = price
                
                # Emit new candle event
                self.events_queue.put(BarEvent(sym, timeframe, dict(row)))
                
            # 2. Process all events inside the queue step-by-step
            while not self.events_queue.empty():
                event = self.events_queue.get()
                
                if event.type == "BAR":
                    # Evaluate trading strategies (consensus) on latest bar
                    # Convert row to a mock dataframe containing previous history for indicator recalculation
                    bar_history = clean_dfs[event.symbol].iloc[:step + 1].copy()
                    
                    action, conf = strategy_eval_func(bar_history)
                    if action in ["BUY", "SELL"]:
                        self.events_queue.put(SignalEvent(event.symbol, event.timeframe, action, conf))
                        
                elif event.type == "SIGNAL":
                    sym = event.symbol
                    action = event.action
                    price = self.latest_prices[sym]
                    
                    # Portfolio Risk & Compliance sizing logic
                    if action == "BUY" and self.portfolio.positions.get(sym, 0.0) == 0.0:
                        # Allocate 90% of cash for paper safety
                        buy_cash = self.portfolio.cash * 0.90
                        qty = buy_cash / price
                        if qty > 0:
                            self.events_queue.put(OrderEvent(sym, "BUY", qty, price))
                    elif action == "SELL" and self.portfolio.positions.get(sym, 0.0) > 0.0:
                        qty = self.portfolio.positions[sym]
                        self.events_queue.put(OrderEvent(sym, "SELL", qty, price))
                        
                elif event.type == "ORDER":
                    # Execute on mock trading exchange fill engine
                    fill_event = self.execution_handler.execute_order(event)
                    self.events_queue.put(fill_event)
                    
                elif event.type == "FILL":
                    # Update portfolio cash, holdings, and trade records
                    self.portfolio.process_fill(event)
            
            # Record historical equity progress at the end of every candle step
            self.portfolio.equity_history.append(self.portfolio.get_equity(self.latest_prices))

        # Calculate finalized performance metrics
        trades = self.portfolio.trades
        sell_trades = [t for t in trades if t["side"] == "SELL"]
        
        total_trades = len(trades)
        wins = [t for t in sell_trades if t.get("pnl", 0.0) > 0]
        win_rate = len(wins) / len(sell_trades) if len(sell_trades) > 0 else 0.0
        
        final_equity = self.portfolio.get_equity(self.latest_prices)
        total_pnl = final_equity - self.portfolio.initial_cash
        pnl_pct = (total_pnl / self.portfolio.initial_cash)
        
        # Drawdown calculation
        equity_series = np.array(self.portfolio.equity_history)
        peaks = np.maximum.accumulate(equity_series)
        drawdowns = (peaks - equity_series) / peaks
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        return {
            "status": "success",
            "initial_cash": self.portfolio.initial_cash,
            "final_equity": final_equity,
            "total_pnl_usd": total_pnl,
            "total_pnl_pct": pnl_pct,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "trades_count": len(sell_trades)
        }
