# Unified Trading Bot - Single Command Guide

**Master Command for Complete Trading Analysis**

All trading bot analysis (market data, backtesting, portfolio tracking, and framework status) is now accessible via a single command.

## Quick Start

### Run Complete Analysis (Recommended for Beginners)
```bash
python unified_analyzer.py
```

This executes:
- Real-time market analysis with multi-timeframe signals
- Historical performance backtesting on all symbols
- Portfolio summary and recent trade review
- External framework status check

### Run with Custom Assets
```bash
python unified_analyzer.py --crypto BTCUSDT,ETHUSDT --stocks AAPL,TSLA
```

### Skip Time-Consuming Components
```bash
# Skip backtest (faster execution)
python unified_analyzer.py --skip-backtest

# Skip portfolio analysis
python unified_analyzer.py --skip-portfolio

# Skip external frameworks check
python unified_analyzer.py --skip-frameworks

# Skip all optional components
python unified_analyzer.py --skip-backtest --skip-portfolio --skip-frameworks
```

## Available Commands

### Unified Analyzer (All-in-One)
```bash
python unified_analyzer.py [OPTIONS]
```

**Options:**
- `--crypto CRYPTO` - Comma-separated cryptocurrency symbols (e.g. BTCUSDT,ETHUSDT)
- `--stocks STOCKS` - Comma-separated traditional stock tickers (e.g. AAPL,TSLA)
- `--forex FOREX` - Comma-separated global Forex pairs (e.g. GBPUSD,EURUSD)
- `--deep-dive SYMBOL` - Investigative quantitative deep-dive on a single symbol
- `--skip-backtest` - Skip historical backtesting
- `--skip-portfolio` - Skip portfolio analysis
- `--skip-frameworks` - Skip external framework status
- `--loop` - Run continuously until stopped
- `--interval SECONDS` - Time between runs when using `--loop` (default: 900)

**Output Sections:**
1. **Real-Time Market Analysis** - Current price, signals, and consensus votes
2. **Backtest Analysis** - Historical performance metrics per strategy
3. **Portfolio Analysis** - Win rate, profit factor, recent trades
4. **External Frameworks** - Integration status with 8 external frameworks
5. **Execution Summary** - Ready-to-trade signals and risk guidelines
6. **Next Steps** - Action recommendations

### Traditional Tracker (Real-Time Only)
```bash
python tracker.py [OPTIONS]
```

**Options:**
- `--top N` - Show top N movers
- `--watchlist SYMBOLS` - Comma-separated symbols
- `--timeframes TIMEFRAMES` - Comma-separated timeframes (15m,1h,4h,1d)
- `--bars N` - Bars per timeframe
- `--detailed` - Show strategy-by-strategy breakdown
- `--full` - Run unified analyzer (same as `python unified_analyzer.py`)

### Backtesting (Detailed Historical Analysis)
```bash
python backtest.py --symbol BTCUSDT [--timeframe 1d] [--strategy all]
```

**Strategies:**
- `ema_rsi` - EMA crossover + RSI confirmation
- `breakout` - Donchian channel breakout
- `mean_reversion` - Bollinger Band mean reversion
- `all` - Test all strategies

### Portfolio Journal (Track Trades)
```bash
python -c "from journal import get_portfolio_summary; print(get_portfolio_summary())"
```

### Telegram Bot (Real-Time Alerts)
```bash
python telegram_bot.py
```

**Commands:**
- `/signals` - Current market signals
- `/portfolio` - Portfolio summary
- `/trades` - Recent trade history
- `/frameworks` - Framework status
- `/help` - Command help

## Typical Workflow

### Morning Market Review
```bash
# Full analysis to understand market conditions
python unified_analyzer.py
```

### Quick Signal Check
```bash
# Real-time signals only (fastest)
python tracker.py --skip-backtest --skip-frameworks
```

### Backtest New Strategy
```bash
# Test a single symbol with detailed backtest
python backtest.py --symbol BTCUSDT --strategy all
```

### Monitor Portfolio
```bash
# Check recent trades and win rate
python -c "from journal import list_recent_trades, get_portfolio_summary; print(get_portfolio_summary())"
```

### Real-Time Telegram Alerts
```bash
# Start bot in background/new terminal
python telegram_bot.py
```

## Output Explanation

### Market Analysis Table
| Column | Meaning |
|--------|---------|
| Symbol | Trading pair |
| Signal | [BUY]/[SELL]/[HOLD] based on 2/3 consensus |
| Buy Votes | Number of strategies voting BUY (0-3) |
| Sell Votes | Number of strategies voting SELL (0-3) |
| Strength | Signal confidence (-1.0 to 1.0) |

### Backtest Results Table
| Metric | Meaning |
|--------|---------|
| Trades | Total closed positions |
| PnL | Total profit/loss in USD |
| Win Rate | % of profitable trades |
| Profit Factor | Gross wins / Gross losses (>1.0 is profitable) |
| Max DD | Maximum peak-to-trough drawdown |

