import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Sourav Biswas\Souravjr0\trading-bot\external\quant\src")))
from quant.config import load_market

targets = ["aapl"]
cfg = load_market("earnings-beatmiss-A")

for source in cfg.data_sources:
    def search_values(val, path="") -> bool:
        if isinstance(val, str):
            val_lower = val.lower()
            for t in targets:
                if t in val_lower or val_lower in t:
                    print(f"MATCH: target={t}, val={val} at path={path}")
                    return True
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if search_values(item, f"{path}[{i}]"):
                    return True
        elif isinstance(val, dict):
            for k, v in val.items():
                if search_values(k, f"{path}.keys({k})") or search_values(v, f"{path}.{k}"):
                    return True
        return False
    search_values(source.params)
