"""
Structured logging module.
Uses structlog for JSON file output + colored console output.
Falls back to stdlib logging if structlog is not installed.
"""

import logging
import os
import sys
import threading
from typing import Any, Optional

_setup_lock = threading.Lock()
_is_configured = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None  # type: ignore[assignment]
    STRUCTLOG_AVAILABLE = False


# ---------------------------------------------------------------------------
# stdlib fallback  (used when structlog is missing)
# ---------------------------------------------------------------------------

class _StdlibBoundLogger:
    """Minimal shim that mimics structlog.BoundLogger using stdlib logging."""

    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None):
        self._logger = logger
        self._context: dict[str, Any] = context or {}

    def _fmt(self, msg: str, kw: dict[str, Any]) -> str:
        merged = {**self._context, **kw}
        extra = " ".join(f"{k}={v}" for k, v in merged.items())
        return f"{msg}  {extra}" if extra else msg

    def bind(self, **new_values: Any) -> "_StdlibBoundLogger":
        ctx = {**self._context, **new_values}
        return _StdlibBoundLogger(self._logger, ctx)

    def unbind(self, *keys: str) -> "_StdlibBoundLogger":
        ctx = {k: v for k, v in self._context.items() if k not in keys}
        return _StdlibBoundLogger(self._logger, ctx)

    def msg(self, message: str, **kw: Any) -> None:
        self.info(message, **kw)

    def debug(self, message: str, **kw: Any) -> None:
        self._logger.debug(self._fmt(message, kw))

    def info(self, message: str, **kw: Any) -> None:
        self._logger.info(self._fmt(message, kw))

    def warning(self, message: str, **kw: Any) -> None:
        self._logger.warning(self._fmt(message, kw))

    def error(self, message: str, **kw: Any) -> None:
        self._logger.error(self._fmt(message, kw))

    def critical(self, message: str, **kw: Any) -> None:
        self._logger.critical(self._fmt(message, kw))

    def exception(self, message: str, **kw: Any) -> None:
        self._logger.exception(self._fmt(message, kw))


def _setup_stdlib_fallback(
    log_dir: str = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> None:
    """Configure stdlib logging as a fallback."""
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # remove existing handlers to avoid duplicates on re-setup
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # file handler (JSONL-ish plain text)
    fh = logging.FileHandler(
        os.path.join(log_dir, "bot.jsonl"), encoding="utf-8"
    )
    fh.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    fh.setFormatter(fmt)
    root.addHandler(fh)


# ---------------------------------------------------------------------------
# structlog configuration
# ---------------------------------------------------------------------------

def _setup_structlog(
    log_dir: str = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> None:
    """Full structlog setup: JSON to file, pretty to console."""
    os.makedirs(log_dir, exist_ok=True)

    # stdlib root logger (structlog renders, stdlib routes)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # -- console handler: human-readable colored output --
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    root.addHandler(console_handler)

    # -- file handler: JSON lines --
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "bot.jsonl"), encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    root.addHandler(file_handler)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Formatter for console: dev-friendly
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)

    # Formatter for file: JSON
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(json_formatter)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(
    log_dir: str = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> None:
    """
    One-time logging setup.  Safe to call multiple times (idempotent).
    """
    global _is_configured
    with _setup_lock:
        if _is_configured:
            return
        if STRUCTLOG_AVAILABLE:
            _setup_structlog(log_dir, console_level, file_level)
        else:
            logging.getLogger(__name__).warning(
                "structlog not installed -- falling back to stdlib logging"
            )
            _setup_stdlib_fallback(log_dir, console_level, file_level)
        
        # Silence verbose third-party loggers to prevent log file bloating
        for verbose_logger in ["yfinance", "urllib3", "requests", "binance", "matplotlib", "asyncio", "ccxt", "httpcore"]:
            logging.getLogger(verbose_logger).setLevel(logging.WARNING)
            
        _is_configured = True


def get_logger(name: str = "trading_bot") -> Any:
    """
    Return a bound logger.  Calls setup_logging() automatically on first use.
    Returns structlog.BoundLogger when available, else a stdlib shim.
    """
    if not _is_configured:
        setup_logging()

    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return _StdlibBoundLogger(logging.getLogger(name))


def bind_context(**kwargs: Any) -> Any:
    """
    Return a new logger with the given key-value pairs bound into every
    subsequent log line.  Typical usage::

        log = bind_context(symbol="BTC", timeframe="1h", cycle_id=42)
        log.info("scan started")
    """
    return get_logger().bind(**kwargs)
