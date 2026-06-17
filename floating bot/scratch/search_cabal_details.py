with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "block 0" in line.lower() or "cabal" in line.lower() or "alpha" in line.lower():
        print(f"Line {i+1}: {line.strip()}")
