with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "stop_loss" in line.lower() or "trailing" in line.lower():
        print(f"Line {i+1}: {line.strip()}")
        # print 5 lines
        for idx in range(max(0, i-5), min(len(lines), i+15)):
            print(f"  {idx+1}: {lines[idx].strip()}")
        print("-" * 40)
        break # just get the first one for now
