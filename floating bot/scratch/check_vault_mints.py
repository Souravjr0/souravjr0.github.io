import httpx
import base64
from solders.pubkey import Pubkey

async def get_token_account_info(rpc_url: str, account_pubkey: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [account_pubkey, {"encoding": "base64"}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(rpc_url, json=payload)
        res = response.json().get("result")
        if res and res.get("value"):
            data_b64 = res["value"]["data"][0]
            raw = base64.b64decode(data_b64)
            # SPL Token Account Layout:
            # mint: offset 0 (32 bytes)
            # owner: offset 32 (32 bytes)
            # amount: offset 64 (8 bytes)
            mint = Pubkey(raw[0:32])
            owner = Pubkey(raw[32:64])
            amount = int.from_bytes(raw[64:72], byteorder="little", signed=False)
            return {"mint": str(mint), "owner": str(owner), "amount": amount}
    return None

async def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key=1d55b334-5ce2-4cfc-9516-cae621b9d6bb"
    
    # Vaults for 3ucNos4N
    vault0 = "4ct7br2vTPzfdmY3S5HLtTxcGSBfn6pnw98hsS6v359A"
    vault1 = "5it83u57VRrVgc51oNV19TTmAJuffPx5GtGwQr7gQNUo"
    
    print("Checking Vault 0:")
    info0 = await get_token_account_info(rpc_url, vault0)
    if info0:
        print(f"  Mint: {info0['mint']}")
        print(f"  Owner: {info0['owner']}")
        print(f"  Amount: {info0['amount']}")
        
    print("\nChecking Vault 1:")
    info1 = await get_token_account_info(rpc_url, vault1)
    if info1:
        print(f"  Mint: {info1['mint']}")
        print(f"  Owner: {info1['owner']}")
        print(f"  Amount: {info1['amount']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
