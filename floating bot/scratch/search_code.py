import os

for root, dirs, files in os.walk("."):
    if ".venv" in root or "__pycache__" in root or ".git" in root or ".gemini" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if "insufficient SOL" in line or "insufficient_sol" in line:
                            print(f"{path}:{line_no}: {line.strip()}")
            except Exception as e:
                pass
