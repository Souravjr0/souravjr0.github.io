#!/usr/bin/env python3
"""
TradingAgents LLM Desk Plugin
Wraps the TauricResearch/TradingAgents multi-agent LLM framework into a single
callable function for our unified_analyzer pipeline.

The framework deploys 6+ specialized LLM agents (market analyst, news analyst,
sentiment analyst, fundamentals analyst, bull/bear researchers, risk debators,
portfolio manager) that debate and vote on a trading decision.

Requires: pip install tradingagents
LLM Provider: Configured via TRADINGAGENTS_LLM_PROVIDER env var (default: google)
"""

import os
import sys
import time
import signal
import logging
import warnings
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Suppress verbose langchain/langgraph warnings globally before any imports
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")
logging.getLogger("langchain").setLevel(logging.ERROR)
logging.getLogger("langchain_core").setLevel(logging.ERROR)
logging.getLogger("langgraph").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("anthropic").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Check if tradingagents is available
_TRADINGAGENTS_AVAILABLE = False
_IMPORT_ERROR = None
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import TradingAgentsConfig
    from tradingagents.llm_clients.google_client import NormalizedChatGoogleGenerativeAI
    _TRADINGAGENTS_AVAILABLE = True
    
    # Patch TradingAgentsGraph._get_provider_kwargs to automatically include retry policies
    # for API rate limit resilience on free tiers (Google Gemini 429 errors).
    _orig_get_provider_kwargs = TradingAgentsGraph._get_provider_kwargs
    
    def _patched_get_provider_kwargs(self):
        kwargs = _orig_get_provider_kwargs(self)
        # Add robust retry policies for LLM providers
        kwargs["max_retries"] = 12  # Survives free-tier rate limits via backoff
        kwargs["timeout"] = 60.0
        return kwargs
        
    TradingAgentsGraph._get_provider_kwargs = _patched_get_provider_kwargs

    # Monkeypatch NormalizedChatGoogleGenerativeAI.invoke to intercept 429 RESOURCE_EXHAUSTED
    # and explicitly sleep/retry on the free tier.
    _orig_invoke = NormalizedChatGoogleGenerativeAI.invoke

    def _patched_invoke(self, prompt_input, config=None, **kwargs):
        import time
        import re
        max_attempts = 8
        for attempt in range(max_attempts):
            try:
                return _orig_invoke(self, prompt_input, config, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "GenerateRequestsPerDay" in err_str or "daily" in err_str.lower():
                    # Handle daily limit exhaustively and fail-fast
                    raise ValueError(
                        "Google Gemini API Key DAILY quota exceeded (20 requests/day limit on free tier). "
                        "Please upgrade to Pay-as-you-go in AI Studio to increase your limit to 1,500 RPD, or wait for the quota to reset at midnight Pacific Time."
                    ) from e
                elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Find retry delay in message, default to 35 seconds
                    match = re.search(r"retry in ([\d\.]+)s", err_str)
                    sleep_time = float(match.group(1)) + 1.0 if match else 35.0
                    print(f"\n[RATE_LIMIT] Gemini 429 Rate Limit hit. Retrying in {sleep_time:.1f}s... (Attempt {attempt+1}/{max_attempts})")
                    time.sleep(sleep_time)
                else:
                    raise e
        return _orig_invoke(self, prompt_input, config, **kwargs)

    NormalizedChatGoogleGenerativeAI.invoke = _patched_invoke
except ImportError as e:
    _IMPORT_ERROR = str(e)
except Exception as e:
    _IMPORT_ERROR = str(e)


# Default config — uses Google Gemini free tier
_LLM_DESK_CONFIG = {
    "llm_provider": os.getenv("TRADINGAGENTS_LLM_PROVIDER", "google"),
    "deep_think_llm": os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", "gemini-2.5-flash"),
    "quick_think_llm": os.getenv("TRADINGAGENTS_QUICK_THINK_LLM", "gemini-2.5-flash"),
    "max_debate_rounds": int(os.getenv("TRADINGAGENTS_MAX_DEBATE_ROUNDS", "1")),
    "max_risk_discuss_rounds": int(os.getenv("TRADINGAGENTS_MAX_RISK_ROUNDS", "1")),
}

# Timeout for a single LLM desk analysis (seconds)
LLM_DESK_TIMEOUT = int(os.getenv("TRADINGAGENTS_TIMEOUT", "180"))

# Cache the graph instance to avoid re-creating it every call
_cached_graph: Optional["TradingAgentsGraph"] = None


def _has_api_key() -> bool:
    """Check if at least one supported LLM API key is configured."""
    provider = _LLM_DESK_CONFIG["llm_provider"].lower()
    key_map = {
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "xai": "XAI_API_KEY",
    }
    # Check if the specific provider key is set
    env_var = key_map.get(provider)
    if env_var and os.getenv(env_var):
        return True
    # Ollama doesn't need a key
    if provider == "ollama":
        return True
    return False


def _get_graph(debug: bool = False) -> "TradingAgentsGraph":
    """Get or create a cached TradingAgentsGraph instance."""
    global _cached_graph
    if _cached_graph is not None:
        if hasattr(_cached_graph, "debug"):
            _cached_graph.debug = debug
        return _cached_graph

    if not _TRADINGAGENTS_AVAILABLE:
        raise ImportError(f"tradingagents package not available: {_IMPORT_ERROR}")

    if not _has_api_key():
        raise ValueError(
            f"No API key found for LLM provider '{_LLM_DESK_CONFIG['llm_provider']}'. "
            f"Set the appropriate env var (e.g., GOOGLE_API_KEY for Google Gemini)."
        )

    # Build config from TradingAgentsConfig + our overrides
    from pathlib import Path
    config = TradingAgentsConfig(
        results_dir=Path("./results"),
        llm_provider=_LLM_DESK_CONFIG["llm_provider"],
        deep_think_llm=_LLM_DESK_CONFIG["deep_think_llm"],
        quick_think_llm=_LLM_DESK_CONFIG["quick_think_llm"],
        max_debate_rounds=_LLM_DESK_CONFIG["max_debate_rounds"],
        max_risk_discuss_rounds=_LLM_DESK_CONFIG["max_risk_discuss_rounds"],
        max_recur_limit=int(os.getenv("TRADINGAGENTS_MAX_RECUR_LIMIT", "50")),
    )

    # For crypto, disable fundamentals analyst since crypto doesn't have balance sheets
    # For stocks, use full analyst suite
    _cached_graph = TradingAgentsGraph(
        selected_analysts=["market", "news", "social", "fundamentals"],
        debug=debug,
        config=config,
    )
    return _cached_graph


def _parse_decision(state) -> dict:
    """Extract the final trading decision from the TradingAgents graph state."""
    result = {
        "action": "HOLD",
        "confidence": 0.0,
        "reasoning": "",
        "bull_case": "",
        "bear_case": "",
        "risk_assessment": "",
        "raw_decision": "",
    }

    try:
        # Check if state is a tuple/list from propagate()
        if isinstance(state, (tuple, list)):
            state = state[0]

        # The final state contains the portfolio manager's decision
        messages = []
        if hasattr(state, "messages"):
            messages = state.messages
        elif isinstance(state, dict):
            messages = state.get("messages", [])
        elif hasattr(state, "model_dump"):
            messages = state.model_dump().get("messages", [])
        if not messages:
            return result

        # Get the last message which should be the final decision
        final_msg = messages[-1] if messages else None
        if final_msg is None:
            return result

        content = ""
        if hasattr(final_msg, "content"):
            content = final_msg.content
        elif isinstance(final_msg, dict):
            content = final_msg.get("content", "")
        elif isinstance(final_msg, str):
            content = final_msg

        result["raw_decision"] = content

        # Parse the action from the content
        content_upper = content.upper()
        if "STRONG BUY" in content_upper or "STRONGLY BUY" in content_upper:
            result["action"] = "BUY"
            result["confidence"] = 0.90
        elif "BUY" in content_upper and "NOT BUY" not in content_upper and "DON'T BUY" not in content_upper:
            result["action"] = "BUY"
            result["confidence"] = 0.70
        elif "STRONG SELL" in content_upper or "STRONGLY SELL" in content_upper:
            result["action"] = "SELL"
            result["confidence"] = 0.90
        elif "SELL" in content_upper and "NOT SELL" not in content_upper and "DON'T SELL" not in content_upper:
            result["action"] = "SELL"
            result["confidence"] = 0.70
        else:
            result["action"] = "HOLD"
            result["confidence"] = 0.50

        # Try to extract confidence percentage from content
        import re
        conf_match = re.search(r'(?:confidence|probability|certainty)[:\s]*(\d{1,3})%', content, re.IGNORECASE)
        if conf_match:
            parsed_conf = int(conf_match.group(1)) / 100.0
            if 0.0 <= parsed_conf <= 1.0:
                result["confidence"] = parsed_conf

        # Extract reasoning sections
        result["reasoning"] = _extract_section(content, ["reasoning", "rationale", "summary", "conclusion", "decision"])
        result["bull_case"] = _extract_section(content, ["bull", "bullish", "upside", "positive"])
        result["bear_case"] = _extract_section(content, ["bear", "bearish", "downside", "negative", "risk"])
        result["risk_assessment"] = _extract_section(content, ["risk", "position size", "allocation", "stop", "stop-loss"])

        # If no specific sections found, use the full content as reasoning
        if not result["reasoning"]:
            # Truncate to first 500 chars for display
            result["reasoning"] = content[:500].strip()

    except Exception as e:
        result["reasoning"] = f"Failed to parse LLM decision: {e}"

    return result


def _extract_section(text: str, keywords: list[str]) -> str:
    """Extract a section from LLM output based on keywords."""
    lines = text.split("\n")
    capturing = False
    captured = []

    for line in lines:
        line_lower = line.lower().strip()
        # Check if this line starts a relevant section
        if any(kw in line_lower for kw in keywords) and (":" in line or line.startswith("#") or line.startswith("**")):
            capturing = True
            # Include the header line content after the colon
            if ":" in line:
                after_colon = line.split(":", 1)[1].strip()
                if after_colon:
                    captured.append(after_colon)
            continue

        if capturing:
            # Stop at next section header
            if line.strip() and (line.startswith("#") or (line.startswith("**") and line.endswith("**"))):
                break
            if line.strip():
                captured.append(line.strip())

    return " ".join(captured[:5])  # Limit to 5 lines


def run_llm_desk(symbol: str, is_crypto: bool = True, debug: bool = False) -> dict:
    """
    Run the TradingAgents multi-agent LLM analysis on a symbol.

    Args:
        symbol: Trading symbol (e.g., "BTCUSDT", "AAPL")
        is_crypto: Whether the symbol is cryptocurrency
        debug: Enable verbose tracking outputs

    Returns:
        dict with keys: action, confidence, reasoning, bull_case, bear_case,
                        risk_assessment, raw_decision, elapsed_sec, error
    """
    start = time.time()
    result = {
        "action": "HOLD",
        "confidence": 0.0,
        "reasoning": "",
        "bull_case": "",
        "bear_case": "",
        "risk_assessment": "",
        "raw_decision": "",
        "elapsed_sec": 0.0,
        "error": None,
    }

    # Pre-flight checks
    if not _TRADINGAGENTS_AVAILABLE:
        result["error"] = f"tradingagents not installed: {_IMPORT_ERROR}"
        result["reasoning"] = "TradingAgents package not available. Install with: pip install tradingagents"
        return result

    if not _has_api_key():
        provider = _LLM_DESK_CONFIG["llm_provider"]
        result["error"] = f"No API key for provider '{provider}'"
        result["reasoning"] = f"Set the API key for your LLM provider. For Google: set GOOGLE_API_KEY in .env"
        return result

    # Convert crypto symbols for yfinance compatibility
    # TradingAgents uses yfinance internally, crypto needs special ticker format
    ticker = symbol
    if is_crypto:
        # Strip USDT/BUSD suffix and add -USD for yfinance
        for quote in ["USDT", "BUSD", "USD"]:
            if symbol.upper().endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                ticker = f"{base}-USD"
                break

    try:
        if debug:
            logging.getLogger().setLevel(logging.INFO)
            logging.getLogger("tradingagents").setLevel(logging.INFO)
            logging.getLogger("langgraph").setLevel(logging.INFO)
            print("[DEBUG] Initializing TradingAgents graph...")

        graph = _get_graph(debug=debug)

        # Determine which analysts to use based on asset type
        if is_crypto:
            # Crypto: skip fundamentals (no balance sheets for crypto)
            analysts = ["market", "news", "social"]
        else:
            # Stocks: full analyst suite
            analysts = ["market", "news", "social", "fundamentals"]

        # Re-create graph if analyst config changed
        global _cached_graph
        current_analysts = getattr(_cached_graph, '_selected_analysts', None)
        if current_analysts != analysts:
            from pathlib import Path
            from tradingagents.default_config import TradingAgentsConfig
            config = TradingAgentsConfig(
                results_dir=Path("./results"),
                llm_provider=_LLM_DESK_CONFIG["llm_provider"],
                deep_think_llm=_LLM_DESK_CONFIG["deep_think_llm"],
                quick_think_llm=_LLM_DESK_CONFIG["quick_think_llm"],
                max_debate_rounds=_LLM_DESK_CONFIG["max_debate_rounds"],
                max_risk_discuss_rounds=_LLM_DESK_CONFIG["max_risk_discuss_rounds"],
                max_recur_limit=int(os.getenv("TRADINGAGENTS_MAX_RECUR_LIMIT", "50")),
            )
            _cached_graph = TradingAgentsGraph(
                selected_analysts=analysts,
                debug=debug,
                config=config,
            )
            _cached_graph._selected_analysts = analysts
            graph = _cached_graph

        # Calculate date range for analysis
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        # Run the analysis with timeout protection (increased for debug runs)
        timeout = 600 if debug else LLM_DESK_TIMEOUT
        def _execute():
            return graph.propagate(ticker, end_date)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute)
            try:
                final_state = future.result(timeout=timeout)
            except FuturesTimeoutError:
                result["error"] = f"LLM Desk timed out after {timeout}s"
                result["reasoning"] = "Analysis took too long. Try reducing debate rounds or using a faster model."
                result["elapsed_sec"] = time.time() - start
                return result

        # Parse the decision from the graph state
        parsed = _parse_decision(final_state)
        result.update(parsed)

    except Exception as e:
        result["error"] = str(e)
        result["reasoning"] = f"LLM Desk analysis failed: {e}"

    result["elapsed_sec"] = time.time() - start
    return result


