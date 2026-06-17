import sys
import os
import base64
sys.path.insert(0, '.')

try:
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from spl.token.instructions import close_account, CloseAccountParams
    from solana.transaction import Transaction
    from solders.hash import Hash

    # Mock keypair
    kp = Keypair()
    
    # Construct close instruction
    inst = close_account(
        CloseAccountParams(
            program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
            account=Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"), # dummy
            dest=kp.pubkey(),
            owner=kp.pubkey(),
        )
    )
    
    tx = Transaction()
    tx.add(inst)
    
    # Set dummy blockhash
    tx.recent_blockhash = Hash.from_string("11111111111111111111111111111111")
    
    # Sign transaction
    tx.sign(kp)
    
    # Serialize
    serialized = tx.serialize()
    encoded = base64.b64encode(serialized).decode("utf-8")
    print(f"[OK] Transaction constructed, signed, and serialized! Base64 len: {len(encoded)}")
except Exception as e:
    print(f"[ERROR] Transaction build failed: {e}")
