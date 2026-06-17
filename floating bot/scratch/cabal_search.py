import os

brain_dir = r"C:\Users\Sourav Biswas\AppData\Local\Temp" # Wait, the app data dir is C:\Users\Sourav Biswas\.gemini\antigravity
# Let's search C:\Users\Sourav Biswas\.gemini\antigravity
for root, dirs, files in os.walk(r"C:\Users\Sourav Biswas\.gemini\antigravity"):
    for file in files:
        if file.endswith(".log") or file.endswith(".txt"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "CABAL DETECTED" in line:
                            print(f"Found in {path}: {line.strip()[:100]}")
                            break
            except Exception:
                pass
