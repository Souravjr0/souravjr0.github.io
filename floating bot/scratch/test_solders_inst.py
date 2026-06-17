import sys
import base64
sys.path.insert(0, '.')

try:
    from solders.keypair import Keypair
    from solders.hash import Hash
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from spl.token.instructions import close_account, CloseAccountParams
    
    kp = Keypair()
    
    # 1. Create the spl close instruction
    inst = close_account(
        CloseAccountParams(
            program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
            account=Pubkey.from_string("So11111111111111111111111111111111111111112"), # mock
            dest=kp.pubkey(),
            owner=kp.pubkey(),
        )
    )
    
    # 2. Build signed transaction
    # signature: new_signed_with_payer(instructions, payer, signing_keypairs, recent_blockhash)
    blockhash = Hash.from_string("11111111111111111111111111111111")
    
    # instructions is a list
    tx = Transaction.new_signed_with_payer(
        [inst],
        kp.pubkey(),
        [kp],
        blockhash
    )
    
    # Serialize to base64
    tx_bytes = bytes(tx)
    encoded = base64.b64encode(tx_bytes).decode("utf-8")
    
    print(f"[OK] Successfully built and signed Transaction using solders! Base64: {encoded[:50]}...")
except Exception as e:
    print(f"[ERROR] Solder transaction failed: {e}")
