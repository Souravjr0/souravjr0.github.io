import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from tracker import analyze_market_symbols
from journal import get_portfolio_summary, list_recent_trades
from external_frameworks import get_framework_statuses

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", 0))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _format_price(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"${value:.4f}"
    return str(value)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show welcome message and available commands."""
    welcome_text = """
🤖 **Trading Bot Started!**

Available Commands:
/signals - Get market signals (multi-timeframe analysis)
/portfolio - Check portfolio & balance
/trades - View recent trades
/frameworks - External framework status
/ml [symbol] - Get on-demand ML signal & SHAP explanation (e.g. /ml BTCUSDT)
/sentiment [symbol] - Get on-demand news sentiment score (e.g. /sentiment BTCUSDT)
/help - Show this message
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    logger.info(f"User {update.message.chat_id} started the bot")


async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get market signals for watchlist symbols."""
    await update.message.reply_text("📊 Analyzing markets... This may take a moment.", parse_mode='Markdown')
    
    try:
        results = analyze_market_symbols()
        
        if not results:
            await update.message.reply_text("❌ No signals generated. Try again later.")
            return
        
        buy_list: list[tuple[str, object, int, int]] = []
        sell_list: list[tuple[str, object, int, int]] = []
        wait_list: list[tuple[str, object, int, int]] = []

        for symbol, data in results.items():
            signals = data.get("signals", {})
            buy_count = sum(1 for s in signals.values() if s.get("action") == "BUY")
            sell_count = sum(1 for s in signals.values() if s.get("action") == "SELL")
            price = data.get("current_price", "N/A")
            entry = (symbol, price, buy_count, sell_count)
            active = buy_count + sell_count

            if active == 0:
                continue

            if buy_count > sell_count:
                buy_list.append(entry)
            elif sell_count > buy_count:
                sell_list.append(entry)
            else:
                wait_list.append(entry)

        buy_list.sort(key=lambda x: (x[2] - x[3], x[0]), reverse=True)
        sell_list.sort(key=lambda x: (x[3] - x[2], x[0]), reverse=True)
        wait_list.sort(key=lambda x: x[0])

        message = "📈 **Market Signals (Multi-Timeframe)**\n\n"
        message += "**Quick Lists**\n"
        if buy_list:
            message += "🟢 **Buy List**\n"
            for symbol, price, buy_count, sell_count in buy_list:
                message += f"{symbol} @ {_format_price(price)} ({buy_count} BUY / {sell_count} SELL)\n"
        else:
            message += "🟢 **Buy List**\nNone\n"

        if sell_list:
            message += "\n🔴 **Sell List**\n"
            for symbol, price, buy_count, sell_count in sell_list:
                message += f"{symbol} @ {_format_price(price)} ({buy_count} BUY / {sell_count} SELL)\n"
        else:
            message += "\n🔴 **Sell List**\nNone\n"

        if wait_list:
            message += "\n⚪ **Wait List**\n"
            for symbol, price, buy_count, sell_count in wait_list:
                message += f"{symbol} @ {_format_price(price)} ({buy_count} BUY / {sell_count} SELL)\n"

        message += "\n"
        
        for symbol, data in results.items():
            message += f"**{symbol}**\n"
            message += f"Price: {_format_price(data.get('current_price', 'N/A'))}\n"
            
            for tf, signals in data.get('signals', {}).items():
                signal = signals.get('signal', 'NEUTRAL')
                score = signals.get('score', '0/3')
                action = signals.get('action', 'WAIT')
                stop = signals.get('stop')
                take = signals.get('take')
                per_strategy = signals.get('per_strategy', {})
                emoji = '🟢' if signal == 'LONG' else '🔴' if signal == 'SHORT' else '⚪'
                message += f"  {emoji} {tf}: **{action}** ({signal} {score})\n"
                if stop is not None or take is not None:
                    stop_text = f"${stop:.4f}" if isinstance(stop, (int, float)) else "n/a"
                    take_text = f"${take:.4f}" if isinstance(take, (int, float)) else "n/a"
                    message += f"     Stop: {stop_text} | Take: {take_text}\n"
                if per_strategy:
                    message += (
                        "     EMA+RSI: {ema} | Breakout: {brk} | MeanRev: {mr}\n"
                    ).format(
                        ema=per_strategy.get("EMA_RSI", "n/a"),
                        brk=per_strategy.get("BREAKOUT", "n/a"),
                        mr=per_strategy.get("MEAN_REV", "n/a"),
                    )
            
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in signals_command: {e}")
        await update.message.reply_text(f"❌ Error fetching signals: {str(e)}")


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show portfolio summary and balance."""
    try:
        summary = get_portfolio_summary()
        
        message = "💼 **Portfolio Summary**\n\n"
        message += f"Total Trades: {summary['total_trades']}\n"
        message += f"Wins: {summary['wins']} | Losses: {summary['losses']}\n"
        message += f"Win Rate: {summary['win_rate']:.2f}%\n"
        message += f"Gross PnL: ${summary['gross_pnl']:.2f}\n"
        message += f"Net PnL: ${summary['net_pnl']:.2f}\n"
        message += f"Avg Win: ${summary['avg_win']:.2f}\n"
        message += f"Avg Loss: ${summary['avg_loss']:.2f}\n"
        
        if summary['open_positions']:
            message += "\n**Open Positions:**\n"
            for pos in summary['open_positions']:
                qty = pos['qty']
                entry = pos['entry_price']
                unrealized = pos.get('unrealized_pnl')
                unrealized_pct = pos.get('unrealized_pnl_pct')
                message += f"{pos['symbol']}: {qty:.6f} @ ${entry:.2f} | "
                if unrealized is None or unrealized_pct is None:
                    message += "Unrealized: n/a\n"
                else:
                    message += f"Unrealized: ${unrealized:.2f} ({unrealized_pct:.2f}%)\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in portfolio_command: {e}")
        await update.message.reply_text(f"❌ Error fetching portfolio: {str(e)}")


