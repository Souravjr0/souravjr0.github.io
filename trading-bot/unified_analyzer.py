#!/usr/bin/env python3
"""
Unified Multi-Market Trading Bot Analyzer & Opportunity Finder
Orchestrates automated stock/crypto discovery, technical analysis,
advanced indicator scans, backtesting, and portfolio tracking in a single run.

Run: python unified_analyzer.py
"""

import os
import sys

# Dynamic path resolution to support restructured package layouts and nested submodules
project_root = os.path.dirname(os.path.abspath(__file__))
for subfolder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, subfolder))
sys.path.append(project_root)

import argparse
import subprocess
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

# Core config & indicators
from config import (
    WATCHLIST, TRACKER_TIMEFRAMES, TRACKER_BARS, QUOTE_ASSET,
    BACKTEST_FEE_RATE, DEFAULT_QUOTE_AMOUNT, ATR_PERIOD,
    ATR_MULTIPLIER_SL, ATR_MULTIPLIER_TP
)
from indicators import add_indicators
from strategies import evaluate_latest_signals, add_strategy_signals
from advanced_skills import analyze_advanced
from journal import get_portfolio_summary, list_recent_trades, save_trade
from exchange_client import get_spot_client
from market_data import fetch_klines, klines_to_dataframe
from external_frameworks import get_framework_statuses
import high_conviction
import telegram_bot
import discovery
import portfolio_optimizer
import sentiment_analyzer
import ml_engine
import model_explainer
import metrics_server
import structured_logger
import tradingagents_plugin
import online_learner
import rl_trader
import re

# Initialize Sentry for production exception-tracking and diagnostics
from config import SENTRY_DSN, SENTRY_ENVIRONMENT

if SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0
        )
        print(f"[Monitoring] Sentry initialized successfully in environment: {SENTRY_ENVIRONMENT}")
    except Exception as e:
        print(f"[Monitoring] Failed to initialize Sentry: {e}")

class Colors:
    GREEN = ""
    RED = ""
    YELLOW = ""
    BLUE = ""
    CYAN = ""
    MAGENTA = ""
    BOLD = ""
    UNDERLINE = ""
    END = ""

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
def visible_len(s: str) -> int:
    return len(ANSI_ESCAPE.sub('', str(s)))

# Keep a global/static reference to the ctypes callback to prevent garbage collection on Windows
_win32_ctrl_handler_ref = None

def win32_ctrl_handler(ctrl_type):
    if ctrl_type in (0, 1, 2, 5, 6):  # CTRL_C, CTRL_BREAK, CTRL_CLOSE, etc.
        print("\n\n[Terminated] Force stopping the Multi-Market opportunity scanner via Windows Console Handler. Goodbye!")
        try:
            from external_frameworks import terminate_active_framework
            terminate_active_framework()
        except Exception:
            pass
        import os
        os._exit(0)
    return True

HRP_WEIGHTS: dict[str, float] = {}
ML_CONFIDENCES: dict[str, float] = {}

def resolve_symbol_ticker(symbol: str) -> str:
    """Intelligently map indices, commodities, and fuzzy tickers to their canonical yfinance or exchange tickers."""
    sym = symbol.strip().upper()
    
    # 1. Standard Dictionary of popular global indices and commodities
    mappings = {
        # Indices
        "DJI": "^DJI",
        "DJIUSD": "^DJI",
        "DOW": "^DJI",
        "DOWJONES": "^DJI",
        "SPX": "^GSPC",
        "SP500": "^GSPC",
        "SPXUSD": "^GSPC",
        "GSPC": "^GSPC",
        "IXIC": "^IXIC",
        "NASDAQ": "^IXIC",
        "COMP": "^IXIC",
        "NDX": "^NDX",
        "NASDAQ100": "^NDX",
        "RUT": "^RUT",
        "RUSSELL": "^RUT",
        "VIX": "^VIX",
        "VIXUSD": "^VIX",
        "FTSE": "^FTSE",
        "FTSE100": "^FTSE",
        "N225": "^N225",
        "NIKKEI": "^N225",
        "NSEI": "^NSEI",
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "BSESN": "^BSESN",
        "SENSEX": "^BSESN",
        # Commodities (Futures)
        "GOLD": "GC=F",
        "GC": "GC=F",
        "XAUUSD": "GC=F",
        "SILVER": "SI=F",
        "SI": "SI=F",
        "XAGUSD": "SI=F",
        "OIL": "CL=F",
        "CRUDE": "CL=F",
        "CRUDEOIL": "CL=F",
    }
    
    if sym in mappings:
        return mappings[sym]
        
    # 2. Handle generic DJIUSD / SPXUSD style where they end with USD but the prefix is a known index
    if sym.endswith("USD") and len(sym) > 3:
        prefix = sym[:-3]
        if prefix in mappings:
            return mappings[prefix]
            
    # 3. Handle Forex currency spot pairs (6-character combination of fiat currencies)
    forex_currencies = {
        "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", 
        "SGD", "HKD", "CNY", "INR", "MXN", "ZAR", "SEK", "NOK", 
        "TRY", "RUB", "BRL", "TWD", "KRW"
    }
    if len(sym) == 6 and sym[:3] in forex_currencies and sym[3:] in forex_currencies:
        if not sym.endswith("=X"):
            return f"{sym}=X"
            
    return sym

def is_stock(symbol: str) -> bool:
    """Helper to detect if a symbol is a stock/index or a crypto pair, after resolution."""
    resolved = resolve_symbol_ticker(symbol)
    
    # Indices, forex standard tickers, and futures are all traditional stock assets
    if any(char in resolved for char in {"=", "^"}):
        return True
        
    if resolved in discovery.STOCK_WATCHLIST:
        return True
        
    # Suffix checks
    if resolved.endswith("USDT") or resolved.endswith("BTC") or resolved.endswith("ETH"):
        return False
        
    # Futures, indices, stocks with dots/dashes
    if any(char in resolved for char in {"-", "."}):
        return True
        
    # If it is alphabetic and length <= 5, it is a stock (e.g. AAPL, GLD)
    return len(resolved) <= 5 and resolved.isalpha()

def fetch_data_unified(symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    """Robust data loader supporting both Binance Crypto and Yahoo Finance Stocks with DARE integration."""
    symbol = symbol.strip().upper()
    resolved = resolve_symbol_ticker(symbol)
    
    df = pd.DataFrame()
    if is_stock(symbol):
        # Fetch stock/index/forex data from Yahoo Finance using the resolved canonical ticker
        df = discovery.fetch_stock_data(resolved, interval=timeframe)
        if not df.empty:
            df = df.tail(bars).copy()
    else:
        # Fetch crypto candle data from Binance
        try:
            client = get_spot_client()
            crypto_ticker = resolved
            # Fallback mapping if standard quote is omitted
            if not (crypto_ticker.endswith("USDT") or crypto_ticker.endswith("BTC") or crypto_ticker.endswith("ETH")):
                crypto_ticker = f"{resolved}USDT"
                
            klines = fetch_klines(client, crypto_ticker, timeframe, bars)
            df = klines_to_dataframe(klines)
            if not df.empty and len(df) < bars and bars >= 50:
                raise ValueError(f"Binance only returned {len(df)} candles, which is less than requested {bars}")
        except Exception as e:
            # Global Cross-Venue Crypto Fallback to yfinance if Binance fails
            try:
                yf_crypto = resolved
                if not yf_crypto.endswith("-USD"):
                    for quote in ["USDT", "USDC", "USD"]:
                        if yf_crypto.endswith(quote):
                            yf_crypto = yf_crypto[:-len(quote)]
                            break
                    yf_crypto = f"{yf_crypto}-USD"
                
                print(f"[Data Loader] Crypto {resolved} failed on Binance. Falling back to Yahoo Finance: {yf_crypto}")
                df = discovery.fetch_stock_data(yf_crypto, interval=timeframe)
                if not df.empty:
                    df = df.tail(bars).copy()
            except Exception as yf_err:
                print(f"[Data Loader] Yahoo Finance fallback also failed for {resolved}: {yf_err}")
                
            if df.empty:
                print(f"[Data Loader] Failed to fetch crypto data for {symbol}: {e}")

    # Intercept and append stochastic black-swan jumps if stress testing is active
    if not df.empty and "--generate-stress-data" in sys.argv:
        try:
            import synthetic_generator
            df = synthetic_generator.generate_synthetic_data(df, num_bars=100)
            print(f"[Stress Test] Appended 100 high-stress Merton Jump-Diffusion bars successfully for {symbol}")
        except Exception as err:
            print(f"[Stress Test] Stochastic stress injection failed for {symbol}: {err}")

    return df

def _print_section(title: str, content: str = "", border_char: str = "=") -> None:
    border = f"{Colors.BOLD}{Colors.CYAN}{border_char * 85}{Colors.END}"
    print(f"\n{border}")
    print(f"{Colors.BOLD}{Colors.GREEN}{title.center(85)}{Colors.END}")
    print(border)
    if content:
        print(content)

def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "  No opportunities found matching these criteria."
    
    widths = [visible_len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], visible_len(str(cell)))
    
    def pad_cell(s: str, width: int) -> str:
        s_str = str(s)
        v_len = visible_len(s_str)
        padding = max(0, width - v_len)
        return s_str + (" " * padding)

    lines = [
        "  " + "  ".join(pad_cell(header, widths[idx]) for idx, header in enumerate(headers)),
        "  " + "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for row in rows:
        lines.append("  " + "  ".join(pad_cell(row[idx], widths[idx]) for idx in range(len(headers))))
    return "\n".join(lines)

def _format_value(value: float | None, precision: int = 4) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.{precision}f}"

def run_multi_market_discovery(symbols_arg: str) -> tuple[list[str], list[str]]:
    """Deduce or dynamically scan markets to populate the asset lists."""
    crypto_list = []
    stock_list = []
    
    parts = [s.strip().upper() for s in symbols_arg.split(",") if s.strip()]
    
    # 1. Check for discovery keywords
    if "DISCOVER_CRYPTO" in parts or not parts:
        print("[Scanner] Dynamically scanning active crypto markets by 24h volume...")
        crypto_list = discovery.get_top_crypto_by_volume(5)
    
    if "DISCOVER_STOCKS" in parts or not parts:
        print("[Scanner] Loading high-liquidity stock tickers...")
        stock_list = discovery.STOCK_WATCHLIST[:5]
        
    # 2. Add explicit items
    for p in parts:
        if p in {"DISCOVER_CRYPTO", "DISCOVER_STOCKS"}:
            continue
        if is_stock(p):
            if p not in stock_list:
                stock_list.append(p)
        else:
            if p not in crypto_list:
                crypto_list.append(p)
                
    # Fallback to watchlist config if both are completely empty
    if not crypto_list and not stock_list:
        for s in WATCHLIST:
            if is_stock(s):
                stock_list.append(s)
            else:
                crypto_list.append(s)
                
    return crypto_list, stock_list

