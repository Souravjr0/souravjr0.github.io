import os

bot_path = "../solana_bot.py"
with open(bot_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

lines = content.splitlines()
print("=== PUMPFUN SNIPER INITIALIZATION IN SOLANA_BOT.PY ===")
for idx, line in enumerate(lines):
    if "PumpFunSniper" in line or "pump_sniper" in line or "max_snipe_sol" in line:
        print(f"Line {idx+1}: {line.strip()}")