async def trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent trades from journal."""
    try:
        trades = list_recent_trades(limit=10)

        if not trades:
            await update.message.reply_text("No trades found in journal.")
            return

        message = "📋 **Recent Trades (Last 10)**\n\n"

        for trade in trades:
            emoji = '✅' if trade['side'] == 'BUY' else '❌'
            message += f"{emoji} {trade['symbol']} {trade['side']}\n"
            message += f"  Price: ${trade['price']:.4f} | Qty: {trade['qty']:.6f}\n"
            message += f"  Strategy: {trade['strategy'] or '-'} | TF: {trade['timeframe'] or '-'}\n"
            message += f"  {trade['timestamp']}\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in trades_command: {e}")
        await update.message.reply_text(f"❌ Error fetching trades: {str(e)}")


async def frameworks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show external framework status."""
    statuses = get_framework_statuses()
    message = "🧩 **External Frameworks**\n\n"
    for status in statuses:
        if status["path_exists"] and status["entry_exists"]:
            state = "✅ Ready"
        elif status["path_exists"]:
            state = "⚠️ Missing entrypoint"
        else:
            state = "⚠️ Missing path"
        message += f"{state} — {status['name']}\n"
    await update.message.reply_text(message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    help_text = """
🤖 **Trading Bot Help**

**Commands:**
/signals - Get multi-timeframe market signals
/portfolio - Portfolio summary & P&L
/trades - View recent trades
/frameworks - External framework status
/ml [symbol] - Get on-demand ML prediction & SHAP key drivers (e.g. /ml BTCUSDT)
/sentiment [symbol] - Get on-demand news sentiment score (e.g. /sentiment BTCUSDT)
/help - Show this help message

**Features:**
• Real-time market analysis across 15m, 1h, 4h, 1d timeframes
• Multi-strategy consensus signaling (EMA+RSI, Breakout, Mean Reversion)
• XGBoost + LightGBM ensemble ML prediction model
• Automated trade journal with P&L tracking
• Position tracking with unrealized P&L

**Note:** This bot monitors your trading account. Use responsibly!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def send_alert(chat_id: int, alert_message: str):
    """Send an alert to Telegram (used by webhook/tracker)."""
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        await app.bot.send_message(chat_id=chat_id, text=alert_message, parse_mode='Markdown')
        logger.info(f"Alert sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


async def send_signal_alert(
    symbol: str,
    timeframe: str,
    signal: str,
    score: str,
    price: float,
    stop: float | None = None,
    take: float | None = None,
):
    """Send trading signal alert to Telegram."""
    action = "BUY" if signal == "LONG" else "SELL" if signal == "SHORT" else "WAIT"
    emoji = '🟢 LONG' if signal == 'LONG' else '🔴 SHORT' if signal == 'SHORT' else '⚪ NEUTRAL'
    stop_text = f"${stop:.4f}" if isinstance(stop, (int, float)) else "n/a"
    take_text = f"${take:.4f}" if isinstance(take, (int, float)) else "n/a"
    alert = f"""
🚨 **Trading Signal**

Symbol: `{symbol}`
Timeframe: `{timeframe}`
Action: **{action}**
Signal: {emoji} ({score})
Current Price: `${price:.2f}`
Stop: {stop_text} | Take: {take_text}
    """
    await send_alert(TELEGRAM_CHAT_ID, alert)


def send_telegram_message(message: str) -> bool:
    """Send a Telegram message synchronously using requests."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            logger.error(f"Telegram API responded with status {res.status_code}: {res.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def send_trade_execution_alert(symbol: str, side: str, qty: float, price: float, sl: float | None, tp: float | None, risk_pct: float, notional: float) -> bool:
    """Send trade execution alert with premium HTML formatting."""
    side_emoji = "🟢" if side.upper() == "BUY" else "🔴"
    sl_str = f"${sl:.4f}" if sl else "None"
    tp_str = f"${tp:.4f}" if tp else "None"
    
    msg = f"""🚀 <b>TRADE EXECUTION ALERT</b>

<b>Symbol:</b> <code>{symbol}</code>
<b>Action:</b> {side_emoji} <b>{side}</b>
<b>Quantity:</b> <code>{qty:.6f}</code>
<b>Execution Price:</b> <code>${price:.4f}</code>
<b>Notional Value:</b> <code>${notional:.2f}</code>
<b>Risk Allocated:</b> <code>{risk_pct:.2f}%</code> of Equity

🛡️ <b>Risk Parameters Enforced:</b>
🔴 <b>Stop Loss (SL):</b> <code>{sl_str}</code>
🟢 <b>Take Profit (TP):</b> <code>{tp_str}</code>"""
    return send_telegram_message(msg)


def send_exit_alert(symbol: str, side: str, qty: float, price: float, profit: float, reason: str) -> bool:
    """Send trade exit/close alert with realized profit/loss."""
    side_emoji = "🔴" if side.upper() == "SELL" else "🟢"
    pnl_emoji = "✅" if profit >= 0 else "❌"
    
    msg = f"""🚪 <b>POSITION CLOSED ALERT</b>

<b>Symbol:</b> <code>{symbol}</code>
<b>Action:</b> {side_emoji} <b>{side} (Close)</b>
<b>Quantity:</b> <code>{qty:.6f}</code>
<b>Exit Price:</b> <code>${price:.4f}</code>
<b>Realized P&amp;L:</b> {pnl_emoji} <b>${profit:.2f}</b>

💡 <b>Exit Reason:</b> <code>{reason}</code>"""
    return send_telegram_message(msg)


def send_consensus_signal_alert(
    symbol: str,
    action: str,
    score: str,
    price: float,
    sl: float | None,
    tp: float | None,
    regime: str,
    ml_signal: str | None = None,
    ml_confidence: float = 0.0,
    shap_explanation: str | None = None,
    kf_zscore: float | None = None,
    ewma_vol: float | None = None,
    q_regime: str | None = None,
    tv_rating: str | None = None,
    tv_rsi: float | None = None,
) -> bool:
    """Send trading signal consensus alert to Telegram."""
    action_emoji = "🟢" if action.upper() == "BUY" else "🔴" if action.upper() == "SELL" else "⚪"
    sl_str = f"${sl:.4f}" if sl else "None"
    tp_str = f"${tp:.4f}" if tp else "None"
    
    msg = f"""🚨 <b>SUPER-CONSENSUS SIGNAL DETECTED</b>

<b>Symbol:</b> <code>{symbol}</code>
<b>Consensus Score:</b> <b>{score}</b>
<b>Action Recommendation:</b> {action_emoji} <b>{action}</b>
<b>Current Price:</b> <code>${price:.4f}</code>
<b>Market Regime:</b> <code>{regime}</code>"""

    if q_regime is not None or kf_zscore is not None or ewma_vol is not None:
        msg += f"\n\n📊 <b>Hedge Fund Quant Engine:</b>"
        if q_regime:
            msg += f"\n<b>Quant Regime:</b> <code>{q_regime}</code>"
        if kf_zscore is not None:
            msg += f"\n<b>Kalman innovation Z:</b> <code>{kf_zscore:+.4f}</code>"
        if ewma_vol is not None:
            msg += f"\n<b>EWMA Volatility:</b> <code>{ewma_vol:.4%}</code>"

    if ml_signal is not None and ml_signal != "HOLD":
        ml_emoji = "🟢 BUY" if ml_signal == "BUY" else "🔴 SELL"
        msg += f"\n\n🔮 <b>ML Ensemble Predictor:</b>"
        msg += f"\n<b>ML Signal:</b> {ml_emoji} (Conf: <code>{ml_confidence:.2%}</code>)"
        if shap_explanation:
            msg += f"\n<b>SHAP Drivers:</b>\n{shap_explanation}"

    if tv_rating is not None:
        msg += f"\n\n📈 <b>TradingView Scanner Consensus:</b>"
        msg += f"\n<b>Technical Recommendation:</b> <code>{tv_rating}</code>"
        if tv_rsi is not None:
            msg += f"\n<b>Relative Strength Index (RSI):</b> <code>{tv_rsi:.1f}</code>"

    msg += f"""\n\n🛡️ <b>Suggested Risk Targets:</b>
🔴 <b>Stop Loss (SL):</b> <code>{sl_str}</code>
🟢 <b>Take Profit (TP):</b> <code>{tp_str}</code>"""
    return send_telegram_message(msg)



def send_llm_desk_alert(
    symbol: str,
    action: str,
    confidence: float,
    reasoning: str,
    bull_case: str = "",
    bear_case: str = "",
    risk_assessment: str = "",
) -> bool:
    """Send LLM Trading Desk analysis alert to Telegram."""
    action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(action.upper(), "⚪")
    
    msg = f"""🤖 <b>LLM TRADING DESK ANALYSIS</b>

<b>Symbol:</b> <code>{symbol}</code>
<b>Decision:</b> {action_emoji} <b>{action}</b> ({confidence:.0%} confidence)"""

    if reasoning:
        msg += f"\n\n<b>Reasoning:</b>\n<i>{reasoning[:300]}</i>"

    if bull_case:
        msg += f"\n\n📈 <b>Bull Case:</b>\n<i>{bull_case[:200]}</i>"

    if bear_case:
        msg += f"\n\n📉 <b>Bear Case:</b>\n<i>{bear_case[:200]}</i>"

    if risk_assessment:
        msg += f"\n\n🛡️ <b>Risk Assessment:</b>\n<i>{risk_assessment[:200]}</i>"

    return send_telegram_message(msg)


def send_daily_digest_alert(summary_text: str) -> bool:
    """Send a daily digest or cycle summary update."""
    msg = f"""📊 <b>DAILY TRADING DIGEST</b>

{summary_text}"""
    return send_telegram_message(msg)



async def ml_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get on-demand ML signal & SHAP explanation."""
    symbol = "BTCUSDT"
    if context.args:
        symbol = context.args[0].upper().strip()
        
    await update.message.reply_text(f"🔮 <b>Running XGBoost + LightGBM ML Analysis for {symbol}...</b>", parse_mode='HTML')
    
    try:
        from unified_analyzer import fetch_data_unified, is_stock
        from ml_engine import MLSignalEngine
        from model_explainer import explain_prediction, format_explanation_text
        
        df = fetch_data_unified(symbol, "1h", 500)
        if df.empty or len(df) < 60:
            await update.message.reply_text(f"❌ Failed to fetch sufficient data for {symbol} (need at least 60 bars).")
            return
            
        engine = MLSignalEngine(symbol, "1h")
        
        # Train on-demand if no model exists or model is stale
        if not engine.load_model():
            await update.message.reply_text(f"🔄 ML model for {symbol} not found. Training model now, please wait...")
            metrics = engine.train(df)
            if "error" in metrics:
                await update.message.reply_text(f"❌ ML Model training failed: {metrics['error']}")
                return
            engine.load_model()
            
        signal, confidence = engine.predict(df)
        explanations = explain_prediction(engine, df, top_n=3)
        explanation_text = format_explanation_text(explanations)
        
        signal_emoji = "🟢 BUY" if signal == "BUY" else "🔴 SELL" if signal == "SELL" else "⚪ HOLD"
        
        message = f"""🔮 <b>ML PROMPT PREDICTION REPORT: {symbol}</b>
        
<b>Timeframe:</b> <code>1h</code>
<b>Ensemble Signal:</b> <b>{signal_emoji}</b>
<b>Model Confidence:</b> <code>{confidence:.2%}</code>

🎯 <b>SHAP Key Technical Drivers (Top 3):</b>
{explanation_text}
"""
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in ml_command: {e}")
        await update.message.reply_text(f"❌ Error during ML analysis: {str(e)}")


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get on-demand news sentiment score."""
    symbol = "BTCUSDT"
    if context.args:
        symbol = context.args[0].upper().strip()
        
    await update.message.reply_text(f"📰 <b>Parsing financial news sentiment for {symbol}...</b>", parse_mode='HTML')
    
    try:
        from unified_analyzer import is_stock
        from sentiment_analyzer import get_sentiment
        
        is_stock_flag = is_stock(symbol)
        api_symbol = symbol
        if not is_stock_flag:
            for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                if symbol.endswith(quote) and len(symbol) > len(quote):
                    api_symbol = symbol[:-len(quote)]
                    break
                    
        result = get_sentiment(api_symbol, is_stock=is_stock_flag)
        
        score = result.get("score", 0.0)
        label = result.get("sentiment_label", "NEUTRAL")
        count = result.get("headline_count", 0)
        headline = result.get("top_headline", "None")
        
        label_emoji = "🟢 BULLISH" if label == "BULLISH" else "🔴 BEARISH" if label == "BEARISH" else "⚪ NEUTRAL"
        
        message = f"""📰 <b>NEWS SENTIMENT REPORT: {symbol}</b>
        
<b>Asset:</b> <code>{api_symbol}</code> ({"Stock" if is_stock_flag else "Crypto"})
<b>Sentiment Score:</b> <b>{score:+.4f}</b>
<b>Sentiment Outlook:</b> {label_emoji}
<b>Headlines Analyzed:</b> <code>{count}</code>

🔥 <b>Highest Impact Headline:</b>
<i>"{headline}"</i>
"""
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in sentiment_command: {e}")
        await update.message.reply_text(f"❌ Error fetching sentiment: {str(e)}")


async def quant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get on-demand Quant indicators (Kalman Filter, EWMA Volatility, Hurst, and Regime)."""
    symbol = "BTCUSDT"
    if context.args:
        symbol = context.args[0].upper().strip()
        
    await update.message.reply_text(f"📊 <b>Running Quant Engine Analysis for {symbol}...</b>", parse_mode='HTML')
    
    try:
        from unified_analyzer import fetch_data_unified, is_stock
        from feature_engineering import extract_features
        import quant_engine
        
        # Fetch 200 bars for statistical stability
        df = fetch_data_unified(symbol, "1h", 200)
        if df.empty or len(df) < 50:
            await update.message.reply_text(f"❌ Failed to fetch sufficient data for {symbol} (need at least 50 bars).")
            return
            
        # Extract features for Hurst exponent
        df = extract_features(df)
        
        # Run Kalman
        kf = quant_engine.KalmanFilter1D()
        kf_filtered, kf_residuals, kf_zscores = kf.run_filter(df["close"].values)
        kf_zscore = float(kf_zscores[-1])
        kf_val = float(kf_filtered[-1])
        
        # Run EWMA Volatility
        returns = df["close"].pct_change()
        ewma_vols = quant_engine.compute_ewma_volatility(returns, decay=0.94)
        ewma_vol = float(ewma_vols.iloc[-1])
        
        # Hurst and Regime classification
        hurst_exp = float(df["feat_hurst"].iloc[-1]) if "feat_hurst" in df.columns else 0.5
        q_regime = quant_engine.classify_quant_regime(df, kf_zscore, hurst_exp, ewma_vol)
        
        current_price = float(df["close"].iloc[-1])
        kf_dev = ((current_price - kf_val) / kf_val) if kf_val > 0 else 0.0
        
        message = f"""📊 <b>QUANT REGIME REPORT: {symbol}</b>
        
<b>Current Price:</b> <code>${current_price:.4f}</code>
<b>Kalman Filter Estimate:</b> <code>${kf_val:.4f}</code> (Dev: <code>{kf_dev:+.2%}</code>)
<b>Kalman Innovation Z-Score:</b> <code>{kf_zscore:+.4f}</code>
<b>EWMA Dynamic Volatility:</b> <code>{ewma_vol:.4%}</code>
<b>Hurst Exponent (50b):</b> <code>{hurst_exp:.4f}</code>
<b>Statistical Regime:</b> <b>{q_regime}</b>

💡 <i>Regime Explanation:
Hurst > 0.52 indicates persistence (trending).
Hurst < 0.48 indicates anti-persistence (mean-reverting).
Kalman Z shows the normalized price deviation from the true hidden price trend.</i>
"""
        await update.message.reply_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in quant_command: {e}")
        await update.message.reply_text(f"❌ Error during quant analysis: {str(e)}")


def run_telegram_bot():
    """Run the Telegram bot (blocking)."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        return
    
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == 0:
        logger.error("TELEGRAM_CHAT_ID not set in .env")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signals", signals_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("trades", trades_command))
    app.add_handler(CommandHandler("frameworks", frameworks_command))
    app.add_handler(CommandHandler("ml", ml_command))
    app.add_handler(CommandHandler("sentiment", sentiment_command))
    app.add_handler(CommandHandler("quant", quant_command))
    app.add_handler(CommandHandler("help", help_command))
    
    logger.info("Telegram bot started. Listening for commands...")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
