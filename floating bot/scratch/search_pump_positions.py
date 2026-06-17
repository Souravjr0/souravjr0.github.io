import os

filepath = "../pumpfun_sniper.py"
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "positions" in line:
        # print safely avoiding unicode encoding errors
        print(f"Line {idx+1}: {line.strip()}".encode('ascii', errors='replace').decode('ascii'))
