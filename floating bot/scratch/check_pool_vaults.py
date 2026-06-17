import httpx
import base64
from solders.pubkey import Pubkey

async def get_vault_balances(rpc_url: str, vault_pubkey: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountBalance",
        "params": [vault_pubkey]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result")
        if res and res.get("value"):
            return res["value"]
    return None

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    pools = {
        "CYbD9RaToYMtWKA7QZyoLahnHdWq553Vm62Lh6qWtuxq": "Raydium CLMM (small)",
        "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv": "Raydium CLMM (massive)"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [list(pools.keys()), {"encoding": "base64"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        value = response.json()["result"]["value"]
        
        for idx, val in enumerate(value):
            pool_id = list(pools.keys())[idx]
            name = pools[pool_id]
            raw = base64.b64decode(val["data"][0])
            
            # token_vault_0: 137 (32 bytes)
            # token_vault_1: 169 (32 bytes)
            vault0 = Pubkey(raw[137:137+32])
            vault1 = Pubkey(raw[169:169+32])
            
            print(f"Pool: {pool_id} ({name})")
            print(f"  Vault 0: {vault0}")
            print(f"  Vault 1: {vault1}")
            
            bal0 = await get_vault_balances(rpc_url, str(vault0))
            bal1 = await get_vault_balances(rpc_url, str(vault1))
            
            if bal0 and bal1:
                amount0 = float(bal0["amount"]) / (10**bal0["decimals"])
                amount1 = float(bal1["amount"]) / (10**bal1["decimals"])
                print(f"  Vault 0 Balance: {amount0:,.4f} (decimals: {bal0['decimals']})")
                print(f"  Vault 1 Balance: {amount1:,.4f} (decimals: {bal1['decimals']})")
                if amount0 > 0:
                    print(f"  Ratio (Vault 1 / Vault 0): {amount1 / amount0:,.4f}")
                    print(f"  Ratio (Vault 0 / Vault 1): {amount0 / amount1:,.4f}")
            else:
                print("  Failed to retrieve vault balances.")
            print("-" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
