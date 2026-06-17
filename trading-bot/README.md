# Professional Algorithmic Trading Bot

A comprehensive, production-ready trading bot for cryptocurrency and stock analysis with real-time signals, backtesting, and automated execution.

## 🚀 Quick Start

```bash
cd trading-bot
python unified_analyzer.py
```

**Done!** Get real-time market analysis with buy/sell signals in seconds.

## ✨ Features

### Core Analysis
- ✅ **Multi-timeframe analysis** (15m, 1h, 4h, 1d)
- ✅ **Consensus-based signals** (2/3 strategy voting for reliability)
- ✅ **Advanced indicators** (EMA, RSI, MACD, ATR, Bollinger Bands, Donchian Channels)
- ✅ **Real-time price tracking** of 10+ cryptocurrencies

### Trading Strategies
- 🎯 **EMA+RSI Strategy** - Trend + momentum
- 🎯 **Breakout Strategy** - Support/resistance penetration
- 🎯 **Mean Reversion Strategy** - Volatility band trading

### Backtesting & Analysis
- 📊 **Historical performance testing** with realistic fees
- 📊 **Win rate, profit factor, max drawdown** metrics
- 📊 **Walk-forward backtesting** for strategy validation
- 📊 **Trade journal** with full portfolio tracking

### Integration
- 🤖 **Telegram bot** for real-time alerts
- 🔗 **TradingView webhooks** for automated execution
- 🔄 **Multiple exchange adapters** (Binance, ccxt, python-binance)
- 🔗 **External framework support** (8 enterprise frameworks integrated)

## 📋 Installation

### Prerequisites
- Python 3.10+ installed
- Windows/Mac/Linux terminal

### Setup (First Time Only)

```bash
# Navigate to bot directory
cd C:\Users\Sourav Biswas\Souravjr0\trading-bot

# Install dependencies
pip install -r requirements.txt

# Verify installation (should complete in 30 seconds)
python unified_analyzer.py --skip-backtest --skip-portfolio
```

## 🎮 Commands

### All-in-One Analysis (Recommended)
```bash
# Complete analysis: market signals + backtest + portfolio
python unified_analyzer.py

# Fast mode: signals only (30 seconds)
python unified_analyzer.py --skip-backtest --skip-portfolio

# Custom assets
python unified_analyzer.py --crypto BTCUSDT,ETHUSDT --stocks AAPL,TSLA --forex GBPUSD=X

# Continuous mode (runs until you stop it)
python unified_analyzer.py --loop --interval 900
```

### Individual Tools
```bash
# Real-time market tracker
python tracker.py --detailed

# Backtest strategy
python backtest.py --symbol BTCUSDT --strategy all

# Telegram alerts (real-time)
python telegram_bot.py

# Trade journal
python -c "from journal import list_recent_trades; print(list_recent_trades(10))"
```

## 📊 Output Example

```
REAL-TIME MARKET ANALYSIS
Symbol    Signal  Buy Votes  Sell Votes  Strength
-------   ------  ---------  ----------  --------
BTCUSDT   [BUY]   2/3        1/3         0.67
ETHUSDT   [SELL]  1/3        2/3        -0.33
BNBUSDT   [HOLD]  0/3        0/3         0.00

BACKTEST ANALYSIS (Historical Performance)
Symbol    Strategy     Trades  PnL      Win Rate  Profit Factor
-------   ----------   ------  -------  --------  ---------------
BTCUSDT   ema_rsi      45      $2,350   62.2%     1.85
BTCUSDT   breakout     38      $1,890   55.3%     1.62

PORTFOLIO ANALYSIS
Metric              Value
--------------      -----
Total Trades        127
Winning Trades      75
Losing Trades       52
Win Rate            59.1%
Total PnL           $4,230.50
Profit Factor       1.71
```

## 🎯 How Signals Work

### Consensus-Based Voting
Three independent strategies analyze price action and vote:

1. **EMA+RSI Strategy**
   - Exponential Moving Averages (20/50 crossover)
   - RSI for momentum confirmation
   - Vote: BUY or SELL or HOLD