def get_llm_desk_status() -> dict:
    """Get the status of the LLM Desk integration."""
    return {
        "available": _TRADINGAGENTS_AVAILABLE,
        "import_error": _IMPORT_ERROR,
        "has_api_key": _has_api_key() if _TRADINGAGENTS_AVAILABLE else False,
        "provider": _LLM_DESK_CONFIG["llm_provider"],
        "deep_model": _LLM_DESK_CONFIG["deep_think_llm"],
        "quick_model": _LLM_DESK_CONFIG["quick_think_llm"],
        "timeout_sec": LLM_DESK_TIMEOUT,
    }


def format_llm_desk_output(result: dict, symbol: str) -> str:
    """Format LLM desk results for console display."""
    lines = []
    border = "=" * 85

    lines.append(f"\n{border}")
    lines.append("LLM TRADING DESK ANALYSIS (Multi-Agent AI)".center(85))
    lines.append(border)

    if result.get("error"):
        lines.append(f"  [WARNING] {result['error']}")
        if result.get("reasoning"):
            lines.append(f"  {result['reasoning']}")
        lines.append(border)
        return "\n".join(lines)

    action = result.get("action", "HOLD")
    confidence = result.get("confidence", 0.0)

    # Action with confidence
    action_display = f"{action} ({confidence:.0%} confidence)"
    if action == "BUY":
        lines.append(f"  >>> DECISION: {action_display} <<<")
    elif action == "SELL":
        lines.append(f"  >>> DECISION: {action_display} <<<")
    else:
        lines.append(f"  --- DECISION: {action_display} ---")

    lines.append(f"  Symbol: {symbol} | Elapsed: {result.get('elapsed_sec', 0.0):.1f}s")
    lines.append("")

    # Reasoning
    if result.get("reasoning"):
        lines.append("  Reasoning:")
        reasoning = result["reasoning"]
        # Word wrap at ~75 chars
        words = reasoning.split()
        line = "    "
        for word in words:
            if len(line) + len(word) + 1 > 80:
                lines.append(line)
                line = "    "
            line += word + " "
        if line.strip():
            lines.append(line)
        lines.append("")

    # Bull case
    if result.get("bull_case"):
        lines.append("  Bull Case:")
        lines.append(f"    {result['bull_case'][:200]}")
        lines.append("")

    # Bear case
    if result.get("bear_case"):
        lines.append("  Bear Case:")
        lines.append(f"    {result['bear_case'][:200]}")
        lines.append("")

    # Risk assessment
    if result.get("risk_assessment"):
        lines.append("  Risk Assessment:")
        lines.append(f"    {result['risk_assessment'][:200]}")

    lines.append(border)
    return "\n".join(lines)