def _analyze_single_symbol(symbol: str, timeframes: list[str], bars: int, args: argparse.Namespace) -> dict | None:
    """Execute standard & advanced multi-timeframe scans on a single symbol with ML + Sentiment + Kalman Filter + EWMA + Quant Regimes."""
    logger = structured_logger.get_logger("trading_bot.scanner")
    symbol_data: dict = {"signals": {}}
    current_price = None
    best_pick = None
    
    # Fetch real-time TradingView technical analyst rating once per symbol
    tv_rating = "NEUTRAL"
    tv_rsi = None
    try:
        import tradingview_client
        tv_data = tradingview_client.query_tradingview_scanner(symbol)
        if tv_data:
            tv_rating = tv_data.get("recommendation", "NEUTRAL")
            tv_rsi = tv_data.get("rsi")
            logger.info("TradingView scan completed", symbol=symbol, rating=tv_rating, rsi=tv_rsi)
    except Exception as e:
        logger.error("Failed to query TradingView scanner", symbol=symbol, error=str(e))
        
    for idx, timeframe in enumerate(timeframes):
        df = fetch_data_unified(symbol, timeframe, bars)
        if df.empty or len(df) < 30:
            continue
            
        last = df.iloc[-1]
        if current_price is None:
            current_price = float(last["close"])
            
        # 1. Fetch News Sentiment
        sent_score = 0.0
        sent_label = "NEUTRAL"
        if not getattr(args, "skip_sentiment", False):
            try:
                api_symbol = symbol
                if not is_stock(symbol):
                    for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                        if symbol.endswith(quote) and len(symbol) > len(quote):
                            api_symbol = symbol[:-len(quote)]
                            break
                sent_dict = sentiment_analyzer.get_sentiment(api_symbol, is_stock=is_stock(symbol))
                sent_score = sent_dict.get("score", 0.0)
                sent_label = sent_dict.get("sentiment_label", "NEUTRAL")
                metrics_server.update_sentiment(symbol, sent_score)
                logger.info("News sentiment fetched", symbol=symbol, score=sent_score, label=sent_label)
            except Exception as e:
                logger.error("Failed to fetch sentiment", symbol=symbol, error=str(e))
        
        # 2. Machine Learning Classifier & Continuous Learning Engine (Layer 3)
        ml_signal = "HOLD"
        ml_confidence = 0.0
        online_signal = "HOLD"
        online_confidence = 0.0
        rl_signal = "HOLD"
        shap_text = ""
        
        if not getattr(args, "skip_ml", False):
            try:
                engine = ml_engine.MLSignalEngine(symbol, timeframe)
                needs_train = getattr(args, "retrain_ml", False) or engine.is_model_stale() or not engine.load_model()
                if needs_train:
                    logger.info("Training ML models", symbol=symbol, timeframe=timeframe)
                    df_train = fetch_data_unified(symbol, timeframe, 500)
                    if not df_train.empty and len(df_train) >= 60:
                        metrics = engine.train(df_train)
                        if "error" not in metrics:
                            logger.info(
                                "ML Model trained successfully",
                                symbol=symbol,
                                timeframe=timeframe,
                                accuracy=metrics.get("accuracy"),
                                f1=metrics.get("f1")
                            )
                            engine.load_model()
                            
                            # Train Adaptive Online SGD Learner
                            try:
                                logger.info("Training Adaptive Online SGD Learner", symbol=symbol, timeframe=timeframe)
                                learner = online_learner.OnlineLearner(symbol, timeframe)
                                df_train_ind = add_indicators(df_train.copy(), atr_period=ATR_PERIOD)
                                df_train_feats = ml_engine.extract_features(df_train_ind)
                                df_train_feats["_label"] = ml_engine._create_labels(df_train_feats, lookforward=5, threshold_pct=1.5)
                                
                                clean_rows = df_train_feats[df_train_feats["_label"] != -99]
                                for _, row in clean_rows.iterrows():
                                    learner.update_online(row.to_dict(), row["_label"])
                                learner.save_model()
                                logger.info("Adaptive Online Learner trained successfully", symbol=symbol, count=learner.count)
                            except Exception as o_err:
                                logger.error("Adaptive Online Learner training failed", symbol=symbol, error=str(o_err))
                                
                            # Train DRL Agent Policy Environment
                            try:
                                logger.info("Training DRL Agent Policy Environment", symbol=symbol, timeframe=timeframe)
                                rl_agent = rl_trader.DeepQNetworkAgent(symbol, timeframe)
                                df_rl_ind = add_indicators(df_train.copy(), atr_period=ATR_PERIOD)
                                df_rl_feats = ml_engine.extract_features(df_rl_ind)
                                rl_agent.train_rl_policy(df_rl_feats, episodes=8)
                                logger.info("DRL Agent Policy trained successfully", symbol=symbol)
                            except Exception as rl_err:
                                logger.error("DRL Agent Policy training failed", symbol=symbol, error=str(rl_err))
                        else:
                            logger.error("ML Model training failed", symbol=symbol, error=metrics["error"])
                    else:
                        logger.warning("Insufficient data to train ML model", symbol=symbol, len=len(df_train))
                
                if engine.load_model():
                    ml_signal, ml_confidence = engine.predict(df)
                    metrics_server.update_ml_confidence(symbol, ml_confidence)
                    logger.info("ML prediction generated", symbol=symbol, signal=ml_signal, confidence=ml_confidence)
                    
                    # Predict using Adaptive Online Learner
                    try:
                        learner = online_learner.OnlineLearner(symbol, timeframe)
                        if learner.load_model():
                            df_pred_ind = add_indicators(df.copy(), atr_period=ATR_PERIOD)
                            df_pred_feats = ml_engine.extract_features(df_pred_ind)
                            last_feat = df_pred_feats.iloc[-1].to_dict()
                            online_signal, online_confidence = learner.predict_online(last_feat)
                            logger.info("Online Learner prediction generated", symbol=symbol, signal=online_signal, confidence=online_confidence)
                    except Exception as o_pred_err:
                        logger.error("Online Learner prediction failed", symbol=symbol, error=str(o_pred_err))
                        
                    # Evaluate Reinforcement Learning DQN Policy
                    try:
                        rl_agent = rl_trader.DeepQNetworkAgent(symbol, timeframe)
                        if rl_agent.load_model():
                            df_rl_ind = add_indicators(df.copy(), atr_period=ATR_PERIOD)
                            df_rl_feats = ml_engine.extract_features(df_rl_ind)
                            last_row = df_rl_feats.iloc[-1]
                            obs = np.array([
                                float(last_row.get("rsi14", 50.0)),
                                float(last_row.get("macd_hist", 0.0)),
                                float(last_row.get("volatility", 0.0)),
                                float(last_row.get("feat_garman_klass_vol", 0.0)),
                                float(last_row.get("feat_dist_ema20", 0.0)),
                                float(0.0)
                            ])
                            obs[0] = (obs[0] - 50.0) / 25.0
                            obs[1] = obs[1] * 10.0
                            obs[2] = obs[2] / 5.0
                            obs[3] = obs[3] * 50.0
                            
                            act = rl_agent.act(obs, explore=False)
                            rl_signal = {0: "HOLD", 1: "BUY", 2: "SELL"}[act]
                            logger.info("DRL Agent Policy prediction generated", symbol=symbol, signal=rl_signal)
                    except Exception as rl_pred_err:
                        logger.error("DRL Agent Policy prediction failed", symbol=symbol, error=str(rl_pred_err))
                    
                    if ml_signal != "HOLD":
                        explanations = model_explainer.explain_prediction(engine, df, top_n=3)
                        shap_text = model_explainer.format_explanation_text(explanations)
            except Exception as e:
                logger.error("Failed to evaluate ML engine", symbol=symbol, error=str(e))

        # 2b. LLM Trading Desk (TradingAgents multi-agent AI)
        llm_action = "HOLD"
        llm_confidence = 0.0
        llm_reasoning = ""
        llm_raw = {}
        if getattr(args, "llm_desk", False) and idx == 0:  # Run once per symbol, not per timeframe
            try:
                logger.info("Running LLM Trading Desk analysis", symbol=symbol)
                llm_raw = tradingagents_plugin.run_llm_desk(symbol, is_crypto=not is_stock(symbol))
                llm_action = llm_raw.get("action", "HOLD")
                llm_confidence = llm_raw.get("confidence", 0.0)
                llm_reasoning = llm_raw.get("reasoning", "")
                if llm_raw.get("error"):
                    logger.warning("LLM Desk returned error", symbol=symbol, error=llm_raw["error"])
                else:
                    logger.info(
                        "LLM Desk decision",
                        symbol=symbol,
                        action=llm_action,
                        confidence=llm_confidence,
                        elapsed=f"{llm_raw.get('elapsed_sec', 0):.1f}s"
                    )
            except Exception as e:
                logger.error("LLM Desk failed", symbol=symbol, error=str(e))

        # Load tuned parameters if they exist
        from genetic_tuner import load_tuned_parameters
        tuned = load_tuned_parameters(symbol)
        
        local_ema_fast = 12
        local_ema_slow = 26
        local_sl_mult = ATR_MULTIPLIER_SL
        local_tp_mult = ATR_MULTIPLIER_TP
        local_kf_q = 1e-4
        local_kf_r = 1e-2
        
        if tuned:
            local_ema_fast = tuned.get("ema_fast", 12)
            local_ema_slow = tuned.get("ema_slow", 26)
            local_sl_mult = tuned.get("atr_multiplier_sl", ATR_MULTIPLIER_SL)
            local_tp_mult = tuned.get("atr_multiplier_tp", ATR_MULTIPLIER_TP)
            local_kf_q = tuned.get("kalman_q", 1e-4)
            local_kf_r = tuned.get("kalman_r", 1e-2)
            logger.info("Auto-loaded tuned parameters", symbol=symbol, ema_fast=local_ema_fast, ema_slow=local_ema_slow, sl_mult=local_sl_mult, tp_mult=local_tp_mult, kf_q=local_kf_q, kf_r=local_kf_r)
            
        # Load self-evolved parameters if they exist to overlay tuning
        try:
            from evolution_engine import load_evolved_parameters
            evolved = load_evolved_parameters(symbol)
        except Exception:
            evolved = None
            
        evolved_weights = None
        evolved_threshold = None
        if evolved:
            evolved_weights = evolved.get("strategy_weights")
            evolved_threshold = evolved.get("consensus_threshold")
            local_sl_mult = evolved.get("atr_multiplier_sl", local_sl_mult)
            local_tp_mult = evolved.get("atr_multiplier_tp", local_tp_mult)
            logger.info("Auto-loaded self-evolved parameters", symbol=symbol, sl_mult=local_sl_mult, tp_mult=local_tp_mult, threshold=evolved_threshold)

        # 3. Add indicators & Evaluate 7-indicator signals
        df = add_indicators(df, atr_period=ATR_PERIOD, ema_fast_span=local_ema_fast, ema_slow_span=local_ema_slow)
        
        # Ensure statistical features are extracted for Hurst exponent and regimes
        from feature_engineering import extract_features
        df = extract_features(df)
        
        summary = evaluate_latest_signals(
            df, 
            local_sl_mult, 
            local_tp_mult, 
            ml_signal=ml_signal, 
            ml_confidence=ml_confidence, 
            tv_rating=tv_rating,
            strategy_weights=evolved_weights,
            consensus_threshold=evolved_threshold
        )
        
        # Incorporate advanced skills indicators
        adv = analyze_advanced(df)
        
        # 4. Kalman Filter, EWMA Volatility, & Quant regime estimation
        import quant_engine
        
        kf = quant_engine.KalmanFilter1D(Q_ratio=local_kf_q, R_ratio=local_kf_r)
        kf_filtered, kf_residuals, kf_zscores = kf.run_filter(df["close"].values)
        kf_zscore = float(kf_zscores[-1])
        
        returns = df["close"].pct_change()
        ewma_vols = quant_engine.compute_ewma_volatility(returns, decay=0.94)
        ewma_vol = float(ewma_vols.iloc[-1])
        
        hurst_exp = float(df["feat_hurst"].iloc[-1]) if "feat_hurst" in df.columns else 0.5
        q_regime = quant_engine.classify_quant_regime(df, kf_zscore, hurst_exp, ewma_vol)
        
        # Update thread-safe global ML_CONFIDENCES
        global ML_CONFIDENCES
        ML_CONFIDENCES[symbol] = ml_confidence
        
        # Prometheus telemetry updates
        metrics_server.update_kalman_z(symbol, kf_zscore)
        metrics_server.update_ewma_vol(symbol, ewma_vol)
        
        # Count votes
        long_votes = 0.0
        short_votes = 0.0
        for k, v in summary.per_strategy.items():
            if v == "LONG":
                if k == "ML_SIGNAL" and ml_confidence > 0.80:
                    long_votes += 1.5
                else:
                    long_votes += 1.0
            elif v == "SHORT":
                if k == "ML_SIGNAL" and ml_confidence > 0.80:
                    short_votes += 1.5
                else:
                    short_votes += 1.0
        
        vote_count = max(long_votes, short_votes)
        has_ml = "ML_SIGNAL" in summary.per_strategy
        has_tv = "TV_RATING" in summary.per_strategy
        total_indicators = 6
        if has_ml:
            total_indicators += 1
        if has_tv:
            total_indicators += 1
        strength = (long_votes - short_votes) / total_indicators
        
        if summary.direction == "LONG":
            action = "BUY"
        elif summary.direction == "SHORT":
            action = "SELL"
        else:
            action = "WAIT"
            
        if action in {"BUY", "SELL"}:
            metrics_server.record_signal(action)
            
        symbol_data["signals"][timeframe] = {
            "signal": summary.direction,
            "score": summary.score,
            "action": action,
            "strength": strength,
            "stop": summary.stop,
            "take": summary.take,
            "regime": adv.get("regime", "n/a"),
            "vwap": adv.get("vwap"),
            "supertrend": adv.get("supertrend", 0),
            "ichi_bull": adv.get("ichi_bull", False),
            "ml_signal": ml_signal,
            "ml_confidence": ml_confidence,
            "online_signal": online_signal,
            "online_confidence": online_confidence,
            "rl_signal": rl_signal,
            "shap_explanation": shap_text,
            "sentiment_score": sent_score,
            "sentiment_label": sent_label,
            # Quant values
            "kf_zscore": kf_zscore,
            "ewma_vol": ewma_vol,
            "q_regime": q_regime,
            "hurst": hurst_exp,
            # LLM Desk
            "llm_action": llm_action,
            "llm_confidence": llm_confidence,
            "llm_reasoning": llm_reasoning,
            "llm_raw": llm_raw,
            # TradingView
            "tv_rating": tv_rating,
            "tv_rsi": tv_rsi,
            "per_strategy": summary.per_strategy,
        }
        
        candidate = {
            "idx": idx,
            "timeframe": timeframe,
            "action": action,
            "strength": strength,
            "vote_count": vote_count,
            "score": summary.score,
            "entry": float(last["close"]),
            "stop": summary.stop,
            "take": summary.take,
            "regime": adv.get("regime", "n/a"),
            "vwap": adv.get("vwap"),
            "supertrend": adv.get("supertrend", 0),
            "ichi_bull": adv.get("ichi_bull", False),
            "ml_signal": ml_signal,
            "ml_confidence": ml_confidence,
            "online_signal": online_signal,
            "online_confidence": online_confidence,
            "rl_signal": rl_signal,
            "shap_explanation": shap_text,
            "sentiment_score": sent_score,
            "sentiment_label": sent_label,
            # Quant values
            "kf_zscore": kf_zscore,
            "ewma_vol": ewma_vol,
            "q_regime": q_regime,
            "hurst": hurst_exp,
            # LLM Desk
            "llm_action": llm_action,
            "llm_confidence": llm_confidence,
            "llm_reasoning": llm_reasoning,
            "llm_raw": llm_raw,
            # TradingView
            "tv_rating": tv_rating,
            "tv_rsi": tv_rsi,
            "per_strategy": summary.per_strategy,
        }
        
        if best_pick is None or abs(strength) > abs(best_pick["strength"]):
            best_pick = candidate
            
    if symbol_data["signals"] and best_pick:
        symbol_data["current_price"] = current_price
        symbol_data["action"] = best_pick["action"]
        symbol_data["signal_score"] = best_pick["score"]
        symbol_data["signal_timeframe"] = best_pick["timeframe"]
        symbol_data["stop"] = best_pick["stop"]
        symbol_data["take"] = best_pick["take"]
        symbol_data["per_strategy"] = best_pick.get("per_strategy", {})
        symbol_data["entry"] = best_pick["entry"]
        symbol_data["regime"] = best_pick["regime"]
        symbol_data["vwap"] = best_pick["vwap"]
        symbol_data["supertrend"] = best_pick["supertrend"]
        symbol_data["ichi_bull"] = best_pick["ichi_bull"]
        symbol_data["ml_signal"] = best_pick.get("ml_signal")
        symbol_data["ml_confidence"] = best_pick.get("ml_confidence")
        symbol_data["online_signal"] = best_pick.get("online_signal")
        symbol_data["online_confidence"] = best_pick.get("online_confidence")
        symbol_data["rl_signal"] = best_pick.get("rl_signal")
        symbol_data["shap_explanation"] = best_pick.get("shap_explanation")
        symbol_data["sentiment_score"] = best_pick.get("sentiment_score")
        symbol_data["sentiment_label"] = best_pick.get("sentiment_label")
        # Quant values
        symbol_data["kf_zscore"] = best_pick.get("kf_zscore")
        symbol_data["ewma_vol"] = best_pick.get("ewma_vol")
        symbol_data["q_regime"] = best_pick.get("q_regime")
        symbol_data["hurst"] = best_pick.get("hurst")
        # LLM Desk
        symbol_data["llm_action"] = best_pick.get("llm_action", "HOLD")
        symbol_data["llm_confidence"] = best_pick.get("llm_confidence", 0.0)
        symbol_data["llm_reasoning"] = best_pick.get("llm_reasoning", "")
        symbol_data["llm_raw"] = best_pick.get("llm_raw", {})
        # TradingView
        symbol_data["tv_rating"] = best_pick.get("tv_rating", "NEUTRAL")
        symbol_data["tv_rsi"] = best_pick.get("tv_rsi")
        return symbol_data

        
    return None

