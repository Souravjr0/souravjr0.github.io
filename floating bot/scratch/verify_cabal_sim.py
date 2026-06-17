import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(1439, 1454):
    print(f"{idx+1}: {repr(lines[idx])}")
