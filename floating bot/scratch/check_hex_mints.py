from solders.pubkey import Pubkey

wsol = Pubkey.from_string("So11111111111111111111111111111111111111112")
usdc = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

print("WSOL hex:", bytes(wsol).hex())
print("USDC hex:", bytes(usdc).hex())
print("WSOL bytes < USDC bytes:", bytes(wsol) < bytes(usdc))