2. **Breakout Strategy**
   - Donchian Channel (20-bar support/resistance)
   - Breakout detection
   - Vote: BUY or SELL or HOLD

3. **Mean Reversion Strategy**
   - Bollinger Bands (2 standard deviations)
   - Overbought/oversold levels
   - Vote: BUY or SELL or HOLD

### Signal Interpretation
- **[BUY] 2/3** → 2 strategies agree = Execute BUY
- **[SELL] 3/3** → All 3 agree = Execute SELL (strongest)
- **[HOLD] -/-** → No consensus = Wait for clarity

## 💰 Risk Management (Critical!)

**ALWAYS follow these rules:**

1. **Stop Loss** = Entry ± (ATR × 2)
   - Calculated automatically in signals
   - Example: Entry $50,000 with ATR $500 → Stop at $49,000

2. **Take Profit** = Entry ± (ATR × 3)
   - Better risk/reward ratio
   - Example: Entry $50,000 with ATR $500 → Target at $51,500

3. **Position Size** = Risk 1-2% per trade
   - $10,000 account → Max $100-200 per trade
   - Never risk more than this

4. **Consensus Rule** = Require 2/3 strategy agreement
   - Reduces false signals
   - Improves win rate

## 📈 Performance Metrics

### What the Numbers Mean

| Metric | Target | Meaning |
|--------|--------|---------|
| Win Rate | > 50% | % of profitable trades |
| Profit Factor | > 1.5 | Ratio of wins to losses |
| Max Drawdown | < 20% | Worst peak-to-trough loss |
| Avg Win | > Avg Loss | Risk/reward ratio |

### Example Performance
```
Win Rate: 59%
Profit Factor: 1.71 (means $1.71 won per $1.00 lost)
Max DD: 12.5% (worst loss was 12.5%)
Avg Win: $187.50
Avg Loss: $110.00
Risk/Reward: 1.7 (good)
```

## 🔧 Configuration

### Change Watchlist
File: `.env`
```env
WATCHLIST=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,TONUSDT,AVAXUSDT,DOTUSDT
```

### Change Analysis Timeframes
```env
TRACKER_TIMEFRAMES=15m,1h,4h,1d
```

### Adjust Backtest Parameters (File: `config.py`)
```python
BACKTEST_BARS = 252        # 1 year of daily data
BACKTEST_FEE_RATE = 0.001  # 0.1% per side (Binance fee)
DEFAULT_QUOTE_AMOUNT = 100 # $100 per trade
```

## 📱 Telegram Bot Setup

