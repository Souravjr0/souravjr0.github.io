import sqlite3
import os

db_path = "trades.db"
if not os.path.exists(db_path):
    print("Database trades.db does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

print("=========================================")
print("     DATABASE STATISTICS AUDIT")
print("=========================================")

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Table: {table:<20} | Rows: {count:<8}")
        
        # Pull extra details for specific tables
        if table == "launch_predictions":
            cursor.execute("SELECT MIN(heuristic_score), MAX(heuristic_score), AVG(heuristic_score) FROM launch_predictions")
            scores = cursor.fetchone()
            if scores and scores[0] is not None:
                print(f"  -> Heuristic Scores: Min={scores[0]:.1f} | Max={scores[1]:.1f} | Avg={scores[2]:.1f}")
        elif table == "raw_swaps":
            cursor.execute("SELECT COUNT(DISTINCT wallet_address), COUNT(DISTINCT mint_address) FROM raw_swaps")
            wallets, mints = cursor.fetchone()
            print(f"  -> Monitored Activity: Unique Wallets={wallets} | Unique Mints={mints}")
        elif table == "paper_trades":
            cursor.execute("SELECT status, SUM(net_pnl_sol) FROM paper_trades GROUP BY status")
            pnl_rows = cursor.fetchall()
            for pnl in pnl_rows:
                print(f"  -> Status: {pnl[0]:<10} | Cumulative P&L: {pnl[1]:+.6f} SOL")
        elif table == "trades":
            cursor.execute("SELECT status, COUNT(*) FROM trades GROUP BY status")
            status_rows = cursor.fetchall()
            for s in status_rows:
                print(f"  -> Status: {s[0]:<10} | Count: {s[1]}")
    except Exception as e:
        print(f"  Error inspecting {table}: {e}")

conn.close()
