import asyncio
import json
import logging
from typing import Callable, Dict
import websockets
from colorama import Fore, Style

logger = logging.getLogger("DevTripwire")

class DevTripwire:
    """
    Predictive Dump Defense.
    Subscribes to the Developer's token account via WebSocket.
    If their token balance decreases (meaning they transferred tokens to a burner
    or sold), the tripwire snaps and triggers an immediate emergency exit.
    """
    def __init__(self, rpc_wss_url: str):
        self.rpc_wss_url = rpc_wss_url
        self.callbacks: Dict[str, Callable] = {}  # token_account -> callback(mint)
        self.mint_map: Dict[str, str] = {}        # token_account -> mint
        self.running = False
        self.ws = None
        self.subscription_ids: Dict[int, str] = {} # sub_id -> token_account
        self._next_id = 1
        self._id_to_account: Dict[int, str] = {} # req_id -> token_account
    def set_tripwire(self, token_account: str, mint: str, callback: Callable):
        """Arm the tripwire on a specific token account."""
        self.callbacks[token_account] = callback
        self.mint_map[token_account] = mint
        
        if self.ws:
            asyncio.create_task(self._subscribe(token_account))
        else:
            logger.info(f"[TRIPWIRE] Queued arming for {token_account[:8]}... (Waiting for WS)")

    def disarm(self, token_account: str):
        """Disarm the tripwire."""
        if token_account in self.callbacks:
            del self.callbacks[token_account]
        if token_account in self.mint_map:
            del self.mint_map[token_account]
            
        # Technically we should unsubscribe via WS here, but closing the connection
        # or ignoring future messages is often sufficient for short-lived snipes.

    async def _subscribe(self, token_account: str):
        """Send the JSON-RPC subscribe message."""
        req_id = self._next_id
        self._next_id += 1
        self._id_to_account[req_id] = token_account
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "accountSubscribe",
            "params": [
                token_account,
                {"encoding": "jsonParsed", "commitment": "confirmed"}
            ]
        }
        try:
            await self.ws.send(json.dumps(payload))
            logger.debug(f"[TRIPWIRE] Subscribed to {token_account}")
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"[TRIPWIRE] Subscribe error: WS closed before sending")
        except Exception as e:
            logger.error(f"[TRIPWIRE] Subscribe error: {e}")

    async def start(self):
        self.running = True
        logger.info(f"{Fore.LIGHTCYAN_EX}[TRIPWIRE]{Style.RESET_ALL} Connecting to {self.rpc_wss_url[:30]}...")
        
        while self.running:
            try:
                async with websockets.connect(self.rpc_wss_url, ping_interval=20, ping_timeout=10) as ws:
                    self.ws = ws
                    logger.info(f"{Fore.GREEN}[TRIPWIRE]{Style.RESET_ALL} Armed and listening.")
                    
                    # Re-subscribe to any queued accounts
                    for account in self.callbacks.keys():
                        await self._subscribe(account)
                        
                    async for message in ws:
                        if not self.running:
                            break
                            
                        data = json.loads(message)
                        
                        # Handle Subscription IDs
                        if "id" in data and "result" in data:
                            sub_id = data["result"]
                            req_id = data["id"]
                            token_account = self._id_to_account.pop(req_id, None)
                            if token_account:
                                self.subscription_ids[sub_id] = token_account
                            continue

                        sub_id = data["params"]["subscription"]
                        token_account = self.subscription_ids.get(sub_id)

                        if token_account and token_account in self.callbacks:
                            account_info = data["params"]["result"]["value"]

                            # A change in state occurred. If balance decreased, it's a dump/transfer.
                            # For safety, any state change on the dev's account triggers the tripwire.
                            mint = self.mint_map.get(token_account)
                            cb = self.callbacks.get(token_account)

                            logger.warning(f"{Fore.RED}{Style.BRIGHT}[TRIPWIRE SNAPPED!]{Style.RESET_ALL} Activity detected on Dev Wallet for {mint}!")

                            if cb and mint:
                                # Fire callback, then disarm
                                await cb(mint)
                                self.disarm(token_account)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[TRIPWIRE] WS closed, reconnecting...")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[TRIPWIRE] WS error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        self.running = False
        if self.ws:
            await self.ws.close()
