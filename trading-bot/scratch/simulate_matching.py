import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Sourav Biswas\Souravjr0\trading-bot\external\quant\src")))
from quant.config import list_markets, load_market

os.environ["BOT_TARGET_SYMBOLS"] = "BTCUSDT"

target_str = os.environ.get("BOT_TARGET_SYMBOLS", "").strip()
targets = [t.strip().lower() for t in target_str.split(",") if t.strip()]
print("Targets:", targets)

slugs = list_markets()
filtered_slugs = []
for slug in slugs:
    try:
        cfg = load_market(slug)
        
        # 1. Match slug
        slug_lower = slug.lower()
        matched = False
        for t in targets:
            if t in slug_lower or slug_lower in t:
                print(f"Slug matched: {slug} because '{t}' in '{slug_lower}'")
                matched = True
                break
                
        # 2. Match display name or platform
        if not matched:
            disp_lower = cfg.display_name.lower()
            plat_lower = cfg.platform.lower()
            for t in targets:
                if t in disp_lower or disp_lower in t or t in plat_lower or plat_lower in t:
                    print(f"Disp/Plat matched: {slug} because '{t}' in '{disp_lower}' or '{plat_lower}'")
                    matched = True
                    break
                    
        # 3. Match nested structures in data sources
        if not matched:
            def search_values(val) -> bool:
                if isinstance(val, str):
                    val_lower = val.lower()
                    for t in targets:
                        if t in val_lower or val_lower in t:
                            print(f"Data source value matched in {slug}: '{val_lower}' matches '{t}'")
                            return True
                elif isinstance(val, list):
                    for item in val:
                        if search_values(item):
                            return True
                elif isinstance(val, dict):
                    for k, v in val.items():
                        if search_values(k) or search_values(v):
                            return True
                return False
                
            for source in cfg.data_sources:
                if search_values(source.params):
                    matched = True
                    break
                    
        if matched:
            filtered_slugs.append(slug)
    except Exception as e:
        print(f"Exception for {slug}: {e}")
        filtered_slugs.append(slug)

print("Filtered slugs:", filtered_slugs)
