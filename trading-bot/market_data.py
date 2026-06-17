import time

import pandas as pd

KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trade_count",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]


def klines_to_dataframe(klines: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(klines, columns=KLINE_COLUMNS)
    if df.empty:
        return df
    numeric_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base",
        "taker_buy_quote",
    ]
    for col in numeric_cols:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df["trade_count"] = df["trade_count"].astype(int)
    return df


def fetch_klines(client, symbol: str, interval: str, bars: int) -> list[list]:
    bars = max(int(bars), 1)
    klines: list[list] = []
    start_time = None

    while len(klines) < bars:
        batch_limit = min(1000, bars - len(klines))
        batch = client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=batch_limit,
            start_time=start_time,
        )
        if not batch:
            break
        if klines and batch[0][0] == klines[-1][0]:
            batch = batch[1:]
        klines.extend(batch)
        start_time = klines[-1][0] + 1
        if len(batch) < batch_limit:
            break
        time.sleep(0.2)

    return klines
