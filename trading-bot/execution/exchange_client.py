import ccxt
from binance.client import Client as PyBinanceClient

from binance_client import BinanceClient
from config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_BASE_URL,
    BINANCE_RECV_WINDOW,
    BINANCE_TESTNET,
    CCXT_ENABLE_RATE_LIMIT,
    CCXT_EXCHANGE,
    CCXT_HOSTNAME,
    CCXT_TESTNET,
    EXCHANGE_PROVIDER,
    PYTHON_BINANCE_TESTNET,
    QUOTE_ASSET,
)


def _resolve_base_url() -> str:
    if BINANCE_BASE_URL:
        return BINANCE_BASE_URL
    return "https://testnet.binance.vision" if BINANCE_TESTNET else "https://api.binance.com"


def _to_ccxt_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if "/" in symbol:
        return symbol
    if symbol.endswith(QUOTE_ASSET):
        base = symbol[: -len(QUOTE_ASSET)]
        return f"{base}/{QUOTE_ASSET}"
    return symbol


def _from_ccxt_symbol(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def _ohlcv_to_klines(rows: list[list]) -> list[list]:
    klines: list[list] = []
    for row in rows:
        if len(row) < 6:
            continue
        ts, open_, high, low, close, volume = row[:6]
        klines.append(
            [
                ts,
                open_,
                high,
                low,
                close,
                volume,
                ts,
                0,
                0,
                0,
                0,
                0,
            ]
        )
    return klines


class BinanceRestAdapter:
    def __init__(self) -> None:
        self.client = BinanceClient(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            base_url=_resolve_base_url(),
            recv_window=BINANCE_RECV_WINDOW,
        )

    def get_ticker_24h(self) -> list[dict]:
        return self.client.get_ticker_24h()

    def get_price(self, symbol: str) -> float:
        return self.client.get_price(symbol)

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list]:
        return self.client.get_klines(symbol, interval, limit, start_time, end_time)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: float | None = None,
        quote_qty: float | None = None,
    ) -> dict:
        return self.client.place_order(symbol, side, order_type, quantity, quote_qty)


class CcxtAdapter:
    def __init__(self) -> None:
        exchange_class = getattr(ccxt, CCXT_EXCHANGE, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported ccxt exchange: {CCXT_EXCHANGE}")

        config = {
            "enableRateLimit": CCXT_ENABLE_RATE_LIMIT,
            "options": {"defaultType": "spot"},
        }
        if CCXT_EXCHANGE == "binance":
            if BINANCE_API_KEY:
                config["apiKey"] = BINANCE_API_KEY
            if BINANCE_API_SECRET:
                config["secret"] = BINANCE_API_SECRET
        
        # Apply custom hostname overrides for geo-restricted domains
        if CCXT_HOSTNAME:
            config["hostname"] = CCXT_HOSTNAME
        elif CCXT_EXCHANGE == "okx":
            config["hostname"] = "okx.cab"

        self.exchange = exchange_class(config)
        if CCXT_TESTNET and CCXT_EXCHANGE == "binance":
            self.exchange.set_sandbox_mode(True)

    def get_ticker_24h(self) -> list[dict]:
        tickers = self.exchange.fetch_tickers()
        data: list[dict] = []
        for ticker in tickers.values():
            symbol = _from_ccxt_symbol(ticker.get("symbol", ""))
            if not symbol.endswith(QUOTE_ASSET):
                continue
            data.append(
                {
                    "symbol": symbol,
                    "priceChangePercent": ticker.get("percentage") or 0,
                    "lastPrice": ticker.get("last") or ticker.get("close") or 0,
                    "quoteVolume": ticker.get("quoteVolume") or 0,
                    "highPrice": ticker.get("high") or 0,
                    "lowPrice": ticker.get("low") or 0,
                }
            )
        return data

    def get_price(self, symbol: str) -> float:
        ccxt_symbol = _to_ccxt_symbol(symbol)
        ticker = self.exchange.fetch_ticker(ccxt_symbol)
        return float(ticker.get("last") or ticker.get("close") or 0)

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list]:
        ccxt_symbol = _to_ccxt_symbol(symbol)
        rows = self.exchange.fetch_ohlcv(
            ccxt_symbol, timeframe=interval, since=start_time, limit=limit
        )
        if end_time is not None:
            rows = [row for row in rows if row[0] <= end_time]
        return _ohlcv_to_klines(rows)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: float | None = None,
        quote_qty: float | None = None,
    ) -> dict:
        if order_type.upper() != "MARKET":
            raise ValueError(f"Unsupported order type: {order_type}")

        ccxt_symbol = _to_ccxt_symbol(symbol)
        side = side.upper()

        if side == "BUY":
            if quote_qty is not None:
                return self.exchange.create_order(
                    ccxt_symbol,
                    "market",
                    "buy",
                    None,
                    None,
                    {"quoteOrderQty": quote_qty},
                )
            if quantity is not None:
                return self.exchange.create_market_buy_order(ccxt_symbol, quantity)
            raise ValueError("BUY order requires quote_qty or quantity")

        if quantity is not None:
            return self.exchange.create_market_sell_order(ccxt_symbol, quantity)
        if quote_qty is not None:
            price = self.get_price(symbol)
            return self.exchange.create_market_sell_order(ccxt_symbol, quote_qty / price)
        raise ValueError("SELL order requires quantity or quote_qty")


class PythonBinanceAdapter:
    def __init__(self) -> None:
        self.client = PyBinanceClient(
            BINANCE_API_KEY,
            BINANCE_API_SECRET,
            testnet=PYTHON_BINANCE_TESTNET,
        )
        if BINANCE_BASE_URL:
            self.client.API_URL = f"{BINANCE_BASE_URL.rstrip('/')}/api"

    def get_ticker_24h(self) -> list[dict]:
        return self.client.get_ticker()

    def get_price(self, symbol: str) -> float:
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker.get("price") or 0)

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list]:
        return self.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: float | None = None,
        quote_qty: float | None = None,
    ) -> dict:
        if order_type.upper() != "MARKET":
            raise ValueError(f"Unsupported order type: {order_type}")

        side = side.upper()
        params: dict[str, object] = {
            "symbol": symbol,
            "side": side,
            "type": order_type.upper(),
        }

        if side == "BUY":
            if quote_qty is not None:
                params["quoteOrderQty"] = quote_qty
            elif quantity is not None:
                params["quantity"] = quantity
            else:
                raise ValueError("BUY order requires quote_qty or quantity")
        else:
            if quantity is not None:
                params["quantity"] = quantity
            elif quote_qty is not None:
                price = self.get_price(symbol)
                params["quantity"] = quote_qty / price
            else:
                raise ValueError("SELL order requires quantity or quote_qty")

        return self.client.create_order(**params)


def get_spot_client():
    if EXCHANGE_PROVIDER == "ccxt":
        return CcxtAdapter()
    if EXCHANGE_PROVIDER == "python_binance":
        return PythonBinanceAdapter()
    return BinanceRestAdapter()