### Step 1: Create Bot
- Chat [@BotFather](https://t.me/BotFather)
- `/newbot` → name your bot
- Copy the API token

### Step 2: Configure
File: `.env`
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Step 3: Start Bot
```bash
python telegram_bot.py
```

### Available Commands
```
/signals - Current buy/sell/hold signals
/portfolio - Win rate and performance metrics
/trades - Last 5 closed trades
/frameworks - External framework status
/help - Show all commands
```

## 🔗 TradingView Integration

For automatic trade execution on TradingView alerts:

```bash
# Terminal 1: Start webhook server
uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2: Get public URL
ngrok http 8000

# Copy URL to TradingView webhook alert
# Example: https://abc123.ngrok.io/execute
```

See `TRADINGVIEW_SETUP.md` for detailed instructions.

## 📁 Project Structure

```
trading-bot/
├── unified_analyzer.py          # Main command (everything at once)
├── tracker.py                   # Real-time market analysis
├── backtest.py                  # Historical performance testing
├── telegram_bot.py              # Telegram alerts & commands
├── app.py                       # TradingView webhook server
├── journal.py                   # Trade tracking database
├── indicators.py                # Technical indicators
├── strategies.py                # Trading strategies
├── exchange_client.py           # Exchange adapters
├── external_frameworks.py       # External framework runner
├── config.py                    # Configuration
├── .env                         # Secrets & API keys
├── requirements.txt             # Python dependencies
├── trader.db                    # SQLite trade journal
├── QUICK_START.md               # 3-step quickstart
├── COMPLETE_SETUP_GUIDE.md     # Full documentation
└── UNIFIED_COMMAND_GUIDE.md    # All command options
```

## ⚡ Performance

### Execution Times
- **Real-time signals only**: 15-30 seconds
- **With backtest (10 symbols)**: 3-5 minutes
- **Full analysis**: 5-10 minutes

### Data Sources
- Primary: Binance REST API (spot prices)
- Fallback: ccxt, python-binance adapters
- Storage: Local SQLite (trade journal)

## 🐛 Troubleshooting

### "No signals" / All [HOLD]
**Cause**: Insufficient historical data or API issue
**Fix**: Wait a moment and try again; check Binance API status

### Import errors
**Cause**: Missing dependencies
**Fix**: `pip install -r requirements.txt`

### "Port already in use"
**Cause**: Another bot instance running
**Fix**: Kill the other process or use `--port 8001`

## 📖 Documentation

- **Quick Start**: `QUICK_START.md` (3 steps)
- **Complete Guide**: `COMPLETE_SETUP_GUIDE.md` (detailed)
- **Command Reference**: `UNIFIED_COMMAND_GUIDE.md` (all options)
- **TradingView Setup**: `TRADINGVIEW_SETUP.md` (webhook integration)

## 🚀 Typical Workflow

### Morning (5-10 min)
```bash
python unified_analyzer.py  # Review market conditions
```

### Daytime (15-30 sec every 1-2 hrs)
```bash
python tracker.py --skip-backtest  # Quick signal check
```

### Execution (when signals align)
- Look for 2/3+ consensus signals
- Use recommended stop loss & take profit
- Risk only 1-2% of portfolio

### Evening (background)
```bash
python telegram_bot.py  # Real-time alerts while you work/sleep
```

## 📊 Key Features Breakdown

### Market Analysis
- 10+ cryptocurrencies tracked
- 4 timeframes analyzed simultaneously
- Live price feeds from Binance

### Strategy Analysis
- 3 independent technical strategies
- Consensus-based signal confirmation
- Per-strategy vote breakdown available

### Backtesting
- Walk-forward analysis on historical data
- Realistic fee deduction
- Performance metrics:
  - Win rate, Profit factor, Max drawdown
  - Average win/loss sizes
  - Expectancy calculation

### Risk Management
- ATR-based stop loss calculation
- Position sizing guidelines
- Portfolio-level PnL tracking

### Integrations
- Telegram bot with multiple commands
- TradingView webhook support
- Multiple exchange providers
- 8 external trading frameworks

## 🎓 Learning Resources

### Understanding Signals
- EMA: Exponential Moving Average (trend indicator)
- RSI: Relative Strength Index (momentum oscillator)
- Bollinger Bands: Volatility bands around moving average
- Donchian Channels: Support/resistance over N periods
- ATR: Average True Range (volatility measure)

### Strategy Details
- See `indicators.py` for technical calculations
- See `strategies.py` for signal generation logic
- See `backtest.py` for performance analysis

## 💡 Best Practices

1. **Start with backtest** - Validate strategy before trading
2. **Paper trade first** - Use testnet with real signals
3. **Monitor daily** - Check signals every morning
4. **Risk management** - Always use stops and position sizing
5. **Review weekly** - Check portfolio performance metrics

## 🤝 Support

For issues or questions:
1. Check `COMPLETE_SETUP_GUIDE.md`
2. Review `QUICK_START.md`
3. Run: `python unified_analyzer.py --help`

## 📝 License

This trading bot is provided as-is. Use at your own risk.
Trading involves substantial risk. Only risk capital you can afford to lose.

## 🔐 Security

- Keep `.env` file private (contains API keys)
- Never share your Telegram bot token
- Use Binance testnet for learning
- Enable 2FA on all exchange accounts

## 🎯 Next Steps

1. **Read**: `QUICK_START.md` (3 minutes)
2. **Run**: `python unified_analyzer.py` (5-10 minutes)
3. **Review**: Signals and backtest metrics
4. **Execute**: Follow 2/3 consensus signals
5. **Monitor**: Check results in portfolio daily

---

**Start your first analysis:**
```bash
python unified_analyzer.py
```

**Professional trading bot. Production ready. ✅**
