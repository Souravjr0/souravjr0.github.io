"""
News sentiment scoring module.
Uses free APIs only: CryptoCompare public news + Yahoo Finance RSS.
No paid keys required.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in financial sentiment dictionary  (200+ terms)
# Each value is a raw sentiment score: positive = bullish, negative = bearish
# ---------------------------------------------------------------------------
SENTIMENT_DICT: dict[str, float] = {
    # ------ bullish terms ------
    "surge": 0.8,
    "surges": 0.8,
    "surging": 0.8,
    "rally": 0.7,
    "rallies": 0.7,
    "rallying": 0.7,
    "breakout": 0.7,
    "bullish": 0.8,
    "soar": 0.8,
    "soars": 0.8,
    "soaring": 0.8,
    "gain": 0.5,
    "gains": 0.5,
    "profit": 0.5,
    "profits": 0.5,
    "profitable": 0.5,
    "upgrade": 0.6,
    "upgraded": 0.6,
    "beat": 0.5,
    "beats": 0.5,
    "outperform": 0.6,
    "outperforms": 0.6,
    "outperforming": 0.6,
    "uptick": 0.4,
    "uptrend": 0.5,
    "rebound": 0.5,
    "rebounds": 0.5,
    "rebounding": 0.5,
    "recovery": 0.5,
    "recover": 0.5,
    "recovering": 0.5,
    "moon": 0.9,
    "mooning": 0.9,
    "pump": 0.6,
    "pumping": 0.6,
    "pumps": 0.6,
    "boom": 0.7,
    "booming": 0.7,
    "explode": 0.7,
    "explodes": 0.7,
    "skyrocket": 0.8,
    "skyrockets": 0.8,
    "jump": 0.5,
    "jumps": 0.5,
    "jumping": 0.5,
    "spike": 0.5,
    "spikes": 0.5,
    "spiking": 0.5,
    "climb": 0.4,
    "climbs": 0.4,
    "climbing": 0.4,
    "rise": 0.4,
    "rises": 0.4,
    "rising": 0.4,
    "positive": 0.3,
    "strong": 0.4,
    "strength": 0.4,
    "higher": 0.3,
    "high": 0.2,
    "record": 0.3,
    "ath": 0.7,
    "accumulate": 0.4,
    "accumulation": 0.4,
    "buy": 0.4,
    "buying": 0.4,
    "bought": 0.3,
    "long": 0.3,
    "adoption": 0.5,
    "adopt": 0.5,
    "adopts": 0.5,
    "partnership": 0.4,
    "launch": 0.3,
    "launches": 0.3,
    "launched": 0.3,
    "approve": 0.5,
    "approved": 0.5,
    "approval": 0.5,
    "support": 0.3,
    "supports": 0.3,
    "supported": 0.3,
    "milestone": 0.4,
    "success": 0.5,
    "successful": 0.5,
    "innovation": 0.3,
    "innovative": 0.3,
    "growth": 0.4,
    "growing": 0.4,
    "expand": 0.3,
    "expanding": 0.3,
    "expansion": 0.3,
    "momentum": 0.4,
    "optimism": 0.5,
    "optimistic": 0.5,
    "confidence": 0.4,
    "confident": 0.4,
    "breakthrough": 0.6,
    "opportunity": 0.3,
    "opportunities": 0.3,
    "bullrun": 0.7,
    "upgrade": 0.5,
    "overweight": 0.4,
    "outpace": 0.4,
    "exceed": 0.4,
    "exceeds": 0.4,
    "exceeded": 0.4,
    "dividend": 0.3,
    "earnings": 0.3,
    "revenue": 0.2,
    "inflow": 0.4,
    "inflows": 0.4,
    "institutional": 0.3,

    # ------ bearish terms ------
    "crash": -0.9,
    "crashes": -0.9,
    "crashing": -0.9,
    "plunge": -0.8,
    "plunges": -0.8,
    "plunging": -0.8,
    "dump": -0.7,
    "dumps": -0.7,
    "dumping": -0.7,
    "bearish": -0.8,
    "decline": -0.5,
    "declines": -0.5,
    "declining": -0.5,
    "loss": -0.5,
    "losses": -0.5,
    "downgrade": -0.6,
    "downgraded": -0.6,
    "miss": -0.5,
    "misses": -0.5,
    "missed": -0.5,
    "underperform": -0.6,
    "underperforms": -0.6,
    "underperforming": -0.6,
    "selloff": -0.7,
    "sell-off": -0.7,
    "drop": -0.5,
    "drops": -0.5,
    "dropping": -0.5,
    "fall": -0.5,
    "falls": -0.5,
    "falling": -0.5,
    "fell": -0.5,
    "sink": -0.6,
    "sinks": -0.6,
    "sinking": -0.6,
    "tank": -0.7,
    "tanks": -0.7,
    "tanking": -0.7,
    "tumble": -0.6,
    "tumbles": -0.6,
    "tumbling": -0.6,
    "collapse": -0.8,
    "collapses": -0.8,
    "collapsing": -0.8,
    "negative": -0.3,
    "weak": -0.4,
    "weakness": -0.4,
    "lower": -0.3,
    "low": -0.2,
    "downturn": -0.5,
    "downtrend": -0.5,
    "correction": -0.4,
    "bear": -0.5,
    "rekt": -0.8,
    "liquidate": -0.6,
    "liquidated": -0.6,
    "liquidation": -0.6,
    "sell": -0.3,
    "selling": -0.4,
    "sold": -0.3,
    "short": -0.3,
    "shorting": -0.4,
    "ban": -0.6,
    "banned": -0.6,
    "bans": -0.6,
    "restrict": -0.5,
    "restricted": -0.5,
    "restriction": -0.5,
    "sue": -0.5,
    "sued": -0.5,
    "lawsuit": -0.5,
    "fine": -0.4,
    "fined": -0.4,
    "penalty": -0.4,
    "hack": -0.7,
    "hacked": -0.7,
    "exploit": -0.7,
    "exploited": -0.7,
    "scam": -0.8,
    "fraud": -0.8,
    "rug": -0.9,
    "rugpull": -0.9,
    "ponzi": -0.9,
    "risk": -0.3,
    "risky": -0.3,
    "fear": -0.5,
    "panic": -0.7,
    "capitulation": -0.8,
    "recession": -0.6,
    "inflation": -0.3,
    "default": -0.6,
    "bankruptcy": -0.8,
    "bankrupt": -0.8,
    "insolvent": -0.8,
    "insolvency": -0.8,
    "debt": -0.3,
    "bubble": -0.5,
    "overvalued": -0.4,
    "overbought": -0.3,
    "warning": -0.4,
    "caution": -0.3,
    "concern": -0.3,
    "concerns": -0.3,
    "volatile": -0.3,
    "volatility": -0.2,
    "uncertainty": -0.4,
    "outflow": -0.4,
    "outflows": -0.4,
    "underweight": -0.4,
    "delist": -0.6,
    "delisted": -0.6,
    "delisting": -0.6,
    "investigation": -0.5,
    "investigated": -0.5,
    "subpoena": -0.5,
    "regulation": -0.2,
    "crackdown": -0.6,
    "shutdown": -0.6,
    "suspend": -0.5,
    "suspended": -0.5,
    "freeze": -0.5,
    "frozen": -0.5,
    "trouble": -0.4,
    "troubled": -0.4,
    "struggle": -0.4,
    "struggling": -0.4,
    "disappoint": -0.4,
    "disappointing": -0.5,
    "disappointment": -0.5,
    "delay": -0.3,
    "delayed": -0.3,
    "stagnant": -0.3,
    "stagnation": -0.3,
    "exit": -0.3,
}

# Intensity modifiers: multiply the next sentiment word's score
INTENSITY_AMPLIFIERS: dict[str, float] = {
    "massive": 1.5,
    "huge": 1.5,
    "enormous": 1.5,
    "extreme": 1.5,
    "extremely": 1.5,
    "significantly": 1.4,
    "significant": 1.4,
    "sharply": 1.4,
    "sharp": 1.4,
    "major": 1.3,
    "dramatically": 1.5,
    "dramatic": 1.5,
    "unprecedented": 1.5,
    "historic": 1.4,
    "record-breaking": 1.5,
    "explosive": 1.5,
    "parabolic": 1.5,
    "insane": 1.5,
    "incredible": 1.4,
    "remarkable": 1.3,
    "substantial": 1.3,
    "heavily": 1.3,
    "aggressively": 1.3,
}

INTENSITY_DAMPENERS: dict[str, float] = {
    "slight": 0.5,
    "slightly": 0.5,
    "minor": 0.5,
    "marginal": 0.5,
    "marginally": 0.5,
    "modest": 0.6,
    "modestly": 0.6,
    "somewhat": 0.6,
    "little": 0.5,
    "small": 0.5,
    "tiny": 0.4,
    "barely": 0.4,
    "partial": 0.6,
    "partially": 0.6,
    "gradual": 0.6,
    "gradually": 0.6,
    "mild": 0.5,
    "mildly": 0.5,
}

# negation words flip the sign
NEGATIONS: set[str] = {
    "not", "no", "never", "neither", "nor", "hardly",
    "isn't", "aren't", "wasn't", "weren't", "won't",
    "don't", "doesn't", "didn't", "can't", "cannot",
    "shouldn't", "wouldn't", "couldn't",
}

_WORD_RE = re.compile(r"[a-z0-9'\-]+")


def _score_text(text: str) -> float:
    """Score a single headline / text snippet. Returns -1.0 .. 1.0."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.0

    total = 0.0
    count = 0
    modifier = 1.0
    negate = False

    for w in words:
        # check negation
        if w in NEGATIONS:
            negate = True
            continue

        # check intensity
        if w in INTENSITY_AMPLIFIERS:
            modifier = INTENSITY_AMPLIFIERS[w]
            continue
        if w in INTENSITY_DAMPENERS:
            modifier = INTENSITY_DAMPENERS[w]
            continue

        # check sentiment
        if w in SENTIMENT_DICT:
            score = SENTIMENT_DICT[w] * modifier
            if negate:
                score = -score
            total += score
            count += 1

        # reset modifiers after consuming a non-modifier word
        modifier = 1.0
        negate = False

    if count == 0:
        return 0.0

    raw = total / count
    return max(-1.0, min(1.0, raw))


