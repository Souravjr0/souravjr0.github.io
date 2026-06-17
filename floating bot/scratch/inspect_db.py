import sqlite3
import os

db_path = "trades.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("Tables in database:", tables)

for table in tables:
    print(f"\n--- Columns in {table} ---")
    cursor.execute(f"PRAGMA table_info({table});")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")
        
    print(f"\n--- Last 5 entries in {table} ---")
    try:
        cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 5;")
        rows = cursor.fetchall()
        for r in rows:
            print(" ", r)
    except Exception as e:
        print("  Error querying table:", e)

conn.close()
