import sys
import os
sys.path.insert(0, '.')

try:
    from solders.pubkey import Pubkey
    from spl.token.instructions import close_account, CloseAccountParams
    print("[OK] spl-token imports succeeded!")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
