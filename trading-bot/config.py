import os

from dotenv import load_dotenv


load_dotenv()


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "").strip()
BINANCE_TESTNET = _get_bool(os.getenv("BINANCE_TESTNET"), True)
BINANCE_RECV_WINDOW = int(os.getenv("BINANCE_RECV_WINDOW", "5000"))
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "").strip()

EXCHANGE_PROVIDER = os.getenv("EXCHANGE_PROVIDER", "binance_rest").strip().lower()
CCXT_EXCHANGE = os.getenv("CCXT_EXCHANGE", "binance").strip().lower()
CCXT_TESTNET = _get_bool(os.getenv("CCXT_TESTNET"), BINANCE_TESTNET)
CCXT_ENABLE_RATE_LIMIT = _get_bool(os.getenv("CCXT_ENABLE_RATE_LIMIT"), True)
CCXT_HOSTNAME = os.getenv("CCXT_HOSTNAME", "").strip()
PYTHON_BINANCE_TESTNET = _get_bool(os.getenv("PYTHON_BINANCE_TESTNET"), BINANCE_TESTNET)

EXTERNAL_FRAMEWORKS_DIR = os.getenv("EXTERNAL_FRAMEWORKS_DIR", "external").strip()
INVESTING_ALGO_PATH = os.getenv("INVESTING_ALGO_PATH", "").strip()
INVESTING_ALGO_ENTRYPOINT = os.getenv("INVESTING_ALGO_ENTRYPOINT", "").strip()
TRADING_BOT_FRAMEWORK_PATH = os.getenv("TRADING_BOT_FRAMEWORK_PATH", "").strip()
TRADING_BOT_FRAMEWORK_ENTRYPOINT = os.getenv("TRADING_BOT_FRAMEWORK_ENTRYPOINT", "").strip()
ALGO_TRADING_ENGINE_PATH = os.getenv("ALGO_TRADING_ENGINE_PATH", "").strip()
ALGO_TRADING_ENGINE_ENTRYPOINT = os.getenv("ALGO_TRADING_ENGINE_ENTRYPOINT", "").strip()
ADVANCED_AI_ML_FRAMEWORK_PATH = os.getenv("ADVANCED_AI_ML_FRAMEWORK_PATH", "").strip()
ADVANCED_AI_ML_FRAMEWORK_ENTRYPOINT = os.getenv("ADVANCED_AI_ML_FRAMEWORK_ENTRYPOINT", "").strip()
DELTA_RISKBOT_PATH = os.getenv("DELTA_RISKBOT_PATH", "").strip()
DELTA_RISKBOT_ENTRYPOINT = os.getenv("DELTA_RISKBOT_ENTRYPOINT", "").strip()
NAUTILUS_TRADER_PATH = os.getenv("NAUTILUS_TRADER_PATH", "").strip()
NAUTILUS_TRADER_ENTRYPOINT = os.getenv("NAUTILUS_TRADER_ENTRYPOINT", "").strip()
QUANT_PATH = os.getenv("QUANT_PATH", "").strip()
QUANT_ENTRYPOINT = os.getenv("QUANT_ENTRYPOINT", "").strip()
AI_TRADING_PLATFORM_PATH = os.getenv("AI_TRADING_PLATFORM_PATH", "").strip()
AI_TRADING_PLATFORM_ENTRYPOINT = os.getenv("AI_TRADING_PLATFORM_ENTRYPOINT", "").strip()

TRADINGVIEW_WEBHOOK_SECRET = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "").strip()

DEFAULT_QUOTE_AMOUNT = float(os.getenv("DEFAULT_QUOTE_AMOUNT", "20"))
MIN_QUOTE_AMOUNT = float(os.getenv("MIN_QUOTE_AMOUNT", "1"))
MAX_QUOTE_AMOUNT = float(os.getenv("MAX_QUOTE_AMOUNT", "1000"))
QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT").strip().upper()

TRACKER_TOP_N = int(os.getenv("TRACKER_TOP_N", "10"))
TRACKER_TIMEFRAMES = [
    tf.strip()
    for tf in os.getenv("TRACKER_TIMEFRAMES", "15m,1h,4h,1d").split(",")
    if tf.strip()
]
TRACKER_BARS = int(os.getenv("TRACKER_BARS", "200"))

ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
ATR_MULTIPLIER_SL = float(os.getenv("ATR_MULTIPLIER_SL", "2"))
ATR_MULTIPLIER_TP = float(os.getenv("ATR_MULTIPLIER_TP", "3"))

BACKTEST_BARS = int(os.getenv("BACKTEST_BARS", "1000"))
BACKTEST_FEE_RATE = float(os.getenv("BACKTEST_FEE_RATE", "0.001"))
JOURNAL_DB_PATH = os.getenv("JOURNAL_DB_PATH", "trader.db").strip()

# --- ML Signal Engine Settings ---
ML_CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.65"))
ML_RETRAIN_DAYS = int(os.getenv("ML_RETRAIN_DAYS", "7"))
ML_LOOKFORWARD_BARS = int(os.getenv("ML_LOOKFORWARD_BARS", "5"))
ML_LABEL_THRESHOLD_PCT = float(os.getenv("ML_LABEL_THRESHOLD_PCT", "1.5"))
ML_MODEL_DIR = os.getenv("ML_MODEL_DIR", "models").strip()

# --- Sentiment Analysis Settings ---
SENTIMENT_ENABLED = _get_bool(os.getenv("SENTIMENT_ENABLED"), True)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "").strip()
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "").strip()

# --- Portfolio Optimizer Settings ---
ENABLE_HRP_OPTIMIZER = _get_bool(os.getenv("ENABLE_HRP_OPTIMIZER"), True)
HRP_MAX_WEIGHT = float(os.getenv("HRP_MAX_WEIGHT", "0.25"))
HRP_LOOKBACK_DAYS = int(os.getenv("HRP_LOOKBACK_DAYS", "60"))

# --- Prometheus Metrics Settings ---
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
METRICS_ENABLED = _get_bool(os.getenv("METRICS_ENABLED"), False)

_default_watchlist = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "ASTERUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "TONUSDT",
    "AVAXUSDT",
    "DOTUSDT",
]

WATCHLIST = [
    symbol.strip().upper()
    for symbol in os.getenv("WATCHLIST", ",".join(_default_watchlist)).split(",")
    if symbol.strip()
]

# --- Institutional Expansion Settings ---
OKX_API_KEY = os.getenv("OKX_API_KEY", "").strip()
OKX_API_SECRET = os.getenv("OKX_API_SECRET", "").strip()
OKX_API_PASSWORD = os.getenv("OKX_API_PASSWORD", "").strip()

TUNED_PARAMS_PATH = os.getenv("TUNED_PARAMS_PATH", "tuned_parameters.json").strip()

# Execution Algorithm: "MARKET", "ICEBERG", "VWAP"
EXECUTION_ALGO = os.getenv("EXECUTION_ALGO", "ICEBERG").strip().upper()
ICEBERG_CHUNKS = int(os.getenv("ICEBERG_CHUNKS", "5"))
ICEBERG_RANDOM_DELAY = _get_bool(os.getenv("ICEBERG_RANDOM_DELAY"), True)

# PyTorch LSTM Model Parameters
LSTM_EPOCHS = int(os.getenv("LSTM_EPOCHS", "20"))
LSTM_BATCH_SIZE = int(os.getenv("LSTM_BATCH_SIZE", "32"))
LSTM_LOOKBACK = int(os.getenv("LSTM_LOOKBACK", "30"))

# --- Sentry & Monitoring Settings ---
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production").strip()
