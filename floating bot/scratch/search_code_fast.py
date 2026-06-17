with open("solana_bot.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "pumpfunsniper" in line.lower() or "dry_run" in line.lower() or "sniper" in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
