import time
import os
import sys
import shutil

# Force UTF-8 terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import glob

def get_latest_log():
    log_dir = r"C:\Users\Sourav Biswas\.gemini\antigravity\brain\4f1d5fc9-b0d9-4fb3-88f1-f19eaf262712\.system_generated\tasks"
    log_files = glob.glob(os.path.join(log_dir, "task-*.log"))
    if not log_files:
        return None
    # Sort by modification time
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]

actual_log = get_latest_log()
temp_log = r"C:\Users\Sourav Biswas\Souravjr0\floating bot\scratch\live_tail.temp"

if not actual_log or not os.path.exists(actual_log):
    print(f"Error: No active task log files found in the system task directory.")
    print("Is the bot daemon running?")
    sys.exit(1)

print(f" -> Found active stream target: {os.path.basename(actual_log)}")

print("========================================================================")
print("             SOLANA Sniping Daemon - REAL-TIME LIVE MONITOR")
print("               cook45 & clack // Zero-Latency MEV Systems")
print("========================================================================")
print(" -> Press Ctrl+C to exit monitor (will not stop the bot daemon)")
print(" -> Filtering out HTTP noise. Showing clean trading activity...\n")

last_seen_lines = 0

def copy_and_read():
    try:
        shutil.copyfile(actual_log, temp_log)
        with open(temp_log, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if os.path.exists(temp_log):
            os.remove(temp_log)
        return lines
    except Exception:
        return []

# Initial catch-up
lines = copy_and_read()
filtered_lines = [l for l in lines if "HTTP Request:" not in l]
for line in filtered_lines[-30:]:
    sys.stdout.write(line)
last_seen_lines = len(lines)

try:
    while True:
        time.sleep(1.0)
        lines = copy_and_read()
        if len(lines) > last_seen_lines:
            new_lines = lines[last_seen_lines:]
            for line in new_lines:
                if "HTTP Request:" not in line:
                    sys.stdout.write(line)
                    sys.stdout.flush()
            last_seen_lines = len(lines)
except KeyboardInterrupt:
    print("\n[MONITOR] Stopped live tail. The bot remains running safely in the background.")
    if os.path.exists(temp_log):
        try:
            os.remove(temp_log)
        except Exception:
            pass