def analyze_opportunity_list(symbols: list[str], timeframes: list[str], bars: int, args: argparse.Namespace) -> dict[str, dict]:
    """Execute standard & advanced multi-timeframe scans on a list of symbols with ML + Sentiment (with multi-threaded concurrency support)."""
    results: dict[str, dict] = {}
    logger = structured_logger.get_logger("trading_bot.scanner")
    
    use_parallel = getattr(args, "parallel", True)
    
    if use_parallel and len(symbols) > 1:
        from concurrent.futures import ThreadPoolExecutor
        logger.info("Executing concurrent multi-threaded scans", count=len(symbols))
        with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as executor:
            futures = {
                executor.submit(_analyze_single_symbol, symbol, timeframes, bars, args): symbol
                for symbol in symbols
            }
            for future in futures:
                symbol = futures[future]
                try:
                    res = future.result()
                    if res:
                        results[symbol] = res
                except Exception as e:
                    logger.error("Concurrent scan error on symbol", symbol=symbol, error=str(e))
    else:
        logger.info("Executing sequential scans", count=len(symbols))
        for symbol in symbols:
            try:
                res = _analyze_single_symbol(symbol, timeframes, bars, args)
                if res:
                    results[symbol] = res
            except Exception as e:
                logger.error("Sequential scan error on symbol", symbol=symbol, error=str(e))
                
    return results

def _run_deep_dive(symbol: str, args: argparse.Namespace) -> None:
    """Execute a highly investigative, multi-layered quantitative deep-dive on a targeted symbol."""
    symbol = symbol.strip().upper()
    logger = structured_logger.get_logger("trading_bot.deep_dive")
    
    print(f"\n================================================================================")
    print(f"               INVESTIGATIVE QUANTITATIVE DEEP DIVE REPORT CARD                 ")
    print(f"                                   {symbol}                                     ")
    print(f"================================================================================\n")
    
    # 1. Real-time Genetic Algorithm Calibration
    print("[1/5] Initiating real-time Genetic Parameter calibration...")
    try:
        from genetic_tuner import GeneticTuner, save_tuned_parameters
        # Run a fast 3-generation GA calibration sweep on 15m candles
        tuner = GeneticTuner(symbol, timeframe="15m", pop_size=15, generations=3)
        tuned = tuner.tune()
        if tuned:
            save_tuned_parameters(tuned)
            print("  -> Dynamic parameters tuned successfully. Saved DNA parameters.")
        else:
            print("  -> Dynamic parameters calibration completed with fallback defaults.")
    except Exception as e:
        print(f"  -> Calibration exception (skipping): {e}")
        
    # 2. Multi-Timeframe Regime Analysis
    print("\n[2/5] Performing multi-timeframe regime analysis...")
    timeframes = ["15m", "1h", "4h", "1d"]
    regimes = {}
    prices = {}
    for tf in timeframes:
        df = fetch_data_unified(symbol, tf, 200)
        if not df.empty and len(df) >= 30:
            from genetic_tuner import load_tuned_parameters
            tuned = load_tuned_parameters(symbol)
            kf_q = tuned.get("kalman_q", 1e-4) if tuned else 1e-4
            kf_r = tuned.get("kalman_r", 1e-2) if tuned else 1e-2
            
            import quant_engine
            kf = quant_engine.KalmanFilter1D(Q_ratio=kf_q, R_ratio=kf_r)
            kf_filtered, kf_residuals, kf_zscores = kf.run_filter(df["close"].values)
            kf_z = float(kf_zscores[-1])
            
            # Hurst and EWMA Volatility
            df = add_indicators(df, atr_period=ATR_PERIOD)
            from feature_engineering import extract_features
            df = extract_features(df)
            
            returns = df["close"].pct_change()
            ewma_vols = quant_engine.compute_ewma_volatility(returns, decay=0.94)
            ewma_vol = float(ewma_vols.iloc[-1])
            
            hurst_exp = float(df["feat_hurst"].iloc[-1]) if "feat_hurst" in df.columns else 0.5
            q_reg = quant_engine.classify_quant_regime(df, kf_z, hurst_exp, ewma_vol)
            
            regimes[tf] = q_reg
            prices[tf] = float(df["close"].iloc[-1])
            print(f"  * Timeframe {tf:<4} | Price: {prices[tf]:<12} | Market Regime: {q_reg:<18} | KF Z: {kf_z:+.2f}")
            
    # 3. Machine Learning Ensemble Signals & SHAP Explainer
    print("\n[3/5] Evaluating deep machine learning ensemble & SHAP explanations...")
    try:
        import ml_engine
        engine = ml_engine.MLSignalEngine(symbol, "1h")
        if engine.load_model():
            df_ml = fetch_data_unified(symbol, "1h", 200)
            if not df_ml.empty:
                ml_signal, ml_confidence = engine.predict(df_ml)
                print(f"  * Ensemble Prediction (1h): {ml_signal} (Confidence: {ml_confidence:.1%})")
                
                # SHAP
                try:
                    import model_explainer
                    explanations = model_explainer.explain_prediction(engine, df_ml, top_n=3)
                    shap_text = model_explainer.format_explanation_text(explanations)
                    if shap_text:
                        print("  * Top Drivers (SHAP values):")
                        for exp in explanations:
                            print(f"    - {exp['feature']:<20}: {exp['shap_value']:+.4f} ({exp.get('description', 'No desc')})")
                except Exception as e:
                    print(f"    - SHAP analysis skipped: {e}")
        else:
            print("  -> Pre-trained ML Signal models not found. Run standard scan first to calibrate.")
    except Exception as e:
        print(f"  -> Machine Learning engine failed: {e}")
        
    # 4. Exchange Depth & Smart Routing Liquidity Assessment
    print("\n[4/5] Running cross-exchange spread & liquidity assessment...")
    try:
        from exchange_router import ExchangeRouter
        router = ExchangeRouter()
        best_venue = router.get_best_execution_venue(symbol, "BUY", 100.0)
        if best_venue:
            print(f"  * Primary Venue:       {best_venue.upper()}")
            tickers = router.get_ticker_both(symbol)
            venue_t = tickers.get(best_venue)
            if venue_t:
                spread = (venue_t["ask"] - venue_t["bid"]) / venue_t["bid"] if venue_t["bid"] > 0 else 0.0
                print(f"  * Bid-Ask Spread:      {spread:.4%}")
                print(f"  * Best Bid Price:      ${venue_t['bid']:.4f}")
                print(f"  * Best Ask Price:      ${venue_t['ask']:.4f}")
    except Exception as e:
        print(f"  -> Liquidity scan skipped (requires exchange connectivity keys): {e}")
        
    # 5. TradingView Analyst rating and RSI
    print("\n[5/5] Checking TradingView Technical Analyst consensus...")
    try:
        import tradingview_client
        tv_data = tradingview_client.query_tradingview_scanner(symbol)
        if tv_data:
            rating = tv_data.get("recommendation", "NEUTRAL")
            rsi = tv_data.get("rsi")
            rsi_str = f"{rsi:.1f}" if rsi is not None else "n/a"
            print(f"  * TradingView Consensus:  {rating}")
            print(f"  * Technical RSI (14):     {rsi_str}")
        else:
            print("  * Technical Consensus:    NEUTRAL (no feed)")
    except Exception as e:
        print(f"  -> TradingView client failed: {e}")
        
    print(f"\n================================================================================")
    print(f"                       DEEP DIVE REPORT COMPLETED SUCCESSFULLY                  ")
    print(f"================================================================================\n")
    
    print_available_commands()

