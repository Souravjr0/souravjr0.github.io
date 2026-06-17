with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(1399, min(1445, len(lines))):
    print(f"{idx+1}: {lines[idx].strip()}")
