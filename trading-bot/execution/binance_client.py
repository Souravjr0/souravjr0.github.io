import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import requests


class BinanceClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str,
        recv_window: int = 5000,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-MBX-APIKEY": api_key})

    def _sign(self, params: dict[str, Any]) -> str:
        query = urllib.parse.urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{query}&signature={signature}"

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        url = f"{self.base_url}{path}"
        method = method.upper()

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            query = self._sign(params)
            if method == "GET":
                response = self.session.get(f"{url}?{query}", timeout=30)
            else:
                response = self.session.request(
                    method,
                    url,
                    data=query,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30,
                )
        else:
            response = self.session.request(method, url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    def get_ticker_24h(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/v3/ticker/24hr")
        return data if isinstance(data, list) else []

    def get_price(self, symbol: str) -> float:
        data = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return float(data["price"])

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list[Any]]:
        params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = int(start_time)
        if end_time is not None:
            params["endTime"] = int(end_time)
        return self._request("GET", "/api/v3/klines", params)

    @staticmethod
    def _format_number(value: float, precision: int = 8) -> str:
        formatted = f"{value:.{precision}f}".rstrip("0").rstrip(".")
        return formatted or "0"

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: float | None = None,
        quote_qty: float | None = None,
    ) -> dict[str, Any]:
        side = side.upper()
        order_type = order_type.upper()
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "newOrderRespType": "RESULT",
        }

        if order_type == "MARKET":
            if side == "BUY":
                if quote_qty is not None:
                    params["quoteOrderQty"] = self._format_number(quote_qty)
                elif quantity is not None:
                    params["quantity"] = self._format_number(quantity)
                else:
                    raise ValueError("BUY order requires quote_qty or quantity")
            else:
                if quantity is not None:
                    params["quantity"] = self._format_number(quantity)
                elif quote_qty is not None:
                    price = self.get_price(symbol)
                    params["quantity"] = self._format_number(quote_qty / price)
                else:
                    raise ValueError("SELL order requires quantity or quote_qty")
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        return self._request("POST", "/api/v3/order", params, signed=True)
