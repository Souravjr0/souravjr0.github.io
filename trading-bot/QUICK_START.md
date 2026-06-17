# QUICK START - Trading Bot in 3 Steps

## Step 1: Open Command Prompt
```
Windows Key + R
Type: cmd
Press Enter
```

## Step 2: Navigate to Bot
```bash
cd C:\Users\Sourav Biswas\Souravjr0\trading-bot
```

## Step 3: Run Bot
```bash
python unified_analyzer.py
```

---

## What You'll See

✅ Real-time cryptocurrency prices
✅ Trading signals ([BUY], [SELL], [HOLD])
✅ Historical performance metrics
✅ Portfolio summary
✅ Risk management guidelines

---

## What the Signals Mean

| Signal | Action |
|--------|--------|
| [BUY] 2/3 or 3/3 | Good signal to buy |
| [SELL] 2/3 or 3/3 | Good signal to sell |
| [HOLD] or no votes | Wait, not enough consensus |

---

## IMPORTANT: Risk Management

**Before trading, always:**
1. Set Stop Loss = Entry ± (ATR × 2)
2. Set Take Profit = Entry ± (ATR × 3)
3. Never risk more than 1-2% per trade
4. Wait for 2/3 strategy consensus

---

## Other Useful Commands

```bash
# Quick signals only (faster)
python tracker.py

# Backtest strategy (see past performance)
python backtest.py --symbol BTCUSDT --strategy all

# Real-time Telegram alerts
python telegram_bot.py

# Check portfolio
python -c "from journal import get_portfolio_summary; import json; print(json.dumps(get_portfolio_summary(), indent=2))"
```

---

## Troubleshooting

**"ModuleNotFoundError"**
→ Run: `pip install -r requirements.txt`

**"No signals available"**
→ Wait a moment and try again (API loading data)

**"Port already in use"**
→ Close other Python windows or use different port

---

## Complete Guide

See `COMPLETE_SETUP_GUIDE.md` for full documentation
See `UNIFIED_COMMAND_GUIDE.md` for all command options

---

## Start Now!

```bash
python unified_analyzer.py
```

Execution time: **5-10 minutes**
Next run: Wait 1-2 hours before checking again
