import os
import json
import base64
import logging
from typing import Optional, List
import httpx
from colorama import Fore, Style

logger = logging.getLogger("JitoBundle")

JITO_BLOCK_ENGINE_URL = "https://tokyo.mainnet.block-engine.jito.wtf/api/v1/bundles"
# Randomly select one of Jito's Tip Accounts
JITO_TIP_ACCOUNTS = [
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jcyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt"
]

class JitoBundleEngine:
    """
    Submits transactions via Jito Bundles to bypass standard RPC congestion
    and guarantee execution order (Delivery Dominance).
    """
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.http = httpx.AsyncClient(timeout=10.0)

    async def submit_bundle(self, signed_tx_base58_list: List[str]) -> Optional[str]:
        """
        Submit a list of base58-encoded signed transactions as a Jito Bundle.
        In production, the final transaction in the list must be a SOL transfer
        to one of the Jito Tip Accounts.
        """
        if self.dry_run:
            logger.info(f"{Fore.MAGENTA}{Style.BRIGHT}[JITO BUNDLE]{Style.RESET_ALL} (DRY RUN) Simulated submission of {len(signed_tx_base58_list)} TXs to Block Engine.")
            return "simulated_bundle_uuid"

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendBundle",
                "params": [
                    signed_tx_base58_list
                ]
            }

            resp = await self.http.post(
                JITO_BLOCK_ENGINE_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    bundle_uuid = data["result"]
                    logger.info(f"{Fore.MAGENTA}{Style.BRIGHT}[JITO BUNDLE SUCCESS]{Style.RESET_ALL} UUID: {bundle_uuid}")
                    return bundle_uuid
                else:
                    logger.error(f"[JITO BUNDLE ERROR] {data.get('error')}")
                    return None
            else:
                logger.error(f"[JITO HTTP ERROR] {resp.status_code} - {resp.text}")
                return None

        except Exception as e:
            logger.error(f"[JITO BUNDLE EXCEPTION] {e}")
            return None
