import os

bot_path = "../solana_bot.py"
with open(bot_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Print first 150 lines or lines containing config
print("=== CONFIGURATION IN SOLANA_BOT.PY ===")
lines = content.splitlines()
for idx, line in enumerate(lines[:120]):
    print(f"Line {idx+1}: {line}")
