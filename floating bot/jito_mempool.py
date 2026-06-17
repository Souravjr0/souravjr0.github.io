import asyncio
import logging
import random
from typing import Callable, Dict

logger = logging.getLogger("JitoMempool")

class JitoMempoolMonitor:
    """
    Simulated Jito Block Engine Mempool Monitor.
    In a live production environment, this connects via gRPC to a Jito Block Engine 
    and subscribes to pending transactions. For this simulation, it randomly generates 
    massive dev dumps to trigger the front-running logic.
    """
    def __init__(self):
        self.callbacks: Dict[str, Callable] = {}
        self.running = False
        self.active_mints = set()

    def subscribe(self, mint: str, callback: Callable):
        """Subscribe to pending mempool transactions involving this mint."""
        self.active_mints.add(mint)
        self.callbacks[mint] = callback
        logger.debug(f"[JITO-MEMPOOL] Subscribed to mempool stream for {mint}")

    def unsubscribe(self, mint: str):
        self.active_mints.discard(mint)
        if mint in self.callbacks:
            del self.callbacks[mint]
            
    async def start(self):
        self.running = True
        logger.info("[JITO-MEMPOOL] Connected to Jito Block Engine Mempool (Simulation Stream)")
        
        while self.running:
            await asyncio.sleep(1.0)
            
            # Simulate intercepting a massive Dev Dump bundle 5% of the time for any active mint
            if self.active_mints and random.random() < 0.05:
                target_mint = random.choice(list(self.active_mints))
                cb = self.callbacks.get(target_mint)
                if cb:
                    logger.warning(f"[JITO-MEMPOOL] [!] INTERCEPTED MASSIVE PENDING DEV DUMP TRANSACTION FOR {target_mint} [!]")
                    # Fire the callback immediately so the bot can front-run it
                    await cb(target_mint)

    async def stop(self):
        self.running = False
