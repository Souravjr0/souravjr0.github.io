import sys
sys.path.insert(0, '.')

try:
    from solders.pubkey import Pubkey
    
    def get_ata_address(wallet: Pubkey, mint: Pubkey) -> Pubkey:
        ata, _ = Pubkey.find_program_address(
            [
                bytes(wallet),
                bytes(Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")),
                bytes(mint),
            ],
            Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"),
        )
        return ata

    wallet = Pubkey.from_string("9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb")
    mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v") # USDC
    ata = get_ata_address(wallet, mint)
    print(f"[OK] Derived ATA address: {ata}")
    # Expected USDC ATA for this wallet: 3X11b... or similar
except Exception as e:
    print(f"[ERROR] ATA derivation failed: {e}")
