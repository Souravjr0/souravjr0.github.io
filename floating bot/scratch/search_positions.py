import os

bot_dir = ".."
files = ["solana_bot.py", "pumpfun_sniper.py"]

for filename in files:
    filepath = os.path.join(bot_dir, filename)
    print(f"\n=== SEARCHING POSITIONS IN {filename} ===")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "recover" in line.lower() or "active_positions" in line or "max_concurrent" in line:
            print(f"  Line {idx+1}: {line.strip()}")
