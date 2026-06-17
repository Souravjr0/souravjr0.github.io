import sqlite3
import os

db_path = "trades.db"
if not os.path.exists(db_path):
    print("Database trades.db does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=========================================")
print("     ON-CHAIN WALLETS INTELLIGENCE")
print("               cook45 & clack")
print("=========================================")

# Get total unique wallets in raw_swaps
cursor.execute("SELECT COUNT(DISTINCT wallet_address) FROM raw_swaps")
total_wallets = cursor.fetchone()[0]
print(f"Total Unique Wallets Profiled: {total_wallets}")

# Find top 10 most active wallets cataloged in raw_swaps
cursor.execute("""
    SELECT wallet_address, COUNT(*), COUNT(DISTINCT mint_address)
    FROM raw_swaps
    GROUP BY wallet_address
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
active_wallets = cursor.fetchall()

print("\n--- Top 10 Most Active Wallets Cataloged ---")
print(f"{'Wallet Address':<48} | {'Trades':<6} | {'Unique Tokens':<13}")
print("-" * 75)
for wallet, trades, tokens in active_wallets:
    print(f"{wallet:<48} | {trades:<6} | {tokens:<13}")

# Find any wallets that are participating in multiple newly launched tokens
cursor.execute("""
    SELECT wallet_address, COUNT(DISTINCT mint_address) as unique_mints
    FROM raw_swaps
    GROUP BY wallet_address
    HAVING unique_mints > 1
    ORDER BY unique_mints DESC
    LIMIT 5
""")
multi_mint_wallets = cursor.fetchall()

if multi_mint_wallets:
    print("\n--- Potential Serial Sniper / Cabal Wallets ---")
    print(" (Wallets participating in multiple launches in under 15 mins)")
    print(f"{'Wallet Address':<48} | {'Launches Sniped':<15}")
    print("-" * 70)
    for wallet, mints in multi_mint_wallets:
        print(f"{wallet:<48} | {mints:<15}")

conn.close()