def print_available_commands() -> None:
    """Print a monochrome ASCII CLI Cheat Sheet containing all key bot commands for easy copy-pasting."""
    print("=====================================================================================")
    print("                       MULTI-MARKET QUANT BOT CLI COMMAND REFERENCE                  ")
    print("=====================================================================================")
    print("  [CRYPTO SCANS]    Scan, optimize, and size digital currencies:")
    print("      python unified_analyzer.py --crypto BTCUSDT,ETHUSDT,SOLUSDT --skip-backtest")
    print("")
    print("  [STOCK SCANS]     Scan traditional equities with Yahoo Finance News integration:")
    print("      python unified_analyzer.py --stocks AAPL,TSLA,MSFT --skip-backtest")
    print("")
    print("  [FOREX SCANS]     Scan spot currency pairs with zero-volume fallback models:")
    print("      python unified_analyzer.py --forex GBPUSD,EURUSD --skip-backtest")
    print("")
    print("  [DEEP DIVE]       Run multi-layered Genetic parameters, SHAP, and Order Book calibration:")
    print("      python unified_analyzer.py --deep-dive BTCUSDT")
    print("      python unified_analyzer.py --deep-dive AAPL")
    print("")
    print("  [STRESS-TEST]     Inject black-swan Merton Jump-Diffusion crashes for tail-risk analysis:")
    print("      python unified_analyzer.py --crypto BTCUSDT --generate-stress-data --skip-backtest")
    print("")
    print("  [EVENT-BACKTEST]  Run backtests using high-fidelity hourly Event-driven queue loop:")
    print("      python unified_analyzer.py --crypto BTCUSDT --event-backtest")
    print("")
    print("  [WALK-FORWARD]    Optimize EMA Fast/Slow params via Out-of-Sample sliding validation:")
    print("      python unified_analyzer.py --crypto BTCUSDT --run-wfo")
    print("")
    print("  [ML RETRAINING]   Retrain XGBoost, LightGBM, and Deep RL models from scratch:")
    print("      python unified_analyzer.py --crypto BTCUSDT --retrain-ml --skip-backtest")
    print("")
    print("  [OBSERVABILITY]   Run scan with real-time Prometheus exporter active on port 9090:")
    print("      python unified_analyzer.py --crypto BTCUSDT --metrics")
    print("")
    print("  [SELF-EVOLUTION]  Evolve strategy weights, consensus, and risk multipliers from trade journal:")
    print("      python unified_analyzer.py --evolve")
    print("=====================================================================================\n")

def _print_opportunities_dashboard(crypto_results: dict[str, dict], stock_results: dict[str, dict]) -> None:
    """Print multi-market scans in a classic, spacious terminal dashboard card layout to prevent wrapping congestion."""
    
    def print_cards(results: dict[str, dict], title: str):
        print(f"\n=================== {title.upper()} ===================")
        if not results:
            print("  No opportunities found matching these criteria.\n")
            return
            
        for symbol, data in results.items():
            act = data.get('action', 'HOLD')
            tf = data.get('signal_timeframe', 'n/a')
            score = data.get('signal_score', '0/8')
            
            p_val = data.get('current_price')
            if p_val is not None:
                price = f"{p_val:.2f}" if is_stock(symbol) else f"{p_val:.4f}"
            else:
                price = "n/a"
                
            q_reg = data.get('q_regime', 'n/a')
            kf_z = data.get('kf_zscore')
            kf_z_str = f"{kf_z:+.2f}" if kf_z is not None else "n/a"
            
            ml_sig = data.get('ml_signal', 'HOLD')
            ml_conf = f"{data.get('ml_confidence', 0.0):.1%}" if data.get('ml_confidence') else "n/a"
            
            sent_val = data.get('sentiment_score')
            sent_lbl = data.get('sentiment_label', 'NEUTRAL')
            sent_str = f"{sent_val:+.2f} ({sent_lbl})" if sent_val is not None else "n/a"
            
            llm_act = data.get('llm_action', '-')
            llm_conf = f"{data.get('llm_confidence', 0.0):.0%}" if data.get('llm_confidence') else "-"
            llm_str = f"{llm_act} ({llm_conf})" if llm_act != '-' else "-"
            
            tv_rating = data.get('tv_rating', 'NEUTRAL')
            tv_rsi = f"{data.get('tv_rsi'):.1f}" if data.get('tv_rsi') is not None else "n/a"
            tv_str = f"{tv_rating} (RSI: {tv_rsi})"
            
            online_sig = data.get('online_signal', 'HOLD')
            online_conf = f"{data.get('online_confidence', 0.0):.1%}" if data.get('online_confidence') else "n/a"
            online_str = f"{online_sig} ({online_conf})"
            
            rl_sig = data.get('rl_signal', 'HOLD')
            
            header_len = len(symbol)
            dash_count = max(1, 74 - header_len)
            print(f"+- {symbol} " + ("-" * dash_count) + "+")
            print(f"|  [Execution]   Timeframe: {tf:<6} Price: {price:<12} Consensus: {score:<6} |")
            print(f"|  [Core Signal] Action:    {act:<55} |")
            print(f"+-------------------------------------------------------------------------------+")
            print(f"|  * Regime Model:     {q_reg:<22} * Trend Deviation:  {kf_z_str:<18} |")
            print(f"|  * ML Classifier:    {ml_sig:<13} ({ml_conf:<5}) * AI Telegram PM:   {llm_str:<18} |")
            print(f"|  * Online Learner:   {online_str:<22} * RL DQN Policy:    {rl_sig:<18} |")
            print(f"|  * News Sentiment:   {sent_str:<22} * TV Analyst Rating: {tv_str:<18} |")
            print(f"+-------------------------------------------------------------------------------+\n")

    print_cards(crypto_results, "Cryptocurrency Opportunities")
    
    # Print LLM Desk reasoning for crypto if any
    for s, data in crypto_results.items():
        if data.get("llm_raw"):
            print(tradingagents_plugin.format_llm_desk_output(data["llm_raw"], s))
            
    print_cards(stock_results, "Stock Market Opportunities")
    
    # Print LLM Desk reasoning for stocks if any
    for s, data in stock_results.items():
        if data.get("llm_raw"):
            print(tradingagents_plugin.format_llm_desk_output(data["llm_raw"], s))

def print_market_analysis(crypto_list: list[str], stock_list: list[str], args: argparse.Namespace) -> dict:
    """Fetch opportunities and print distinct classic dashboards for stocks and crypto with ANSI terminal styling."""
    _print_section("REAL-TIME MULTI-MARKET OPPORTUNITY SCAN")
    
    timeframes = TRACKER_TIMEFRAMES
    bars = TRACKER_BARS
    
    crypto_results = analyze_opportunity_list(crypto_list, timeframes, bars, args)
    stock_results = analyze_opportunity_list(stock_list, timeframes, bars, args)
    
    _print_opportunities_dashboard(crypto_results, stock_results)
    
    # Merge both results
    merged = {**crypto_results, **stock_results}
    return merged

def print_wfo_results(crypto_list: list[str], stock_list: list[str]) -> None:
    """Run Walk-Forward Optimization sliding window calibrations on all discovered assets."""
    _print_section("WALK-FORWARD SLIDING WINDOW OPTIMIZATION (WFO)")
    
    wfo_results = []
    import wfo_engine
    
    all_symbols = crypto_list + stock_list
    for symbol in all_symbols:
        try:
            # Fetch historical candles
            df = fetch_data_unified(symbol, "1d", 252)
            if df.empty or len(df) < 50:
                continue
                
            res = wfo_engine.run_wfo_optimization(df, in_sample_pct=0.70, fee_rate=BACKTEST_FEE_RATE)
            if res.get("status") == "success":
                wfo_results.append([
                    symbol,
                    f"EMA {res['best_ema_fast']}/{res['best_ema_slow']}",
                    f"{res['in_sample_pnl_pct']:.1%}",
                    f"{res['out_of_sample_pnl_pct']:.1%}",
                    f"{res['out_of_sample_sharpe']:.2f}",
                    f"{res['overfitting_ratio']:.2f}"
                ])
        except Exception as err:
            print(f"  -> WFO calibration failed for {symbol}: {err}")
            
    if wfo_results:
        print("\n" + _format_table(
            ["Symbol", "Best DNA Params", "IS PnL", "OOS PnL", "OOS Sharpe", "OOS/IS Ratio"],
            wfo_results
        ))
    else:
        print("  No WFO optimizations successfully completed.")

def print_backtest_results(crypto_list: list[str], stock_list: list[str]) -> None:
    """Run historical backtests on all discovered assets to verify profit-factors."""
    if "--run-wfo" in sys.argv:
        print_wfo_results(crypto_list, stock_list)
        return
        
    if "--event-backtest" in sys.argv:
        _print_section("EVENT-DRIVEN HIGH-FIDELITY BACKTEST (Queue-Based Fill Simulation)")
        event_results = []
        import event_engine
        
        all_symbols = crypto_list + stock_list
        for symbol in all_symbols:
            try:
                # Use hourly candles for granular event processing
                df = fetch_data_unified(symbol, "1h", 252)
                if df.empty or len(df) < 50:
                    continue
                    
                df = add_indicators(df, atr_period=ATR_PERIOD)
                
                # Hook event strategy evaluation
                def event_strategy_eval(history_df: pd.DataFrame) -> Tuple[str, float]:
                    hist = add_indicators(history_df, atr_period=ATR_PERIOD)
                    sig_summary = evaluate_latest_signals(hist, atr_mult_sl=2.0, atr_mult_tp=3.0)
                    action = "BUY" if sig_summary.direction == "LONG" else "SELL" if sig_summary.direction == "SHORT" else "HOLD"
                    return action, 1.0
                    
                engine = event_engine.EventEngine(fee_rate=BACKTEST_FEE_RATE, slippage=0.0005)
                res = engine.run_backtest({symbol: df}, event_strategy_eval, timeframe="1h")
                
                if res.get("status") == "success":
                    event_results.append([
                        symbol,
                        "EVENT_CONSENSUS",
                        str(res["trades_count"]),
                        f"${res['total_pnl_usd']:.2f}",
                        f"{res['win_rate']:.1%}",
                        f"{res['max_drawdown']:.1%}"
                    ])
            except Exception as err:
                print(f"  -> Event-driven execution failed for {symbol}: {err}")
                
        if event_results:
            print("\n" + _format_table(
                ["Symbol", "Engine", "Trades", "PnL", "Win Rate", "Max DD"],
                event_results
            ))
        else:
            print("  No event-driven backtests successfully executed.")
        return

    _print_section("BACKTEST ANALYSIS (Historical Performance Verification)")
    
    all_results = []
    from backtest import _run_backtest as run_backtest, STRATEGY_MAP
    
    all_symbols = crypto_list + stock_list
    for symbol in all_symbols:
        try:
            # Load daily historical data (252 bars = 1 year of daily charts)
            df = fetch_data_unified(symbol, "1d", 252)
            if df.empty or len(df) < 50:
                continue
                
            df = add_indicators(df, atr_period=ATR_PERIOD)
            df = add_strategy_signals(df)
            
            for strategy_name, signal_col in STRATEGY_MAP.items():
                result = run_backtest(
                    df=df,
                    signal_col=signal_col,
                    fee_rate=BACKTEST_FEE_RATE,
                    position_size=DEFAULT_QUOTE_AMOUNT,
                )
                
                all_results.append([
                    symbol,
                    strategy_name.upper(),
                    str(result.trade_count),
                    _format_value(result.total_pnl, 2),
                    f"{result.win_rate:.1f}%",
                    _format_value(result.profit_factor, 2),
                    f"{result.max_drawdown_pct:.1f}%",
                ])
        except Exception:
            continue
            
    if all_results:
        print("\n" + _format_table(
            ["Symbol", "Strategy", "Trades", "PnL", "Win Rate", "Profit Factor", "Max DD"],
            all_results
        ))
    else:
        print("  No backtest histories found.")

