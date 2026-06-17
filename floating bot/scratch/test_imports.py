import sys
sys.path.insert(0, '.')

try:
    import solana
    print(f"solana modules: {dir(solana)}")
except Exception as e:
    print(f"Failed to import solana: {e}")

try:
    from solders.transaction import Transaction
    print("solders.transaction.Transaction imported successfully!")
except Exception as e:
    print(f"Failed to import solders.transaction: {e}")
