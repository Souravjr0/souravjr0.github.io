with open("launch_predictor.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def predict_launch" in line:
        print(f"Line {i+1}: {line.strip()}")
        # print 40 lines
        for idx in range(i, min(len(lines), i+60)):
            print(f"  {idx+1}: {lines[idx].strip()}")
