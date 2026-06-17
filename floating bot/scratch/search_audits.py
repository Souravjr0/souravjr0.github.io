with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def _check_rugcheck" in line or "def _check_goplus" in line:
        print(f"Line {i+1}: {line.strip()}")
        # print 20 lines
        for idx in range(i, min(len(lines), i+20)):
            print(f"  {idx+1}: {lines[idx].strip()}")
