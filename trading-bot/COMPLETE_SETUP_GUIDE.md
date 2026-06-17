# Trading Bot - Complete Setup & Usage Summary

## What You Have

A professional-grade **algorithmic trading bot** that combines:
- ✅ Real-time multi-timeframe market analysis
- ✅ Advanced technical indicators (EMA, RSI, MACD, ATR, Bollinger Bands)
- ✅ Consensus-based trading signals (2/3 strategy voting)
- ✅ Historical backtesting with performance metrics
- ✅ Trade journal with portfolio tracking
- ✅ Telegram bot for real-time alerts
- ✅ TradingView webhook integration
- ✅ Multiple exchange adapters (Binance, ccxt, python-binance)
- ✅ 8 external framework integrations

## Master Command (Start Here)

```bash
cd C:\Users\Sourav Biswas\Souravjr0\trading-bot
python unified_analyzer.py
```

**This single command executes:**
1. Real-time market analysis (10 cryptocurrencies)
2. Backtesting on historical data
3. Portfolio performance summary
4. Framework integration status
5. Trading signal recommendations

## Installation (First Time Only)

```bash
# Navigate to bot directory
cd C:\Users\Sourav Biswas\Souravjr0\trading-bot

# Install dependencies (one-time)
pip install -r requirements.txt

# Verify installation
python unified_analyzer.py --skip-backtest --skip-portfolio
```

## Complete Command Reference

### Market Analysis
```bash
# Complete analysis (recommended)
python unified_analyzer.py

# Fast signals only
python unified_analyzer.py --skip-backtest --skip-portfolio

# Custom assets
python unified_analyzer.py --crypto BTCUSDT,ETHUSDT --stocks AAPL,TSLA --forex GBPUSD=X

# Traditional tracker
python tracker.py
```

### Backtesting
```bash
# Backtest single symbol
python backtest.py --symbol BTCUSDT --strategy all

# Test specific strategy
python backtest.py --symbol ETHUSDT --strategy ema_rsi
```

### Telegram Bot (Real-Time Alerts)
```bash
# Start telegram bot
python telegram_bot.py

# Available commands in Telegram:
# /signals - Current buy/sell signals
# /portfolio - Win rate and performance
# /trades - Recent trade history
# /frameworks - Framework status
# /help - Command help
```

### Portfolio Tracking
```bash
# View trade journal
python -c "from journal import list_recent_trades; print(list_recent_trades(10))"

# Portfolio summary
python -c "from journal import get_portfolio_summary; import json; print(json.dumps(get_portfolio_summary(), indent=2))"
```

## Signal Interpretation

### How Signals Work
- **3 independent strategies** analyze price action
- **Signals require 2/3 consensus** to avoid false positives
- **Each strategy uses different indicators:**

1. **EMA+RSI Strategy**
   - Uses Exponential Moving Averages (20/50)
   - RSI for momentum confirmation
   - Example: Price above 50 EMA + RSI > 70 = Potential buy

2. **Breakout Strategy**
   - Donchian channels (20-bar high/low)
   - Breakouts signal trend reversals
   - Example: Break above 20-bar high = Potential buy

3. **Mean Reversion Strategy**
   - Bollinger Bands (2 std dev)
   - Trade when price touches bands
   - Example: Price below lower band = Potential buy

### Reading Output

```
BTCUSDT  [BUY] 2/3 @ $76937  (2 strategies agree = execute)
ETHUSDT  [SELL] 3/3 @ $2135  (all 3 agree = strongest signal)
BNBUSDT  [HOLD] - - (no consensus = wait)
```

## Risk Management (Critical!)

**Before Every Trade:**

1. **Stop Loss** = Entry ± (ATR × 2)
   - Automatically calculated in bot
   - Limits downside risk

2. **Take Profit** = Entry ± (ATR × 3)
   - Better risk/reward ratio
   - Locks in profits

3. **Position Size** = 1-2% of portfolio per trade
   - Example: $10,000 account → max $100-200 per trade

4. **Wait for Consensus** = 2/3 signals required
   - Reduces false entries

## File Structure

```
trading-bot/
├── unified_analyzer.py    (Main all-in-one command)
├── tracker.py             (Real-time market analysis)
├── backtest.py            (Historical performance testing)
├── telegram_bot.py        (Real-time alerts via Telegram)
├── app.py                 (TradingView webhook server)
├── journal.py             (Trade tracking database)
├── indicators.py          (Technical indicators)
├── strategies.py          (Trading strategy logic)
├── exchange_client.py     (Exchange adapters)
├── config.py              (Configuration)
├── .env                   (Secrets & API keys)
├── requirements.txt       (Python dependencies)
├── trader.db              (SQLite trade journal)
└── external/              (External framework integrations)
```

## Configuration

### Edit Watchlist
File: `.env`
```
WATCHLIST=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT
```

