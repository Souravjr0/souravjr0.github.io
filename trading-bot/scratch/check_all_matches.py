import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Sourav Biswas\Souravjr0\trading-bot\external\quant\src")))
from quant.config import list_markets, load_market

targets = ["btcusdt"]

slugs = list_markets()
for slug in slugs:
    try:
        cfg = load_market(slug)
    except Exception as e:
        print(f"Failed to load {slug}: {e}")
        continue
    
    slug_lower = slug.lower()
    matched = False
    for t in targets:
        if t in slug_lower or slug_lower in t:
            print(f"[SLUG MATCH] {slug} matches {t}")
            matched = True

    if not matched:
        disp_lower = cfg.display_name.lower()
        plat_lower = cfg.platform.lower()
        for t in targets:
            if t in disp_lower or disp_lower in t or t in plat_lower or plat_lower in t:
                print(f"[DISPLAY/PLAT MATCH] {slug} matches {t} (disp: '{disp_lower}', plat: '{plat_lower}')")
                matched = True

    if not matched:
        def search_values(val, path="") -> bool:
            if isinstance(val, str):
                val_lower = val.lower()
                for t in targets:
                    if t in val_lower or val_lower in t:
                        print(f"[DATA MATCH] {slug} matches {t} at params.{path} = '{val}'")
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
            
        for source in cfg.data_sources:
            if search_values(source.params):
                matched = True
                break