def _label(score: float) -> str:
    if score > 0.1:
        return "BULLISH"
    elif score < -0.1:
        return "BEARISH"
    return "NEUTRAL"


def _fetch_url(url: str, timeout: int = 10) -> Optional[bytes]:
    """Fetch raw bytes from a URL. Returns None on failure."""
    try:
        req = Request(url, headers={"User-Agent": "TradingBot/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, OSError, Exception) as exc:
        logger.warning("HTTP fetch failed for %s: %s", url, exc)
        return None


def _neutral(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "score": 0.0,
        "headline_count": 0,
        "top_headline": "",
        "sentiment_label": "NEUTRAL",
    }


# ---- Crypto: CryptoCompare public API ----

# common mappings for ticker -> coin name used in CryptoCompare categories
_COIN_NAMES: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "DOT": "Polkadot",
    "AVAX": "Avalanche",
    "MATIC": "Polygon",
    "LINK": "Chainlink",
    "LTC": "Litecoin",
    "UNI": "Uniswap",
    "ATOM": "Cosmos",
    "NEAR": "NEAR",
    "ARB": "Arbitrum",
    "OP": "Optimism",
    "APT": "Aptos",
    "SUI": "Sui",
    "BNB": "BNB",
    "SHIB": "Shiba Inu",
}


def get_crypto_sentiment(symbol: str) -> dict:
    """
    Fetch latest crypto news from CryptoCompare and score headlines.
    No API key required for basic access.
    """
    coin = _COIN_NAMES.get(symbol.upper(), symbol)
    url = f"https://min-api.cryptocompare.com/data/v2/news/?categories={coin}"

    raw = _fetch_url(url)
    if raw is None:
        return _neutral(symbol)

    try:
        import json
        data = json.loads(raw)
    except Exception:
        return _neutral(symbol)

    articles = data.get("Data", [])
    if not articles:
        return _neutral(symbol)

    scores: list[float] = []
    headlines: list[str] = []
    for art in articles[:50]:  # cap to 50 headlines
        title = art.get("title", "")
        body = art.get("body", "")
        text = f"{title}. {body[:200]}"
        headlines.append(title)
        scores.append(_score_text(text))

    if not scores:
        return _neutral(symbol)

    avg_score = sum(scores) / len(scores)
    avg_score = max(-1.0, min(1.0, avg_score))

    # top headline = the one with strongest absolute score
    best_idx = max(range(len(scores)), key=lambda i: abs(scores[i]))
    return {
        "symbol": symbol.upper(),
        "score": round(avg_score, 4),
        "headline_count": len(scores),
        "top_headline": headlines[best_idx] if headlines else "",
        "sentiment_label": _label(avg_score),
    }


# ---- Stock: Yahoo Finance RSS ----

def get_stock_sentiment(symbol: str) -> dict:
    """
    Fetch RSS from Yahoo Finance and score headlines.
    """
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"

    raw = _fetch_url(url)
    if raw is None:
        return _neutral(symbol)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return _neutral(symbol)

    items = root.findall(".//item")
    if not items:
        return _neutral(symbol)

    scores: list[float] = []
    headlines: list[str] = []
    for item in items[:50]:
        title_el = item.find("title")
        desc_el = item.find("description")
        title = title_el.text if title_el is not None and title_el.text else ""
        desc = desc_el.text if desc_el is not None and desc_el.text else ""
        text = f"{title}. {desc[:200]}"
        headlines.append(title)
        scores.append(_score_text(text))

    if not scores:
        return _neutral(symbol)

    avg_score = sum(scores) / len(scores)
    avg_score = max(-1.0, min(1.0, avg_score))

    best_idx = max(range(len(scores)), key=lambda i: abs(scores[i]))
    return {
        "symbol": symbol.upper(),
        "score": round(avg_score, 4),
        "headline_count": len(scores),
        "top_headline": headlines[best_idx] if headlines else "",
        "sentiment_label": _label(avg_score),
    }


# ---- Dispatcher ----

def get_sentiment(symbol: str, is_stock: bool = False) -> dict:
    """
    Unified entry point.  Routes to crypto or stock sentiment.
    Returns neutral on any failure.
    """
    try:
        if is_stock:
            return get_stock_sentiment(symbol)
        return get_crypto_sentiment(symbol)
    except Exception as exc:
        logger.error("Sentiment fetch error for %s: %s", symbol, exc)
        return _neutral(symbol)


# ---- CLI quick test ----

if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    stock_flag = "--stock" in sys.argv
    result = get_sentiment(sym, is_stock=stock_flag)
    print("--- Sentiment Result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