def print_portfolio_analysis() -> None:
    """Summarize portfolio status and recent trade execution history."""
    _print_section("PORTFOLIO STATUS & RECENT JOURNAL LOGS")
    
    try:
        summary = get_portfolio_summary()
        summary_rows = [
            ["Total Registered Trades", str(summary.get("total_trades", 0))],
            ["Winning Executions", str(summary.get("wins", 0))],
            ["Losing Executions", str(summary.get("losses", 0))],
            ["Realized Win Rate", f"{summary.get('win_rate', 0.0):.1f}%"],
            ["Accrued Total PnL", f"${summary.get('net_pnl', 0.0):.2f}"],
            ["Average Winner Size", f"${summary.get('avg_win', 0.0):.2f}"],
            ["Average Loser Size", f"${summary.get('avg_loss', 0.0):.2f}"],
        ]
        
        # Calculate profit factor dynamically
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        avg_win = summary.get("avg_win", 0.0)
        avg_loss = summary.get("avg_loss", 0.0)
        profit_factor = (wins * avg_win) / (losses * avg_loss) if (losses * avg_loss) > 0 else 0.0
        summary_rows.append(["Profit Factor", _format_value(profit_factor, 2)])
        
        print("\nPaper Account Performance metrics:")
        print(_format_table(["Metric", "Value"], summary_rows))
        
        # Show open positions dynamically if any exist
        open_positions = summary.get("open_positions", [])
        if open_positions:
            print("\nOpen Positions:")
            pos_rows = []
            for p in open_positions:
                pos_rows.append([
                    p["symbol"],
                    _format_value(p["qty"], 4),
                    _format_value(p["entry_price"], 4),
                    _format_value(p["current_price"], 4) if p.get("current_price") else "n/a",
                    _format_value(p["unrealized_pnl"], 2) if p.get("unrealized_pnl") is not None else "n/a",
                ])
            print(_format_table(
                ["Symbol", "Qty", "Avg Cost", "Mark Price", "Unrealized PnL"],
                pos_rows
            ))
            
        recent = list_recent_trades(limit=5)
        if recent:
            print("\nRecent Journal Logged Entries:")
            trade_rows = []
            for t in recent:
                trade_rows.append([
                    t["timestamp"][:19] if t["timestamp"] else "-",
                    t["symbol"],
                    t["side"],
                    _format_value(t["qty"], 4),
                    _format_value(t["price"], 4),
                    _format_value(t["fee"], 2),
                    t.get("strategy") or "-",
                ])
            print(_format_table(
                ["Timestamp", "Asset", "Side", "Qty", "Price", "Fee", "Strategy"],
                trade_rows
            ))
    except Exception as e:
        import traceback
        print(f"Failed to fetch portfolio tracker summary: {e}")
        traceback.print_exc()

def print_framework_statuses() -> None:
    """Display statuses of configured elite external tools & plugins."""
    _print_section("ELITE EXTERNAL PLUGINS & INTEGRATION STATUS")
    
    statuses = get_framework_statuses()
    rows = []
    
    for s in statuses:
        state = "READY" if (s["path_exists"] and s["entry_exists"]) else "MISSING"
        rows.append([s["name"], state, s["entrypoint"] or "-"])
        
    print(_format_table(["Framework Integration", "Status", "Entrypoint"], rows))

def run_active_plugins(args: argparse.Namespace) -> None:
    """Automatically execute all ready external plugins/frameworks."""
    _print_section("AUTOMATED PLUGIN ORCHESTRATION ENGINE")
    import os
    active_targets = []
    if getattr(args, "crypto", ""):
        active_targets.extend(args.crypto.split(","))
    if getattr(args, "stocks", ""):
        active_targets.extend(args.stocks.split(","))
    if getattr(args, "forex", ""):
        active_targets.extend(args.forex.split(","))
    active_targets = [s.strip().upper() for s in active_targets if s.strip()]
    if active_targets:
        os.environ["BOT_TARGET_SYMBOLS"] = ",".join(active_targets)
    from external_frameworks import run_framework
    statuses = get_framework_statuses()
    
    # Check if a specific plugin was requested, or run all ready ones
    target_plugin = getattr(args, "plugin", "").strip().lower()
    
    extra_args = []
    if getattr(args, "plugin_args", ""):
        extra_args = args.plugin_args.split()
        
    run_count = 0
    for s in statuses:
        # If a specific plugin is requested, only run that one
        if target_plugin and s["key"] != target_plugin:
            continue
            
        if s["path_exists"] and s["entry_exists"]:
            print(f"\n>>> [Plugin Engine] Launching integration script: {s['name']} ({s['key']})...")
            try:
                run_framework(s["key"], extra_args)
                print(f"[SUCCESS] [Plugin Engine] {s['name']} executed successfully.")
                run_count += 1
            except Exception as e:
                print(f"[ERROR] [Plugin Engine] Execution failed for {s['name']}: {e}")
        elif target_plugin:
            print(f"[ERROR] [Plugin Engine] Cannot run plugin {s['name']} ({s['key']}) because it is not READY (missing folder or entrypoint).")
            
    if run_count == 0:
        if target_plugin:
            print(f"[INFO] Target plugin '{target_plugin}' was not found or is not ready.")
        else:
            print("[INFO] No active/ready plugins found to execute. Configure paths in .env or run setup scripts.")

def is_drawdown_limit_exceeded() -> tuple[bool, float, float]:
    """
    Check if the current paper account equity is below the 20% drawdown limit ($8,000).
    Returns: (is_exceeded, current_equity, limit)
    """
    starting_balance = 10000.0
    limit = starting_balance * 0.80  # 20% max drawdown limit = $8,000
    try:
        portfolio = get_portfolio_summary()
        net_pnl = float(portfolio.get("net_pnl", 0.0) or 0.0)
        open_positions = portfolio.get("open_positions", [])
        unrealized_pnl = sum(float(p.get("unrealized_pnl", 0.0) or 0.0) for p in open_positions)
        equity = starting_balance + net_pnl + unrealized_pnl
    except Exception:
        equity = starting_balance
    return (equity < limit), equity, limit

def compute_dynamic_position_size(symbol: str, entry: float, stop: float | None) -> tuple[float, float, float]:
    """
    Calculate dynamic position sizing based on HRP weights if enabled,
    or falling back to risking 1% of current paper trading portfolio equity.
    """
    starting_balance = 10000.0
    try:
        portfolio = get_portfolio_summary()
        net_pnl = float(portfolio.get("net_pnl", 0.0) or 0.0)
        open_positions = portfolio.get("open_positions", [])
        unrealized_pnl = sum(float(p.get("unrealized_pnl", 0.0) or 0.0) for p in open_positions)
        equity = starting_balance + net_pnl + unrealized_pnl
    except Exception:
        equity = starting_balance

    # Try HRP weight first if enabled
    weight = HRP_WEIGHTS.get(symbol, 0.0)
    ml_conf = ML_CONFIDENCES.get(symbol, 0.5)
    
    import quant_engine
    kelly_scale = quant_engine.calculate_kelly_fraction(ml_conf, fraction=0.2)
    # Scale factor: kelly_scale relative to standard max fraction (0.2)
    # Range of kelly_factor: [0.0, 1.0]
    kelly_factor = kelly_scale / 0.2
    
    if weight > 0:
        # Sizing target notional as weight * total equity, scaled by Kelly Criterion
        quote_amount = weight * equity * kelly_factor
        print(f"[Risk Manager] Sizing {symbol} via HRP scaled by Kelly (conf={ml_conf:.1%}, multiplier={kelly_factor:.2%}): target weight={weight:.2%}, scaled weight={weight*kelly_factor:.2%}, notional=${quote_amount:.2f}")
    else:
        # Fixed risk per trade (1% of total equity) fallback, scaled by Kelly Criterion
        risk_usd = equity * 0.01 * kelly_factor
        qty = 0.0
        if stop is not None and not pd.isna(stop):
            sl_distance = abs(entry - stop)
            if sl_distance > 0:
                qty = risk_usd / sl_distance
                
        # Cap/fallback to standard/max limits
        max_alloc = min(equity * 0.10, 1000.0) * kelly_factor
        if qty <= 0 or (qty * entry) > max_alloc:
            qty = max_alloc / entry if entry > 0 else 0.0
        quote_amount = qty * entry
        print(f"[Risk Manager] Sizing {symbol} via 1% fixed-risk scaled by Kelly (conf={ml_conf:.1%}, multiplier={kelly_factor:.2%}): notional=${quote_amount:.2f}")
        
    # Load evolved position size multiplier if available
    try:
        from evolution_engine import load_evolved_parameters
        evolved = load_evolved_parameters(symbol)
        pos_size_mult = evolved.get("position_size_multiplier", 1.0) if evolved else 1.0
    except Exception:
        pos_size_mult = 1.0
        
    if pos_size_mult != 1.0:
        quote_amount *= pos_size_mult
        print(f"[Risk Manager] Applied evolved position size multiplier for {symbol}: {pos_size_mult:.2f}x (New Notional: ${quote_amount:.2f})")

    # Cap maximum order allocation by the safety drawdown circuit breaker limit
    max_alloc_cap = min(equity * 0.25, 2500.0)  # Institutional cap: 25% single-asset
    if quote_amount > max_alloc_cap:
        quote_amount = max_alloc_cap
        
    qty = quote_amount / entry if entry > 0 else 0.0
    fee = quote_amount * BACKTEST_FEE_RATE
    return qty, quote_amount, fee


def check_volatility_circuit_breaker(df: pd.DataFrame, symbol: str) -> bool:
    """
    Calculate market volatility as standard deviation of last 20 close returns.
    If volatility exceeds 10%, block entry orders to prevent trading in chaotic markets.
    """
    if df is None or len(df) < 21:
        return False
    returns = df["close"].pct_change().tail(20)
    volatility = float(returns.std())
    if volatility > 0.10:
        print(f"[Circuit Breaker] {symbol} high volatility detected ({volatility*100:.2f}%). SUSPENDING entry execution.")
        msg = f"⚠️ <b>VOLATILITY CIRCUIT BREAKER TRIGGERED</b>\n\n<code>{symbol}</code> standard deviation of returns (<b>{volatility*100:.2f}%</b>) exceeds the 10.0% safety threshold. Order execution suspended."
        telegram_bot.send_telegram_message(msg)
        return True
    return False


