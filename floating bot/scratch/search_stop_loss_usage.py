with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "stop_loss_pct" in line and "self.stop_loss_pct" not in line:
        print(f"Line {i+1}: {line.strip()}")
    elif "stop_loss" in line.lower() and i > 1500:
        print(f"Line {i+1}: {line.strip()}")
        # print 5 lines before and after
        for idx in range(max(0, i-5), min(len(lines), i+10)):
            print(f"  {idx+1}: {lines[idx].strip()}")
        print("-" * 40)
