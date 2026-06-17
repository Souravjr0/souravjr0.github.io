import sqlite3

conn = sqlite3.connect("trades.db")
c = conn.cursor()

# Get all paper trades
c.execute("SELECT * FROM paper_trades ORDER BY timestamp DESC LIMIT 20")
rows = c.fetchall()

# Get column names
c.execute("PRAGMA table_info(paper_trades)")
cols = [col[1] for col in c.fetchall()]

print(f"Paper Trades (last 20, columns: {cols}):")
print("=" * 120)

total_pnl = 0
for r in rows:
    row_dict = dict(zip(cols, r))
    ts = row_dict.get("timestamp", 0)
    direction = row_dict.get("direction", "")
    mint = row_dict.get("mint_address", "")[:12]
    amount_sol = row_dict.get("amount_sol", 0)
    price = row_dict.get("price_sol", 0)
    status = row_dict.get("status", "")
    pnl = row_dict.get("net_pnl_sol", 0)
    
    from datetime import datetime
    time_str = datetime.utcfromtimestamp(ts).strftime('%H:%M:%S') if ts else "?"
    
    print(f"  {time_str} | {direction:<5} | Mint: {mint}... | SOL: {amount_sol:.6f} | Price: {price:.10f} | Status: {status:<8} | PnL: {pnl:+.6f}")
    if pnl:
        total_pnl += pnl

print(f"\nTotal Paper P&L: {total_pnl:+.6f} SOL")
conn.close()
