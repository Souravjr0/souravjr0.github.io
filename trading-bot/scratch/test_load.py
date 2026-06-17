import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Sourav Biswas\Souravjr0\trading-bot\external\quant\src")))
from quant.config import list_markets, load_market

try:
    slugs = list_markets()
    print("Slugs found:", slugs)
    for slug in slugs:
        try:
            cfg = load_market(slug)
            print(f"Successfully loaded {slug}")
        except Exception as e:
            print(f"Failed to load {slug}:")
            traceback.print_exc()
except Exception as e:
    traceback.print_exc()
