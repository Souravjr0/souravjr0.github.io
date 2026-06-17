import argparse
import sqlite3
from datetime import datetime, timezone

import requests

from exchange_client import get_spot_client
from config import JOURNAL_DB_PATH


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    lines = [
        "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)),
        "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))))
    return "\n".join(lines)


def _print_section(title: str, headers: list[str], rows: list[list[str]]) -> None:
    print(f"\n{title}")
    print(_format_table(headers, rows))


def _normalize_side(side: str) -> str:
    normalized = side.strip().upper()
    if normalized in {"BUY", "SELL"}:
        return normalized
    raise ValueError("Side must be BUY or SELL")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(JOURNAL_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            fee REAL DEFAULT 0,
            strategy TEXT,
            timeframe TEXT,
            notes TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
    conn.commit()


def get_journal_db() -> sqlite3.Connection:
    conn = _connect()
    _init_db(conn)
    return conn


def _apply_trade(
    positions: dict[str, dict[str, float]],
    symbol: str,
    side: str,
    qty: float,
    price: float,
) -> tuple[float, float]:
    pos = positions.setdefault(symbol, {"qty": 0.0, "cost": 0.0})
    realized = 0.0
    closed_qty = 0.0

    if side == "BUY":
        if pos["qty"] < 0:
            closing_qty = min(qty, abs(pos["qty"]))
            avg_cost = pos["cost"] / pos["qty"] if pos["qty"] else price
            realized = (avg_cost - price) * closing_qty
            pos["cost"] += avg_cost * closing_qty
            pos["qty"] += closing_qty
            closed_qty = closing_qty
            qty -= closing_qty
        if qty > 0:
            pos["cost"] += qty * price
            pos["qty"] += qty
    else:
        if pos["qty"] > 0:
            closing_qty = min(qty, pos["qty"])
            avg_cost = pos["cost"] / pos["qty"] if pos["qty"] else price
            realized = (price - avg_cost) * closing_qty
            pos["cost"] -= avg_cost * closing_qty
            pos["qty"] -= closing_qty
            closed_qty = closing_qty
            qty -= closing_qty
        if qty > 0:
            pos["cost"] -= qty * price
            pos["qty"] -= qty

    return realized, closed_qty


def _compute_trade_stats(rows: list[sqlite3.Row]) -> dict[str, float | int]:
    positions: dict[str, dict[str, float]] = {}
    wins = 0
    losses = 0
    win_sum = 0.0
    loss_sum = 0.0
    gross_pnl = 0.0
    net_pnl = 0.0

    for row in rows:
        side = row["side"]
        symbol = row["symbol"]
        qty = float(row["qty"])
        price = float(row["price"])
        fee = float(row["fee"] or 0.0)

        realized, closed_qty = _apply_trade(positions, symbol, side, qty, price)
        if closed_qty > 0:
            gross_pnl += realized
            net_pnl += realized - fee
            if realized >= 0:
                wins += 1
                win_sum += realized
            else:
                losses += 1
                loss_sum += realized
        else:
            net_pnl -= fee

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    avg_win = win_sum / wins if wins > 0 else 0.0
    avg_loss = abs(loss_sum / losses) if losses > 0 else 0.0

    return {
        "total_trades": len(rows),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def list_recent_trades(limit: int = 10) -> list[dict[str, object]]:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            """
            SELECT ts, symbol, side, qty, price, fee, strategy, timeframe, notes
            FROM trades
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    trades: list[dict[str, object]] = []
    for row in rows:
        trades.append(
            {
                "timestamp": row["ts"],
                "symbol": row["symbol"],
                "side": row["side"],
                "qty": float(row["qty"]),
                "price": float(row["price"]),
                "fee": float(row["fee"] or 0.0),
                "strategy": row["strategy"],
                "timeframe": row["timeframe"],
                "notes": row["notes"],
            }
        )
    return trades


def get_portfolio_summary() -> dict[str, object]:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT ts, symbol, side, qty, price, fee FROM trades ORDER BY ts ASC"
        ).fetchall()

    if not rows:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "open_positions": [],
        }

    stats = _compute_trade_stats(rows)

    positions: dict[str, dict[str, float]] = {}
    for row in rows:
        _apply_trade(
            positions,
            row["symbol"],
            row["side"],
            float(row["qty"]),
            float(row["price"]),
        )

    client = get_spot_client()

    open_positions: list[dict[str, object]] = []
    for symbol, pos in positions.items():
        qty = pos["qty"]
        if qty == 0:
            continue

        avg_cost = pos["cost"] / qty if qty else 0.0
        import socket
        original_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(2.5)
            symbol_upper = symbol.strip().upper()
            is_stock_symbol = False
            # Check standard stock watchlists or short alphabetic tickers
            if len(symbol_upper) <= 5 and symbol_upper.isalpha() and not (symbol_upper.endswith("USDT") or symbol_upper.endswith("BTC") or symbol_upper.endswith("ETH")):
                is_stock_symbol = True

            if is_stock_symbol:
                import yfinance as yf
                ticker = yf.Ticker(symbol_upper)
                df = ticker.history(period="1d")
                if not df.empty:
                    mark = float(df["Close"].iloc[-1])
            else:
                mark = client.get_price(symbol)
        except Exception:
            mark = None
        finally:
            socket.setdefaulttimeout(original_timeout)

        unrealized = None
        unrealized_pct = None
        if mark is not None and avg_cost:
            if qty > 0:
                unrealized = (mark - avg_cost) * qty
                unrealized_pct = (mark - avg_cost) / avg_cost * 100
            else:
                unrealized = (avg_cost - mark) * abs(qty)
                unrealized_pct = (avg_cost - mark) / avg_cost * 100

        open_positions.append(
            {
                "symbol": symbol,
                "qty": qty,
                "entry_price": avg_cost,
                "current_price": mark,
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
            }
        )

    stats["open_positions"] = open_positions
    return stats


def add_trade(args: argparse.Namespace) -> None:
    side = _normalize_side(args.side)
    timestamp = args.timestamp or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        _init_db(conn)
        conn.execute(
            """
            INSERT INTO trades (ts, symbol, side, qty, price, fee, strategy, timeframe, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                args.symbol.upper(),
                side,
                args.qty,
                args.price,
                args.fee,
                args.strategy,
                args.timeframe,
                args.notes,
            ),
        )
        conn.commit()
    print("Trade saved.")


def list_trades(args: argparse.Namespace) -> None:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            """
            SELECT ts, symbol, side, qty, price, fee, strategy, timeframe, notes
            FROM trades
            ORDER BY ts DESC
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()

    if not rows:
        print("No trades recorded.")
        return

    output = [
        [
            row["ts"],
            row["symbol"],
            row["side"],
            f"{row['qty']:.6f}",
            f"{row['price']:.4f}",
            f"{row['fee']:.4f}",
            row["strategy"] or "-",
            row["timeframe"] or "-",
            row["notes"] or "-",
        ]
        for row in rows
    ]
    _print_section(
        f"Last {len(rows)} Trades",
        ["Time", "Symbol", "Side", "Qty", "Price", "Fee", "Strategy", "TF", "Notes"],
        output,
    )


def _compute_positions(rows: list[sqlite3.Row]) -> dict[str, dict[str, float]]:
    positions: dict[str, dict[str, float]] = {}
    for row in rows:
        symbol = row["symbol"]
        side = row["side"]
        qty = float(row["qty"])
        price = float(row["price"])

        if symbol not in positions:
            positions[symbol] = {"qty": 0.0, "cost": 0.0}

        pos = positions[symbol]
        if side == "BUY":
            pos["cost"] += qty * price
            pos["qty"] += qty
        else:
            if pos["qty"] > 0:
                avg_cost = pos["cost"] / pos["qty"] if pos["qty"] else 0
                pos["cost"] -= avg_cost * qty
                pos["qty"] -= qty
            else:
                pos["cost"] -= qty * price
                pos["qty"] -= qty
    return positions


def summary(args: argparse.Namespace) -> None:
    with _connect() as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT ts, symbol, side, qty, price FROM trades ORDER BY ts ASC"
        ).fetchall()

    if not rows:
        print("No trades recorded.")
        return

    positions = _compute_positions(rows)
    client = None
    if args.mark:
        client = get_spot_client()

    output = []
    for symbol, pos in positions.items():
        qty = pos["qty"]
        if qty == 0:
            continue
        avg_cost = pos["cost"] / qty if qty else 0
        mark = None
        if client:
            try:
                mark = client.get_price(symbol)
            except requests.RequestException:
                mark = None
            except ValueError:
                mark = None
        unrealized = None
        if mark is not None:
            if qty > 0:
                unrealized = (mark - avg_cost) * qty
            else:
                unrealized = (avg_cost - mark) * abs(qty)
        output.append(
            [
                symbol,
                f"{qty:.6f}",
                f"{avg_cost:.4f}",
                f"{mark:.4f}" if mark is not None else "n/a",
                f"{unrealized:.2f}" if unrealized is not None else "n/a",
            ]
        )

    if not output:
        print("No open positions.")
        return

    _print_section(
        "Portfolio Summary",
        ["Symbol", "Qty", "Avg Cost", "Mark", "Unrealized PnL"],
        output,
    )


def save_trade(
    symbol: str,
    side: str,
    qty: float,
    price: float,
    fee: float = 0.0,
    strategy: str = None,
    timeframe: str = None,
    notes: str = None,
    timestamp: str = None,
) -> None:
    side = _normalize_side(side)
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        _init_db(conn)
        conn.execute(
            """
            INSERT INTO trades (ts, symbol, side, qty, price, fee, strategy, timeframe, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                symbol.upper(),
                side,
                qty,
                price,
                fee,
                strategy,
                timeframe,
                notes,
            ),
        )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Trade journal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_cmd = subparsers.add_parser("add", help="Add a trade")
    add_cmd.add_argument("--symbol", required=True)
    add_cmd.add_argument("--side", required=True)
    add_cmd.add_argument("--qty", type=float, required=True)
    add_cmd.add_argument("--price", type=float, required=True)
    add_cmd.add_argument("--fee", type=float, default=0.0)
    add_cmd.add_argument("--strategy", default=None)
    add_cmd.add_argument("--timeframe", default=None)
    add_cmd.add_argument("--notes", default=None)
    add_cmd.add_argument("--timestamp", default=None)
    add_cmd.set_defaults(func=add_trade)

    list_cmd = subparsers.add_parser("list", help="List trades")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=list_trades)

    summary_cmd = subparsers.add_parser("summary", help="Portfolio summary")
    summary_cmd.add_argument("--mark", action="store_true", help="Fetch live prices")
    summary_cmd.set_defaults(func=summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
