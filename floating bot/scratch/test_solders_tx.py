import sys
sys.path.insert(0, '.')

try:
    from solders.transaction import Transaction
    import inspect
    print("Transaction constructor:")
    print(inspect.signature(Transaction.__init__))
    print("\nTransaction methods:")
    print([name for name, val in inspect.getmembers(Transaction) if not name.startswith("__")])
except Exception as e:
    print(f"Error: {e}")
