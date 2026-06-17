import os

bot_dir = ".."
files = ["copy_trader.py", "solana_bot.py", "swap_to_usdc.py", "token_sniper.py"]

for filename in files:
    filepath = os.path.join(bot_dir, filename)
    print(f"\n=== INSPECTING JUPITER CALLS IN {filename} ===")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        if any(keyword in line for keyword in ["jup.ag", "quote-api", "swapTransaction", "userPublicKey"]):
            print(f"  Line {idx+1}: {line.strip()}")