def track_and_close_positions(args: argparse.Namespace) -> None:
    """
    Track active open positions from the trade journal, evaluate
    trailing stops (Chandelier Exit) or standard TP/SL, close breached positions,
    and push real-time exit alerts to Telegram.
    """
    print("\n" + "="*85)
    print("[POSITION MONITOR] EVALUATING ACTIVE OPEN POSITIONS & TRAILING STOPS".center(85))
    print("="*85)
    
    try:
        portfolio = get_portfolio_summary()
        open_positions = portfolio.get("open_positions", [])
    except Exception as e:
        print(f"[Position Monitor] Failed to load open positions: {e}")
        return
        
    # Restrict monitoring to explicit user symbols if specified via specialized CLI flags
    active_targets = []
    if getattr(args, "crypto", ""):
        active_targets.extend(args.crypto.split(","))
    if getattr(args, "stocks", ""):
        active_targets.extend(args.stocks.split(","))
    if getattr(args, "forex", ""):
        active_targets.extend(args.forex.split(","))
    target_symbols = {s.strip().upper() for s in active_targets if s.strip()}
    if target_symbols:
        open_positions = [pos for pos in open_positions if pos["symbol"].upper() in target_symbols]
            
    active_monitored = 0
    for pos in open_positions:
        symbol = pos["symbol"]
        qty = float(pos["qty"])
        entry_price = float(pos["entry_price"])
        
        if qty == 0 or abs(qty) < 1e-7:
            continue
            
        active_monitored += 1
        is_long = qty > 0
        tf = "1h" if is_stock(symbol) else "15m"
        
        print(f"\n[Position Monitor] Checking {symbol} ({'LONG' if is_long else 'SHORT'}): Qty={qty:.6f}, AvgEntry=${entry_price:.4f}")
        
        df = fetch_data_unified(symbol, tf, 100)
        if df.empty or len(df) < 30:
            print(f"  [Warning] Insufficient or missing data for {symbol}. Skipping monitor.")
            continue
            
        # Load tuned parameters if they exist
        from genetic_tuner import load_tuned_parameters
        tuned = load_tuned_parameters(symbol)
        
        local_ema_fast = 12
        local_ema_slow = 26
        local_sl_mult = ATR_MULTIPLIER_SL
        local_tp_mult = ATR_MULTIPLIER_TP
        
        if tuned:
            local_ema_fast = tuned.get("ema_fast", 12)
            local_ema_slow = tuned.get("ema_slow", 26)
            local_sl_mult = tuned.get("atr_multiplier_sl", ATR_MULTIPLIER_SL)
            local_tp_mult = tuned.get("atr_multiplier_tp", ATR_MULTIPLIER_TP)
            
        df = add_indicators(df, atr_period=ATR_PERIOD, ema_fast_span=local_ema_fast, ema_slow_span=local_ema_slow)
        adv = analyze_advanced(df)
        
        last = df.iloc[-1]
        current_price = float(last["close"])
        atr = float(last.get("atr14", 0.0))
        
        # Calculate dynamic stop-loss/take-profit levels
        chandelier_long = adv.get("chandelier_long")
        chandelier_short = adv.get("chandelier_short")
        
        # Hard limits
        if is_long:
            hard_sl = entry_price - atr * local_sl_mult if atr else entry_price * 0.95
            hard_tp = entry_price + atr * local_tp_mult if atr else entry_price * 1.10
        else:
            hard_sl = entry_price + atr * local_sl_mult if atr else entry_price * 1.05
            hard_tp = entry_price - atr * local_tp_mult if atr else entry_price * 0.90
            
        print(f"  Current Price: ${current_price:.4f} | Hard SL: ${hard_sl:.4f} | Hard TP: ${hard_tp:.4f}")
        if chandelier_long and is_long:
            print(f"  Chandelier Long Exit (Stop): ${chandelier_long:.4f}")
        if chandelier_short and not is_long:
            print(f"  Chandelier Short Exit (Stop): ${chandelier_short:.4f}")
            
        exit_triggered = False
        reason = ""
        
        # Check Long positions
        if is_long:
            if current_price <= hard_sl:
                exit_triggered = True
                reason = f"Hard Stop-Loss hit at ${hard_sl:.4f}"
            elif current_price >= hard_tp:
                exit_triggered = True
                reason = f"Hard Take-Profit hit at ${hard_tp:.4f}"
            elif chandelier_long and current_price < chandelier_long:
                exit_triggered = True
                reason = f"Chandelier Exit Trailing Stop hit at ${chandelier_long:.4f}"
        # Check Short positions
        else:
            if current_price >= hard_sl:
                exit_triggered = True
                reason = f"Hard Stop-Loss hit at ${hard_sl:.4f}"
            elif current_price <= hard_tp:
                exit_triggered = True
                reason = f"Hard Take-Profit hit at ${hard_tp:.4f}"
            elif chandelier_short and current_price > chandelier_short:
                exit_triggered = True
                reason = f"Chandelier Exit Trailing Stop hit at ${chandelier_short:.4f}"
                
        if exit_triggered:
            print(f"[Exit Triggered] {reason} for {symbol}!")
            side = "SELL" if is_long else "BUY"
            qty_to_close = abs(qty)
            realized_pnl = (current_price - entry_price) * qty_to_close if is_long else (entry_price - current_price) * qty_to_close
            fee = (qty_to_close * current_price) * BACKTEST_FEE_RATE
            
            if is_stock(symbol):
                try:
                    save_trade(
                        symbol=symbol,
                        side=side,
                        qty=qty_to_close,
                        price=current_price,
                        fee=fee,
                        strategy="TRAILING_STOP_EXIT",
                        timeframe=tf,
                        notes=f"Mock Stock Trailing Stop triggered via {reason}. Realized PnL: ${realized_pnl:.2f}"
                    )
                    print(f"  [Executor] Saved stock exit trade for {symbol} @ ${current_price:.4f}")
                except Exception as e:
                    print(f"  [Error] Failed to save exit trade: {e}")
            else:
                exec_res = execute_smart_order(symbol, side, quote_amount=(qty_to_close * current_price))
                print(f"[Executor] Crypto exit response: {exec_res}")
                try:
                    save_trade(
                        symbol=symbol,
                        side=side,
                        qty=qty_to_close,
                        price=current_price,
                        fee=fee,
                        strategy="TRAILING_STOP_EXIT",
                        timeframe=tf,
                        notes=f"Crypto Trailing Stop exit via {reason}. Realized PnL: ${realized_pnl:.2f}. Resp: {str(exec_res)[:60]}"
                    )
                    print(f"  [Executor] Saved crypto exit trade for {symbol} @ ${current_price:.4f}")
                except Exception as e:
                    print(f"  [Error] Failed to save exit trade: {e}")
                    
            # Send Telegram Alert
            telegram_bot.send_exit_alert(symbol, side, qty_to_close, current_price, realized_pnl, reason)
        else:
            print("  [Monitor] Position is safe. Continuing to hold.")
            
    if active_monitored == 0:
        print("  No active open positions found to monitor.")
    print("="*85 + "\n")

def execute_smart_order(symbol: str, side: str, quote_amount: float | None = None, quantity: float | None = None) -> dict:
    """Executes order routing through SmartOrderRouter (Binance/OKX SOR) using dynamic execution algos (Iceberg/VWAP)."""
    try:
        from exchange_router import ExchangeRouter
        from execution_algos import execute_iceberg_order, execute_vwap_order
        from config import EXECUTION_ALGO
        
        router = ExchangeRouter()
        
        if EXECUTION_ALGO == "ICEBERG":
            res_list = execute_iceberg_order(router, symbol, side, quantity=quantity, quote_qty=quote_amount)
            return res_list[0] if res_list else {"status": "error", "message": "Iceberg failed"}
        elif EXECUTION_ALGO == "VWAP":
            res_list = execute_vwap_order(router, symbol, side, quantity=quantity, quote_qty=quote_amount)
            return res_list[0] if res_list else {"status": "error", "message": "VWAP failed"}
        else:
            return router.route_order(symbol, side, quantity=quantity, quote_qty=quote_amount)
    except Exception as e:
        # Graceful fallback to default high_conviction paper trader in case routing environment fails
        print(f"[Smart Router] routing failed, falling back: {e}")
        import high_conviction
        return high_conviction.execute_paper_order(symbol, side, quote_amount=quote_amount, quantity=quantity)

def execute_consensus_signals(results: dict[str, dict], args: argparse.Namespace) -> None:
    """Execute paper orders for consensus signals when they cross the 4/6 strategy threshold."""
    if not getattr(args, "enable_paper_execute", False):
        return
        
    exceeded, equity, limit = is_drawdown_limit_exceeded()
    if exceeded:
        print("\n" + "="*85)
        print("[CRITICAL RISK MANAGER] PORTFOLIO EXECUTION BLOCKED!")
        print(f"   Current paper equity (${equity:.2f}) has breached the 20% max drawdown limit (${limit:.2f})!")
        print("   Halt placed on new order entries to protect account capital.")
        print("="*85 + "\n")
        return
        
    for symbol, data in results.items():
        action = data.get("action", "WAIT")
        score_str = data.get("signal_score", "0/6")
        try:
            score_num = int(score_str.split("/")[0])
        except Exception:
            score_num = 0
            
        if score_num >= 4 and action in {"BUY", "SELL"}:
            price = data.get("entry")
            if not price:
                continue
                
            tf = data.get("signal_timeframe", "n/a")
            stop = data.get("stop")
            
            # Fetch volatility data and run circuit breaker
            vol_df = fetch_data_unified(symbol, tf, 50)
            if check_volatility_circuit_breaker(vol_df, symbol):
                continue
            
            # Use dynamic position sizing
            qty, quote_amount, fee = compute_dynamic_position_size(symbol, price, stop)
            
            print(f"[Executor] Consensus {action} signal triggered for {symbol} with score {score_str}!")
            print(f"[Executor] Risk Manager sized order: Qty={qty:.4f}, Notional=${quote_amount:.2f}, Fee=${fee:.2f}")
            
            # Send Consensus Alert to Telegram
            telegram_bot.send_consensus_signal_alert(
                symbol=symbol,
                action=action,
                score=score_str,
                price=price,
                sl=stop,
                tp=data.get("take"),
                regime=data.get("regime", "n/a"),
                ml_signal=data.get("ml_signal"),
                ml_confidence=data.get("ml_confidence", 0.0),
                shap_explanation=data.get("shap_explanation"),
                tv_rating=data.get("tv_rating"),
                tv_rsi=data.get("tv_rsi"),
            )

            
            # Send LLM Desk alert to Telegram if available
            llm_raw = data.get("llm_raw", {})
            if llm_raw and not llm_raw.get("error") and llm_raw.get("action", "HOLD") != "HOLD":
                telegram_bot.send_llm_desk_alert(
                    symbol=symbol,
                    action=llm_raw.get("action", "HOLD"),
                    confidence=llm_raw.get("confidence", 0.0),
                    reasoning=llm_raw.get("reasoning", ""),
                    bull_case=llm_raw.get("bull_case", ""),
                    bear_case=llm_raw.get("bear_case", ""),
                    risk_assessment=llm_raw.get("risk_assessment", ""),
                )
            
            # Calculate voting strategies for logging in database notes
            voting_strats = []
            per_strat = data.get("per_strategy", {})
            for k, v in per_strat.items():
                if v == action or (action == "BUY" and v == "LONG") or (action == "SELL" and v == "SHORT"):
                    voting_strats.append(k)
            votes_str = f" [VOTES] {','.join(voting_strats)}" if voting_strats else ""

            if is_stock(symbol):
                try:
                    save_trade(
                        symbol=symbol,
                        side=action,
                        qty=qty,
                        price=price,
                        fee=fee,
                        strategy=f"CONSENSUS_{score_str.replace('/', '_')}",
                        timeframe=tf,
                        notes=f"Mock Stock Consensus {action} placed by bot with dynamic risk sizing.{votes_str}"
                    )
                    print(f"[Executor] Saved Stock Consensus {action} order for {symbol} @ {price:.2f} to journal.")
                    # Send execution alert
                    telegram_bot.send_trade_execution_alert(symbol, action, qty, price, stop, data.get("take"), 1.0, quote_amount)
                except Exception as e:
                    print(f"[Executor] Failed to save consensus stock trade: {e}")
            else:
                exec_res = execute_smart_order(symbol, action, quote_amount=quote_amount)
                print(f"[Executor] Crypto Consensus order response for {symbol}: {exec_res}")
                try:
                    save_trade(
                        symbol=symbol,
                        side=action,
                        qty=qty,
                        price=price,
                        fee=fee,
                        strategy=f"CONSENSUS_{score_str.replace('/', '_')}",
                        timeframe=tf,
                        notes=f"Crypto Consensus order with dynamic risk sizing. Response: {str(exec_res)[:60]}.{votes_str}"
                    )
                    print(f"[Executor] Saved Crypto Consensus {action} order for {symbol} @ {price:.2f} to journal.")
                    # Send execution alert
                    telegram_bot.send_trade_execution_alert(symbol, action, qty, price, stop, data.get("take"), 1.0, quote_amount)
                except Exception as e:
                    print(f"[Executor] Failed to save consensus crypto trade to journal: {e}")