### Portfolio Summary Table
| Metric | Meaning |
|--------|---------|
| Total Trades | All trades closed |
| Win Rate | % of winning trades |
| Avg Win/Loss | Average profit per winning/losing trade |
| Profit Factor | Risk/reward ratio |

## Signal Interpretation

### Consensus Voting (2/3 Required for Signal)
- **3 Strategies Available:**
  - EMA+RSI: Price trend + momentum oscillator
  - Breakout: Support/resistance level penetration
  - Mean Reversion: Volatility band mean reversion

- **Signal Logic:**
  - **[BUY]** = 2+ strategies vote BUY (consensus)
  - **[SELL]** = 2+ strategies vote SELL (consensus)
  - **[HOLD]** = Mixed votes or no consensus

### Example Signals
```
BTCUSDT [BUY] 2/3 - 2 strategies agree to buy
ETHUSDT [SELL] 3/3 - All strategies agree to sell (strongest signal)
BNBUSDT [HOLD] - No consensus, wait for clarity
```

## Risk Management Rules

**Always follow these before trading:**

1. **Stop Loss** = Entry Price ± (ATR × 2)
   - Automatically calculated and shown for each signal

2. **Take Profit** = Entry Price ± (ATR × 3)
   - Provides better risk/reward ratio than stop loss

3. **Position Sizing** = Risk only 1-2% of portfolio per trade
   - Example: $10,000 portfolio → max $100-200 risk per trade

4. **Consensus Requirement** = Wait for 2/3 strategy agreement
   - Reduces false signals and improves win rate

## Command Reference

| Task | Command |
|------|---------|
| Complete analysis (all tools) | `python unified_analyzer.py` |
| Fast real-time signals | `python tracker.py` |
| Detailed backtest | `python backtest.py --symbol BTCUSDT --strategy all` |
| Portfolio stats | `python telegram_bot.py /portfolio` |
| Enable telegram alerts | `python telegram_bot.py` (in separate terminal) |
| Check framework status | `python unified_analyzer.py --skip-backtest` |

## Performance Expectations

### Execution Time
- **Real-time signals only**: ~15-30 seconds (depends on network)
- **With backtest**: ~2-5 minutes (depends on symbol count and history)
- **Full analysis**: ~5-10 minutes (includes all components)

### Data Sources
- **Price data**: Binance REST API (spot trading)
- **Exchange adapters**: ccxt, python-binance (fallback)
- **Storage**: Local SQLite database (trade journal)

## Customization

### Change Default Watchlist
Edit `.env`:
```
WATCHLIST=BTCUSDT,ETHUSDT,BNBUSDT
```

### Adjust Backtest Parameters
Edit `config.py`:
```python
BACKTEST_BARS = 252  # Days to backtest
BACKTEST_FEE_RATE = 0.001  # 0.1% per side
DEFAULT_QUOTE_AMOUNT = 100  # USD per trade
```

### Modify Technical Indicators
Edit `config.py`:
```python
ATR_PERIOD = 14  # ATR lookback
RSI_PERIOD = 14  # RSI lookback
EMA_FAST = 20   # Fast EMA
EMA_SLOW = 50   # Slow EMA
```

## Troubleshooting

### "No data available" / All signals are [HOLD]
- **Cause**: Insufficient historical data or API connection issue
- **Fix**: Check internet connection and Binance API status
- **Workaround**: Try again in a few moments

### "No backtest results available"
- **Cause**: DataFrame too small or indicator calculation failed
- **Fix**: Ensure watchlist symbols are valid (e.g., BTCUSDT)
- **Workaround**: Skip backtest with `--skip-backtest` flag

### Command not found
- **Cause**: Not in trading-bot directory
- **Fix**: `cd C:\Users\Sourav Biswas\Souravjr0\trading-bot`

### Port already in use (for Telegram bot)
- **Cause**: Another instance running
- **Fix**: Run `python telegram_bot.py` in new terminal or kill prior process

## Next Steps

1. **Start with unified analyzer**: `python unified_analyzer.py`
2. **Review signals**: Look for 2/3 consensus signals
3. **Check portfolio**: Review historical performance
4. **Execute trades**: Follow risk management rules
5. **Monitor with Telegram**: `python telegram_bot.py` in background

## Integration with TradingView

For webhook-based automated execution on TradingView alerts:

1. Start webhook server: `uvicorn app:app --host 0.0.0.0 --port 8000`
2. Get ngrok URL: Use ngrok tunnel for public access
3. Configure TradingView: Add webhook alerts to bot URL
4. Alerts auto-execute trades instantly

See `TRADINGVIEW_SETUP.md` for full setup instructions.

## Support & Documentation

- **Main tracker**: `python tracker.py --help`
- **Backtest details**: `python backtest.py --help`
- **Framework integration**: `python external_frameworks.py list`
- **Bot commands**: `/help` in Telegram

---

**Master Command Remember**: `python unified_analyzer.py`

This single command gives you everything you need for professional trading analysis.
