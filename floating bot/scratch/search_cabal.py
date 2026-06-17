with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "shadow_copy" in line or "is_shadow" in line or "_execute_jito_buy" in line:
        print(f"Line {i+1}: {line.strip()}")
        # print 5 lines before and after
        start = max(0, i-10)
        end = min(len(lines), i+10)
        for idx in range(start, end):
            print(f"  {idx+1}: {lines[idx].strip()}")
        print("-" * 40)
