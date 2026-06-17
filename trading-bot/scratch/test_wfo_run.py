import sys
import os

project_root = r"C:\Users\Sourav Biswas\Souravjr0\trading-bot"
for folder in ["core", "models", "execution", "discovery", "utils"]:
    sys.path.append(os.path.join(project_root, folder))
sys.path.append(project_root)

import pandas as pd
import unified_analyzer
import wfo_engine

print("Fetching data...")
df = unified_analyzer.fetch_data_unified("BTCUSDT", "1d", 252)
print("Data shape:", df.shape)
if df.empty:
    print("DataFrame is empty!")
else:
    print("Columns:", df.columns)
    print("Running WFO optimization...")
    res = wfo_engine.run_wfo_optimization(df)
    print("Result:", res)
