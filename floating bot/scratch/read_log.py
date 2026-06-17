import sys
import os

# Force stdout to handle UTF-8/ASCII cleanly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log_path = r"C:\Users\Sourav Biswas\Souravjr0\floating bot\scratch\task_log.temp"
actual_log = r"C:\Users\Sourav Biswas\.gemini\antigravity\brain\4f1d5fc9-b0d9-4fb3-88f1-f19eaf262712\.system_generated\tasks\task-6390.log"

if os.path.exists(actual_log):
    try:
        import shutil
        shutil.copyfile(actual_log, log_path)
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if os.path.exists(log_path):
            os.remove(log_path)
        
        # Filter out noisy HTTP request dumps
        filtered_lines = []
        for line in lines:
            if "HTTP Request:" not in line:
                clean_line = line.encode("ascii", errors="replace").decode("ascii")
                filtered_lines.append(clean_line)
        
        print(f"Total Raw Lines: {len(lines)} | Filtered Lines: {len(filtered_lines)}")
        print("--- LATEST TRADING UPDATES (PATCHED JITO RUN) ---")
        for line in filtered_lines[-40:]:
            sys.stdout.write(line)
            
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Log not found.")