def execute_opportunities_bold(crypto_list: list[str], stock_list: list[str], args: argparse.Namespace) -> None:
    """Run dynamic high-conviction momentum checks and place alerts/orders."""
    bold_results = []
    all_symbols = crypto_list + stock_list
    
    drawdown_blocked = False
    if getattr(args, "enable_paper_execute", False):
        exceeded, equity, limit = is_drawdown_limit_exceeded()
        if exceeded:
            drawdown_blocked = True
            print("\n" + "="*85)
            print("[CRITICAL RISK MANAGER] BOLD PLACEMENT BLOCKED!")
            print(f"   Current paper equity (${equity:.2f}) has breached the 20% max drawdown limit (${limit:.2f})!")
            print("   Automatic BOLD order placements are blocked to protect capital.")
            print("="*85 + "\n")
            
    for symbol in all_symbols:
        try:
            # Check high conviction on shorter timeframe (15m/1h)
            tf = "1h" if is_stock(symbol) else "15m"
            df = fetch_data_unified(symbol, tf, 200)
            if df.empty or len(df) < 50:
                continue
                
            cfg = high_conviction.HCConfig()
            df = high_conviction.add_hc_indicators(df, cfg)
            
            latest = df.iloc[-1]
            price = float(latest["close"])
            
            buy_signal = high_conviction.is_bold_buy(df, cfg)
            sell_signal = high_conviction.is_bold_sell(df, cfg)
            
            if buy_signal:
                bold_results.append((symbol, "BUY", price))
                
                # Check Volatility Circuit Breaker
                if check_volatility_circuit_breaker(df, symbol):
                    continue
                
                if getattr(args, "enable_bold_alerts", False):
                    msg = f"🔥 <b>BOLD OPPORTUNITY DETECTED</b>\n\nBUY <code>{symbol}</code> @ <b>${price:.4f}</b> | Momentum Release"
                    telegram_bot.send_telegram_message(msg)
                    
                if getattr(args, "enable_paper_execute", False):
                    if drawdown_blocked:
                        print(f"[Executor] Safety Block Active: BOLD BUY for {symbol} blocked due to account drawdown.")
                        continue
                    # For bold signals, assume stop price is entry minus cfg.SL_PCT
                    stop = price * (1 - cfg.SL_PCT / 100)
                    qty, quote_amount, fee = compute_dynamic_position_size(symbol, price, stop)
                    
                    if is_stock(symbol):
                        print(f"[Executor] Placing Mock Stock BOLD Order for {symbol} @ {price:.2f}")
                        print(f"[Executor] Risk Manager sized order: Qty={qty:.4f}, Notional=${quote_amount:.2f}, Fee=${fee:.2f}")
                        try:
                            save_trade(
                                symbol=symbol,
                                side="BUY",
                                qty=qty,
                                price=price,
                                fee=fee,
                                strategy="BOLD_MOMENTUM",
                                timeframe=tf,
                                notes="Mock Stock BOLD Order placed by bot with dynamic risk sizing."
                            )
                            # Send trade execution alert
                            telegram_bot.send_trade_execution_alert(symbol, "BUY", qty, price, stop, price * (1 + cfg.SL_PCT * 1.5 / 100), 1.0, quote_amount)
                        except Exception as e:
                            print(f"[Executor] Failed to save BOLD stock trade: {e}")
                    else:
                        exec_res = execute_smart_order(symbol, "BUY", quote_amount=quote_amount)
                        print(f"[Executor] Crypto BOLD Paper order response for {symbol}: {exec_res}")
                        print(f"[Executor] Risk Manager sized order: Qty={qty:.4f}, Notional=${quote_amount:.2f}, Fee=${fee:.2f}")
                        try:
                            save_trade(
                                symbol=symbol,
                                side="BUY",
                                qty=qty,
                                price=price,
                                fee=fee,
                                strategy="BOLD_MOMENTUM",
                                timeframe=tf,
                                notes=f"Crypto BOLD order with dynamic risk sizing. Response: {str(exec_res)[:60]}"
                            )
                            # Send trade execution alert
                            telegram_bot.send_trade_execution_alert(symbol, "BUY", qty, price, stop, price * (1 + cfg.SL_PCT * 1.5 / 100), 1.0, quote_amount)
                        except Exception as e:
                            print(f"[Executor] Failed to save BOLD crypto trade: {e}")
                            
            elif sell_signal:
                bold_results.append((symbol, "SELL", price))
                
                # Check Volatility Circuit Breaker
                if check_volatility_circuit_breaker(df, symbol):
                    continue
                
                if getattr(args, "enable_bold_alerts", False):
                    msg = f"⚠️ <b>BOLD EXIT SIGNAL DETECTED</b>\n\nSELL <code>{symbol}</code> @ <b>${price:.4f}</b> | Momentum Exhausted"
                    telegram_bot.send_telegram_message(msg)
                    
                if getattr(args, "enable_paper_execute", False):
                    if drawdown_blocked:
                        print(f"[Executor] Safety Block Active: BOLD SELL for {symbol} blocked due to account drawdown.")
                        continue
                    # For bold exits, assume stop is entry plus cfg.SL_PCT (in case of short exit)
                    stop = price * (1 + cfg.SL_PCT / 100)
                    qty, quote_amount, fee = compute_dynamic_position_size(symbol, price, stop)
                    
                    if is_stock(symbol):
                        print(f"[Executor] Placing Mock Stock BOLD SELL Order for {symbol} @ {price:.2f}")
                        print(f"[Executor] Risk Manager sized order: Qty={qty:.4f}, Notional=${quote_amount:.2f}, Fee=${fee:.2f}")
                        try:
                            save_trade(
                                symbol=symbol,
                                side="SELL",
                                qty=qty,
                                price=price,
                                fee=fee,
                                strategy="BOLD_MOMENTUM",
                                timeframe=tf,
                                notes="Mock Stock BOLD SELL Order placed by bot with dynamic risk sizing."
                            )
                            # Send exit alert
                            telegram_bot.send_exit_alert(symbol, "SELL", qty, price, 0.0, "BOLD exit signal triggered.")
                        except Exception as e:
                            print(f"[Executor] Failed to save BOLD stock exit: {e}")
                    else:
                        exec_res = execute_smart_order(symbol, "SELL", quote_amount=quote_amount)
                        print(f"[Executor] Crypto BOLD Paper sell response for {symbol}: {exec_res}")
                        print(f"[Executor] Risk Manager sized order: Qty={qty:.4f}, Notional=${quote_amount:.2f}, Fee=${fee:.2f}")
                        try:
                            save_trade(
                                symbol=symbol,
                                side="SELL",
                                qty=qty,
                                price=price,
                                fee=fee,
                                strategy="BOLD_MOMENTUM",
                                timeframe=tf,
                                notes=f"Crypto BOLD exit with dynamic risk sizing. Response: {str(exec_res)[:60]}"
                            )
                            # Send exit alert
                            telegram_bot.send_exit_alert(symbol, "SELL", qty, price, 0.0, "BOLD exit signal triggered.")
                        except Exception as e:
                            print(f"[Executor] Failed to save BOLD crypto exit: {e}")
        except Exception:
            continue
            
    if bold_results:
        _print_section("HIGH-CONVICTION OPPORTUNITIES (BOLD MOVES)")
        rows = [[s, act, f"${p:.4f}"] for s, act, p in bold_results]
        print(_format_table(["Asset", "Action", "Execution Price"], rows))

def print_execution_summary(results: dict[str, dict]) -> None:
    """Formulate clear, actionable buy and sell recommendations with terminal color enhancements."""
    _print_section("UNIFIED TRADING RECOMMENDATIONS")
    
    buys = []
    sells = []
    holds = []
    
    for symbol, data in results.items():
        action = data.get("action", "WAIT")
        tf = data.get("signal_timeframe", "n/a")
        score = data.get("signal_score", "0/3")
        entry = data.get("entry")
        stop = data.get("stop")
        take = data.get("take")
        regime = data.get("regime", "Sideways")
        
        px_fmt = 2 if is_stock(symbol) else 4
        entry_s = _format_value(entry, px_fmt)
        stop_s = _format_value(stop, px_fmt)
        take_s = _format_value(take, px_fmt)
        
        # Colorize regime names
        if regime == "BULL_TREND":
            regime_s = f"{Colors.BOLD}{Colors.GREEN}BULL_TREND{Colors.END}"
        elif regime == "BEAR_TREND":
            regime_s = f"{Colors.BOLD}{Colors.RED}BEAR_TREND{Colors.END}"
        elif regime == "MEAN_REVERSION":
            regime_s = f"{Colors.BOLD}{Colors.CYAN}MEAN_REVERSION{Colors.END}"
        elif regime == "HIGH_VOLATILITY":
            regime_s = f"{Colors.BOLD}{Colors.MAGENTA}HIGH_VOLATILITY{Colors.END}"
        else:
            regime_s = f"{Colors.BOLD}{Colors.YELLOW}{regime}{Colors.END}"
            
        if action == "BUY":
            info = f"  {Colors.BOLD}{Colors.GREEN}[BUY]{Colors.END} {Colors.BOLD}{symbol}{Colors.END} ({tf}) | Entry: {entry_s} | Stop: {stop_s} | Target: {take_s} | Score: {Colors.BOLD}{Colors.GREEN}{score}{Colors.END} | Regime: {regime_s}"
            buys.append(info)
        elif action == "SELL":
            info = f"  {Colors.BOLD}{Colors.RED}[SELL]{Colors.END} {Colors.BOLD}{symbol}{Colors.END} ({tf}) | Entry: {entry_s} | Stop: {stop_s} | Target: {take_s} | Score: {Colors.BOLD}{Colors.RED}{score}{Colors.END} | Regime: {regime_s}"
            sells.append(info)
        else:
            info = f"  {Colors.BOLD}{Colors.YELLOW}[HOLD]{Colors.END} {Colors.BOLD}{symbol}{Colors.END} | Regime: {regime_s} | Consensus: {score}"
            holds.append(info)
            
    if buys:
        print(f"\n{Colors.BOLD}{Colors.GREEN}ENTRY SIGNALS (Ready to Execute):{Colors.END}")
        for b in buys:
            print(b)
            
    if sells:
        print(f"\n{Colors.BOLD}{Colors.RED}EXIT SIGNALS (Ready to Close):{Colors.END}")
        for s in sells:
            print(s)
            
    if holds:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}MONITOR / WAIT LIST:{Colors.END}")
        for h in holds:
            print(h)
            
    print(f"\n{Colors.BOLD}{Colors.CYAN}Risk Parameters & Safety Compliance Guidelines:{Colors.END}")
    print(f"  * Strict Stop-Loss (SL) = Entry +/- (ATR * 2) enforced on all open orders.")
    print(f"  * Target Profit (TP) = Entry +/- (ATR * 3) to protect your risk-reward ratio.")
    print(f"  * Position-sizing: Allocate exactly 1-2% of total cash per trade to protect your capital.")
    print(f"  * Only pull the trigger when at least 4/6 strategies reach consensus (Super-Consensus).")

