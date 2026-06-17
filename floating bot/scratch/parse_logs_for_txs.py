import os
import sys

# Set standard output encoding to utf-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

log_path = r'C:\Users\Sourav Biswas\.gemini\antigravity\brain\4f1d5fc9-b0d9-4fb3-88f1-f19eaf262712\.system_generated\tasks\task-5128.log'
if not os.path.exists(log_path):
    print("Log file not found!")
    exit(1)

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("Analyzing logs for successful trades...")
for idx, line in enumerate(lines, 1):
    line_clean = line.strip()
    if "[OK]" in line_clean or "Position opened" in line_clean or "sell" in line_clean.lower() or "buy" in line_clean.lower():
        if "HTTP Request" not in line_clean and "Pool Price" not in line_clean:
            # Print safely avoiding encoding errors
            print(f"L{idx}: {line_clean}")