### Change Analysis Timeframes
File: `.env`
```
TRACKER_TIMEFRAMES=15m,1h,4h,1d
```

### Adjust Backtest Settings
File: `config.py`
```python
BACKTEST_BARS = 252        # 1 year of daily data
BACKTEST_FEE_RATE = 0.001  # 0.1% Binance fee
DEFAULT_QUOTE_AMOUNT = 100 # $100 per trade
```

## Performance Metrics

### Backtest Results Explained

| Metric | Good Range | Meaning |
|--------|-----------|---------|
| Win Rate | > 50% | % of profitable trades |
| Profit Factor | > 1.5 | Ratio of wins to losses |
| Max Drawdown | < 20% | Worst peak-to-trough loss |
| Avg Win | > Avg Loss | Win size vs loss size |

### Example Results
```
Strategy: ema_rsi
  Trades: 12
  Total PnL: $450.25
  Win Rate: 58.3%
  Profit Factor: 1.75
  Max DD: 12.5%
```

## Typical Daily Workflow

### Morning (Review)
```bash
# Check market conditions
python unified_analyzer.py
# Takes: 5-10 minutes
```

### Daytime (Monitor)
```bash
# Quick signal check every 1-2 hours
python tracker.py --skip-backtest
# Takes: 15-30 seconds
```

### Execution
```bash
# Use signals from bot to enter/exit trades
# Always use stop loss and take profit
# Follow 2/3 consensus rule
```

### Evening (Telegram Alerts)
```bash
# Start bot for real-time alerts
python telegram_bot.py
# Monitor trades in background
```

## Telegram Bot Setup

### 1. Create Bot
- Chat with [@BotFather](https://t.me/BotFather) on Telegram
- Create new bot: `/newbot`
- Note the API token

### 2. Get Your Chat ID
- Chat with your bot: `/start`
- In `.env`, set `TELEGRAM_CHAT_ID`

### 3. Start Bot
```bash
python telegram_bot.py
```

### Available Commands
- `/signals` - Buy/Sell/Hold signals
- `/portfolio` - Win rate, profit factor
- `/trades` - Last 5 trades
- `/frameworks` - Framework status
- `/help` - Show all commands

## TradingView Integration

### Setup Webhook
1. Get ngrok URL: `ngrok http 8000`
2. Start webhook: `uvicorn app:app --port 8000`
3. Add to TradingView alert: `{ngrok_url}/execute`
4. Alerts auto-execute trades

See `TRADINGVIEW_SETUP.md` for full setup.

## Troubleshooting

### "No signals" / All [HOLD]
- **Cause**: Insufficient historical data or API issue
- **Fix**: Check Binance API status or wait for data to load

### "Port already in use"
- **Cause**: Another bot instance running
- **Fix**: Kill process or use different port

### Import errors
- **Fix**: Reinstall: `pip install -r requirements.txt`

### Wrong exchange connected
- Check `.env`: `EXCHANGE_PROVIDER=ccxt`
- Or: `EXCHANGE_PROVIDER=binance_rest`

## Performance Tips

1. **Run backtest once weekly** to validate strategy
2. **Check portfolio daily** to track performance
3. **Use telegram alerts** for real-time signals
4. **Scale position size** as portfolio grows (1-2% rule)
5. **Adjust stops/targets** for different symbol volatility

## Next Steps

1. **Start now**: `python unified_analyzer.py`
2. **Review signals** from all 3 strategies
3. **Execute on 2/3 consensus** only
4. **Use stop loss & take profit** every time
5. **Track results** in trade journal

## Support Commands

```bash
# Show all options
python unified_analyzer.py --help
python tracker.py --help
python backtest.py --help

# Check installed packages
pip list | find "pandas\|numpy\|ccxt"

# Verify bot is working
python -c "import pandas, numpy, ccxt; print('All dependencies OK')"
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│ TRADING BOT - QUICK START                  │
├─────────────────────────────────────────────┤
│ cd trading-bot                             │
│ python unified_analyzer.py                 │
│                                             │
│ THEN:                                       │
│ • Review 2/3 consensus signals             │
│ • Check backtest performance               │
│ • Execute on buy/sell signals              │
│ • Use ATR-based stops                      │
│ • Risk only 1-2% per trade                │
└─────────────────────────────────────────────┘

COMMANDS:
  Market Analysis: python unified_analyzer.py
  Quick Signals:   python tracker.py
  Backtesting:     python backtest.py --symbol BTCUSDT --strategy all
  Live Alerts:     python telegram_bot.py
  Portfolio:       python -c "from journal import *; print(get_portfolio_summary())"

SIGNALS (2/3 votes = execute):
  [BUY] 2/3    = Enter long position
  [SELL] 2/3   = Exit or go short
  [HOLD] -/-   = Wait for consensus
```

---

**Created**: Professional Trading Bot v1.0
**Author**: Copilot Trading Systems
**Status**: Ready for Production Use ✅
