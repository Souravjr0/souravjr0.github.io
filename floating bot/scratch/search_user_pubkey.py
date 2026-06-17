import os

bot_dir = ".."
for filename in os.listdir(bot_dir):
    if not filename.endswith(".py"):
        continue
    filepath = os.path.join(bot_dir, filename)
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "userPublicKey" in content:
        print(f"[FOUND] {filename} uses userPublicKey")