def format_llm_desk_telegram(result: dict, symbol: str) -> str:
    """Format LLM desk results for Telegram notification."""
    action = result.get("action", "HOLD")
    confidence = result.get("confidence", 0.0)

    icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(action, "⚪")

    lines = [
        f"{icon} <b>LLM Trading Desk</b>",
        f"<code>{symbol}</code> → <b>{action}</b> ({confidence:.0%})",
        "",
    ]

    if result.get("reasoning"):
        lines.append(f"<i>{result['reasoning'][:150]}</i>")

    if result.get("error"):
        lines.append(f"⚠️ {result['error']}")

    return "\n".join(lines)


if __name__ == "__main__":
    """CLI test: python tradingagents_plugin.py BTCUSDT"""
    import argparse

    parser = argparse.ArgumentParser(description="TradingAgents LLM Desk - Direct Test")
    parser.add_argument("symbol", type=str, nargs="?", default="BTCUSDT", help="Symbol to analyze")
    parser.add_argument("--stock", action="store_true", help="Treat as stock symbol")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with full logs")
    args = parser.parse_args()

    # Show status
    status = get_llm_desk_status()
    print(f"LLM Desk Status:")
    print(f"  Available: {status['available']}")
    print(f"  Provider:  {status['provider']}")
    print(f"  Model:     {status['deep_model']}")
    print(f"  API Key:   {'SET' if status['has_api_key'] else 'MISSING'}")
    print()

    if not status["available"]:
        print(f"ERROR: {status['import_error']}")
        sys.exit(1)

    if not status["has_api_key"]:
        print(f"ERROR: No API key set for provider '{status['provider']}'")
        print(f"Set GOOGLE_API_KEY in your .env file to use Google Gemini (free tier)")
        sys.exit(1)

    symbol = args.symbol.upper()
    is_crypto = not args.stock

    print(f"Running LLM Desk analysis on {symbol} ({'crypto' if is_crypto else 'stock'})...")
    print(f"This may take 30-120 seconds as multiple AI agents debate...\n")

    result = run_llm_desk(symbol, is_crypto=is_crypto, debug=args.debug)
    print(format_llm_desk_output(result, symbol))