def _run_cycle(args: argparse.Namespace) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    raw_title = "UNIFIED MULTI-MARKET BOT OPPORTUNITY FINDER"
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*85}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{raw_title.center(85)}{Colors.END}")
    print(f"{Colors.CYAN}{timestamp.center(85)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*85}{Colors.END}")
    
    # 1. Setup logging & Start metrics server
    structured_logger.setup_logging()
    logger = structured_logger.get_logger("trading_bot.cycle")
    logger.info("Cycle execution started", timestamp=timestamp)
    
    start_time = time.time()
    
    if getattr(args, "metrics", False):
        try:
            metrics_server.start_metrics_server(9090)
        except Exception as e:
            logger.error("Failed to start metrics server", error=str(e))
            
    crypto_list = []
    stock_list = []
    
    if getattr(args, "crypto", ""):
        crypto_list = [s.strip().upper() for s in args.crypto.split(",") if s.strip()]
    if getattr(args, "stocks", ""):
        stock_list = [s.strip().upper() for s in args.stocks.split(",") if s.strip()]
    if getattr(args, "forex", ""):
        # Forex fiat pairs map directly to traditional yfinance equities/stock loader (e.g. GBPUSD=X)
        forex_symbols = [s.strip().upper() for s in args.forex.split(",") if s.strip()]
        for fs in forex_symbols:
            if fs not in stock_list:
                stock_list.append(fs)
                
    # Fallback to dynamic asset discovery if none of the specialized parameters are set
    if not crypto_list and not stock_list:
        crypto_list, stock_list = run_multi_market_discovery("")
        
    all_symbols = crypto_list + stock_list
    
    # 2. Portfolio Optimization: HRP Weights
    if not getattr(args, "skip_hrp", False) and all_symbols:
        logger.info("Running Hierarchical Risk Parity portfolio optimization", symbols=all_symbols)
        print("\n--- HRP Portfolio Optimization & Risk Analysis ---")
        returns_dict = {}
        for symbol in all_symbols:
            try:
                # Fetch 252 daily bars for reliable returns calculation (1 year)
                df_daily = fetch_data_unified(symbol, "1d", 252)
                if not df_daily.empty and len(df_daily) >= 10:
                    returns_dict[symbol] = df_daily["close"].pct_change()
            except Exception as e:
                logger.error("Failed to fetch daily returns for HRP", symbol=symbol, error=str(e))
                
        try:
            global HRP_WEIGHTS
            weights = portfolio_optimizer.get_optimal_weights(all_symbols, returns_dict, max_weight=0.25)
            HRP_WEIGHTS.clear()
            HRP_WEIGHTS.update(weights)
            
            # Print and log HRP allocation weights
            hrp_rows = []
            for sym, wt in weights.items():
                hrp_rows.append([sym, f"{wt:.2%}"])
            print(_format_table(["Symbol", "HRP Target Weight"], hrp_rows))
            logger.info("HRP weights computed", weights=weights)
            
            # Calculate and display portfolio risk metrics
            risk_metrics = portfolio_optimizer.compute_portfolio_risk_metrics(returns_dict, weights)
            print("\nPortfolio Risk Metrics:")
            print(f"  * Annualized Portfolio Volatility: {risk_metrics.get('portfolio_volatility', 0.0):.2%}")
            print(f"  * Portfolio Sharpe Ratio (Rf=0): {risk_metrics.get('portfolio_sharpe', 0.0):.4f}")
            print(f"  * Diversification Ratio: {risk_metrics.get('diversification_ratio', 1.0):.4f}")
            max_corr = risk_metrics.get("max_correlation_pair")
            if max_corr:
                print(f"  * Highest Correlation Pair: {max_corr[0]} & {max_corr[1]} (corr = {max_corr[2]:.4f})")
            
            # Record current account equity metric
            try:
                summary = get_portfolio_summary()
                starting_balance = 10000.0
                net_pnl = float(summary.get("net_pnl", 0.0) or 0.0)
                open_positions = summary.get("open_positions", [])
                unrealized_pnl = sum(float(p.get("unrealized_pnl", 0.0) or 0.0) for p in open_positions)
                equity = starting_balance + net_pnl + unrealized_pnl
                metrics_server.update_equity(equity)
                metrics_server.update_positions(len(open_positions))
            except Exception as e:
                logger.error("Failed to update account metrics", error=str(e))
        except Exception as e:
            logger.error("HRP execution failed", error=str(e))
            
    # Active trailing stop & exit monitor
    if args.enable_paper_execute:
        track_and_close_positions(args)
        
    results = print_market_analysis(crypto_list, stock_list, args)
    
    execute_consensus_signals(results, args)
    
    execute_opportunities_bold(crypto_list, stock_list, args)
    
    if not args.skip_backtest:
        print_backtest_results(crypto_list, stock_list)
        
    if not args.skip_portfolio:
        print_portfolio_analysis()
        
    if not args.skip_frameworks:
        print_framework_statuses()
        if getattr(args, "run_plugins", False):
            run_active_plugins(args)
        
    print_execution_summary(results)
    
    # Auto-run trade learning and Self-Evolution Engine optimization sweep
    try:
        from evolution_engine import SelfEvolutionEngine
        print("\n" + "="*85)
        print("SELF-EVOLUTION ENGINE: REINFORCEMENT LEARNING SWEEP")
        print("="*85)
        engine = SelfEvolutionEngine()
        engine.evolve()
        print("="*85 + "\n")
    except Exception as e:
        logger.error("Self-Evolution execution failed", error=str(e))
    
    # Record duration metric
    duration = time.time() - start_time
    metrics_server.record_cycle(duration)
    
    logger.info("Cycle execution finished", duration_sec=duration)
    _print_section("CYCLE REPORT TERMINATED SUCCESSFULLY")
    
    print_available_commands()

def main() -> None:
    import signal
    import os
    import sys
    
    def sigint_handler(sig, frame):
        print("\n\n[Terminated] Force stopping the Multi-Market opportunity scanner. Goodbye!")
        try:
            from external_frameworks import terminate_active_framework
            terminate_active_framework()
        except Exception:
            pass
        os._exit(0)
        
    if sys.platform == "win32":
        try:
            import ctypes
            global _win32_ctrl_handler_ref
            PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            _win32_ctrl_handler_ref = PHANDLER_ROUTINE(win32_ctrl_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_win32_ctrl_handler_ref, True)
        except Exception:
            signal.signal(signal.SIGINT, sigint_handler)
    else:
        signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser(
        description="Unified Stock & Crypto Opportunity Finder Bot"
    )

    parser.add_argument(
        "--crypto",
        type=str,
        default="",
        help="Specialized target cryptocurrency symbols separated by commas (e.g. BTCUSDT,ETHUSDT)"
    )
    parser.add_argument(
        "--stocks",
        type=str,
        default="",
        help="Specialized target traditional stock tickers separated by commas (e.g. AAPL,TSLA)"
    )
    parser.add_argument(
        "--forex",
        type=str,
        default="",
        help="Specialized target global Forex pairs separated by commas (e.g. GBPUSD,EURUSD)"
    )
    parser.add_argument(
        "--deep-dive",
        type=str,
        default="",
        help="Single targeted symbol to execute multi-layered investigative quantitative deep-dive on"
    )
    parser.add_argument(
        "--generate-stress-data",
        action="store_true",
        help="Generate synthetic black-swan Merton Jump-Diffusion market data frames for stress testing"
    )
    parser.add_argument(
        "--event-backtest",
        action="store_true",
        help="Run high-fidelity fill-by-fill Event-Driven Backtesting Core simulation"
    )
    parser.add_argument(
        "--run-wfo",
        action="store_true",
        help="Run sliding Walk-Forward Parameter Optimization validator"
    )
    parser.add_argument(
        "--evolve",
        action="store_true",
        help="Run the standalone trade learning and Self-Evolution Engine optimization sweep"
    )
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Skip historical backtests"
    )
    parser.add_argument(
        "--skip-portfolio",
        action="store_true",
        help="Skip active trade journal overview"
    )
    parser.add_argument(
        "--skip-frameworks",
        action="store_true",
        help="Skip external integrations overview"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Execute in an infinite scanning loop"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Interval sleep in loop (seconds, default: 900)"
    )
    parser.add_argument(
        "--disable-bold-alerts",
        action="store_true",
        help="Disable active Telegram alerts for high-conviction (bold) signals"
    )
    parser.add_argument(
        "--disable-paper-execute",
        action="store_true",
        help="Disable mock paper orders automatically on signals"
    )
    parser.add_argument(
        "--skip-ml",
        action="store_true",
        help="Skip Machine Learning Signal Engine"
    )
    parser.add_argument(
        "--retrain-ml",
        action="store_true",
        help="Force retrain ML models"
    )
    parser.add_argument(
        "--skip-sentiment",
        action="store_true",
        help="Skip financial news sentiment analysis"
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Enable Prometheus metrics exporter on port 9090"
    )
    parser.add_argument(
        "--skip-hrp",
        action="store_true",
        help="Skip Hierarchical Risk Parity portfolio allocation weights"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        dest="parallel",
        help="Use multi-threaded parallel scanning for assets"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_false",
        dest="parallel",
        help="Disable multi-threaded parallel scanning"
    )
    parser.add_argument(
        "--run-plugins",
        action="store_true",
        help="Automatically execute all ready external plugins/frameworks at the end of the scan cycle"
    )
    parser.add_argument(
        "--plugin",
        type=str,
        default="",
        help="Execute only a specific plugin by its key (e.g., --plugin quant)"
    )
    parser.add_argument(
        "--plugin-args",
        type=str,
        default="",
        help="Extra arguments to pass to the executed plugins (e.g. --plugin-args '--test')"
    )
    parser.add_argument(
        "--llm-desk",
        action="store_true",
        dest="llm_desk",
        help="Enable TradingAgents multi-agent LLM analysis (requires GOOGLE_API_KEY or other LLM provider key)"
    )
    parser.set_defaults(parallel=True)
    
    args = parser.parse_args()
    args.enable_paper_execute = not args.disable_paper_execute
    args.enable_bold_alerts = not args.disable_bold_alerts
    
    if getattr(args, "evolve", False):
        try:
            from evolution_engine import SelfEvolutionEngine
            print("\n--- STANDALONE SELF-EVOLUTION OPTIMIZER SWEEP ---")
            engine = SelfEvolutionEngine()
            engine.evolve()
        except Exception as e:
            print(f"[Error] Failed to run standalone evolution: {e}")
        print_available_commands()
        return

    if getattr(args, "deep_dive", ""):
        _run_deep_dive(args.deep_dive, args)
        return
        
    if not args.loop:
        _run_cycle(args)
        return
        
    try:
        while True:
            _run_cycle(args)
            print(f"\n[Loop] Sleeping for {args.interval} seconds... Ctrl+C to terminate.")
            time.sleep(max(args.interval, 10))
    except KeyboardInterrupt:
        print("\n[Terminated] Stopping the Multi-Market opportunity scanner.")

if __name__ == "__main__":
    main()
