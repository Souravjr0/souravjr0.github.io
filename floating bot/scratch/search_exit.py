with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "_exit" in line or "os.exit" in line or "sys.exit" in line:
        print(f"Line {i+1}: {line.strip()}")
