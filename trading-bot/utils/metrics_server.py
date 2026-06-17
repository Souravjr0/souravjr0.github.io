"""
Lightweight Prometheus metrics exporter.
Starts a daemon HTTP thread serving /metrics.
All functions become no-ops if prometheus_client is not installed.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        start_http_server,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed -- metrics endpoint disabled, "
        "all metric functions are no-ops"
    )

# ---------------------------------------------------------------------------
# Metric definitions (only created when prometheus_client is present)
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    SCAN_CYCLE_DURATION = Histogram(
        "bot_scan_cycle_duration_seconds",
        "Duration of a single scan cycle in seconds",
        buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
    )
    ACTIVE_POSITIONS = Gauge(
        "bot_active_positions_count",
        "Number of currently active positions",
    )
    PAPER_EQUITY = Gauge(
        "bot_paper_equity_usd",
        "Current paper-trading equity in USD",
    )
    SIGNALS_GENERATED = Counter(
        "bot_signals_generated_total",
        "Total number of trading signals generated",
        ["action"],
    )
    API_ERRORS = Counter(
        "bot_api_errors_total",
        "Total API errors by exchange",
        ["exchange"],
    )
    ML_CONFIDENCE = Gauge(
        "bot_ml_confidence_score",
        "Latest ML model confidence score per symbol",
        ["symbol"],
    )
    SENTIMENT_SCORE = Gauge(
        "bot_sentiment_score",
        "Latest sentiment score per symbol",
        ["symbol"],
    )
    KALMAN_Z = Gauge(
        "bot_kalman_z_score",
        "Latest Kalman Filter innovation z-score per symbol",
        ["symbol"],
    )
    EWMA_VOL = Gauge(
        "bot_ewma_volatility",
        "Latest EWMA volatility score per symbol",
        ["symbol"],
    )
else:
    SCAN_CYCLE_DURATION = None
    ACTIVE_POSITIONS = None
    PAPER_EQUITY = None
    SIGNALS_GENERATED = None
    API_ERRORS = None
    ML_CONFIDENCE = None
    SENTIMENT_SCORE = None
    KALMAN_Z = None
    EWMA_VOL = None

# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

_server_started = False
_server_lock = threading.Lock()


def start_metrics_server(port: int = 9090) -> None:
    """
    Start a background daemon thread serving Prometheus metrics on *port*.
    Safe to call multiple times; only the first call has effect.
    """
    global _server_started
    if not PROMETHEUS_AVAILABLE:
        logger.info("Prometheus not available -- metrics server not started")
        return

    with _server_lock:
        if _server_started:
            return
        try:
            start_http_server(port)
            _server_started = True
            logger.info("Prometheus metrics server started on port %d", port)
        except OSError as exc:
            logger.error("Failed to start metrics server on port %d: %s", port, exc)


# ---------------------------------------------------------------------------
# Convenience helpers  (all no-ops when prometheus_client is absent)
# ---------------------------------------------------------------------------

def record_cycle(duration: float) -> None:
    """Record a scan cycle duration in seconds."""
    if SCAN_CYCLE_DURATION is not None:
        SCAN_CYCLE_DURATION.observe(duration)


def update_positions(count: int) -> None:
    """Set the active-positions gauge."""
    if ACTIVE_POSITIONS is not None:
        ACTIVE_POSITIONS.set(count)


def update_equity(equity: float) -> None:
    """Set the paper-equity gauge."""
    if PAPER_EQUITY is not None:
        PAPER_EQUITY.set(equity)


def record_signal(action: str) -> None:
    """Increment the signals counter for a given action (BUY / SELL / HOLD)."""
    if SIGNALS_GENERATED is not None:
        SIGNALS_GENERATED.labels(action=action).inc()


def record_api_error(exchange: str) -> None:
    """Increment the API-error counter for a given exchange."""
    if API_ERRORS is not None:
        API_ERRORS.labels(exchange=exchange).inc()


def update_ml_confidence(symbol: str, confidence: float) -> None:
    """Set the ML confidence gauge for a symbol."""
    if ML_CONFIDENCE is not None:
        ML_CONFIDENCE.labels(symbol=symbol).set(confidence)


def update_sentiment(symbol: str, score: float) -> None:
    """Set the sentiment gauge for a symbol."""
    if SENTIMENT_SCORE is not None:
        SENTIMENT_SCORE.labels(symbol=symbol).set(score)


def update_kalman_z(symbol: str, score: float) -> None:
    """Set the Kalman Z innovation gauge for a symbol."""
    if KALMAN_Z is not None:
        KALMAN_Z.labels(symbol=symbol).set(score)


def update_ewma_vol(symbol: str, vol: float) -> None:
    """Set the EWMA volatility gauge for a symbol."""
    if EWMA_VOL is not None:
        EWMA_VOL.labels(symbol=symbol).set(vol)
