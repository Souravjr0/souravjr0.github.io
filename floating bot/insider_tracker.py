import json
import os
import logging
import random
from typing import Set

logger = logging.getLogger("InsiderTracker")

class InsiderTracker:
    """
    Manages a database of known Cabal / Alpha wallets that are highly profitable at sniping Block 0 launches.
    """

    def __init__(self, db_path: str = "insider_wallets.json", simulation_mode: bool = False):
        self.db_path = db_path
        self.simulation_mode = simulation_mode
        self.cabal_wallets: Set[str] = set()
        self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self.cabal_wallets = set(data.get("wallets", []))
            except Exception as e:
                logger.error(f"[INSIDER-TRACKER] Error loading DB: {e}")

        # Seed mock cabal wallets only in simulation mode to avoid false positives in live trading
        if not self.cabal_wallets and self.simulation_mode:
            self.cabal_wallets = {
                "AlphaWallet111111111111111111111111111111",
                "CabalWhale2222222222222222222222222222222",
                "InsiderGod3333333333333333333333333333",
            }
            self._save_db()

    def _save_db(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({"wallets": list(self.cabal_wallets)}, f, indent=4)
        except Exception as e:
            logger.error(f"[INSIDER-TRACKER] Error saving DB: {e}")

    def add_insider(self, wallet: str):
        if wallet not in self.cabal_wallets:
            self.cabal_wallets.add(wallet)
            self._save_db()
            logger.info(f"[INSIDER-TRACKER] Added new Alpha wallet to Cabal database: {wallet}")

    def is_insider(self, wallet: str) -> bool:
        """Check if a wallet is in the known cabal list."""
        return wallet in self.cabal_wallets

    def simulate_insider_launch(self, payload: dict) -> dict:
        """
        For simulation testing: randomly mutate a standard PumpPortal payload
        to make it look like it was bought by an Insider so we can test the bypass logic.
        (10% chance to mutate)
        """
        if random.random() < 0.50 and self.cabal_wallets:
            payload["traderPublicKey"] = random.choice(list(self.cabal_wallets))
        return payload
