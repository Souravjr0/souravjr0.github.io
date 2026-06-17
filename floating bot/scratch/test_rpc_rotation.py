import asyncio
import httpx
import logging
from colorama import Fore, Style, init

init()
logger = logging.getLogger("SolanaArbBot")
logging.basicConfig(level=logging.INFO, format="%(message)s")

class MockSniper:
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=5.0)
        self.rpc_endpoints = [
            "https://invalid-rpc-node-testing-123.com", # Mock offline node
            "https://api.mainnet-beta.solana.com",      # Backup public node
            "https://rpc.ankr.com/solana"               # Backup 2
        ]
        self.rpc_index = 0

    async def _rpc_call(self, payload: dict, timeout: float = 3.0) -> dict:
        for attempt in range(len(self.rpc_endpoints)):
            url = self.rpc_endpoints[self.rpc_index]
            print(f"Attempt {attempt+1}: Connecting to {url}...")
            try:
                resp = await self.http.post(url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    print(f"{Fore.LIGHTRED_EX}[RPC-429]{Style.RESET_ALL} Node {url} rate-limited. Rotating...")
                else:
                    print(f"[RPC-HTTP-{resp.status_code}] Node {url} error. Rotating...")
            except Exception as e:
                print(f"[RPC-NET-ERROR] Node {url} offline: {e}. Rotating...")
                
            # Rotate
            self.rpc_index = (self.rpc_index + 1) % len(self.rpc_endpoints)
            
        raise Exception("All RPC endpoints failed!")

async def test():
    bot = MockSniper()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSlot"
    }
    try:
        res = await bot._rpc_call(payload)
        print(f"\n[SUCCESS] Result: {res}")
        print(f"Currently active RPC index: {bot.rpc_index} ({bot.rpc_endpoints[bot.rpc_index]})")
    except Exception as e:
        print(f"[FAILED] {e}")
    await bot.http.aclose()

if __name__ == '__main__':
    asyncio.run(test())
