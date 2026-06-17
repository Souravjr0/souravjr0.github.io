import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

log_path = r'C:\Users\Sourav Biswas\.gemini\antigravity\brain\4f1d5fc9-b0d9-4fb3-88f1-f19eaf262712\.system_generated\tasks\task-5128.log'
if not os.path.exists(log_path):
    print("Log file not found!")
    exit(1)

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("Searching for sell, dump, and position exit events in logs...")
for idx, line in enumerate(lines, 1):
    l_lower = line.lower()
    if any(k in l_lower for k in ["sell", "dump", "tripwire", "p&l", "exit", "close", "reclaim"]):
        if "http request" not in l_lower and "pool price" not in l_lower and "multipleaccounts" not in l_lower:
            print(f"L{idx}: {line.strip()}")
