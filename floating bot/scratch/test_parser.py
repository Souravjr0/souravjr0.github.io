import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "1d55b334-5ce2-4cfc-9516-cae621b9d6bb")
RPC_HTTP = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

IGNORE_TOKENS = {
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn"
}

DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM v4",
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "Raydium CPMM",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpool",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": "Jupiter v4",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "Pump.fun",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap",
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
}

def parse_swap(tx_data, tracked_wallet) -> dict | None:
    meta = tx_data.get("meta", {})
    if not meta or meta.get("err"):
        return None

    tx = tx_data.get("transaction", {})
    message = tx.get("message", {})
    account_keys = [k.get("pubkey") if isinstance(k, dict) else k for k in message.get("accountKeys", [])]
    if not account_keys:
        return None

    pre_balances = meta.get("preTokenBalances", [])
    post_balances = meta.get("postTokenBalances", [])

    token_mint = None
    for b in pre_balances + post_balances:
        mint = b.get("mint")
        if mint and mint not in IGNORE_TOKENS:
            token_mint = mint
            break

    if not token_mint:
        return None

    account_owners = {}
    for b in pre_balances + post_balances:
        idx = b.get("accountIndex")
        owner = b.get("owner")
        if idx is not None and owner:
            account_owners[idx] = owner

    tracked_wallet_involved = False
    for idx, pubkey in enumerate(account_keys):
        if pubkey == tracked_wallet:
            tracked_wallet_involved = True
            
    for idx, owner in account_owners.items():
        if owner == tracked_wallet:
            tracked_wallet_involved = True

    if not tracked_wallet_involved:
        return None

    # Target owners should only consist of the tracked_wallet and its owner if it's a token account
    target_owners = {tracked_wallet}
    for idx, pubkey in enumerate(account_keys):
        if pubkey == tracked_wallet:
            owner = account_owners.get(idx)
            if owner:
                target_owners.add(owner)

    pre_amount = 0.0
    post_amount = 0.0

    for b in pre_balances:
        if b.get("mint") == token_mint:
            owner = b.get("owner")
            idx = b.get("accountIndex")
            token_account_pubkey = account_keys[idx] if idx < len(account_keys) else None
            if owner in target_owners or token_account_pubkey == tracked_wallet:
                pre_amount += float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)

    for b in post_balances:
        if b.get("mint") == token_mint:
            owner = b.get("owner")
            idx = b.get("accountIndex")
            token_account_pubkey = account_keys[idx] if idx < len(account_keys) else None
            if owner in target_owners or token_account_pubkey == tracked_wallet:
                post_amount += float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)

    change = post_amount - pre_amount
    
    if change > 0:
        trade_type = "buy"
    elif change < 0:
        trade_type = "sell"
    else:
        return None

    dex_found = "unknown"
    for pid in account_keys:
        if pid in DEX_PROGRAMS:
            dex_found = DEX_PROGRAMS[pid]
            break

    return {
        "type": trade_type,
        "dex": dex_found,
        "token_mint": token_mint,
        "amount": abs(change),
    }

async def main():
    wallet = "CEmeuuZtpfUaoacsneX8yXyuZnaX4tiPNdhXR8zpGMHG"
    
    # Load from tx_example.json
    if os.path.exists("scratch/tx_example.json"):
        with open("scratch/tx_example.json", "r") as f:
            tx_data = json.load(f)
            res = parse_swap(tx_data, wallet)
            print("tx_example.json swap info:", res)

    # Let's test the other signatures from the previous run
    async with httpx.AsyncClient() as client:
        sigs = [
            '2a7PMFau7M8u8tK5JLeEuLTkGAS44dtJWyuaccuMuQiYK5z2ePojVaKbv1GKo73qrdFBnaV8bJzWLU5VgSbaAEti',
            '3Q6w1R96pxDVNozcToRzzM7aQZZ6sQdbfjc6j2Pytykf5SPMg2ccaiNysyuHir96eMRnZX5g9K143gNU3hD2aLWC',
            '5mSbhqmMP7EjqfkYUYUraMynujm2mFCDK97cBSugEYpf4zcqM5e68syynCvhhppK2Jk6wU5EGJPSJP5ZrM48Arc4'
        ]
        for sig in sigs:
            payload_tx = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            tx_resp = await client.post(RPC_HTTP, json=payload_tx, timeout=10.0)
            tx_data = tx_resp.json().get("result")
            if tx_data:
                res = parse_swap(tx_data, wallet)
                print(f"Sig {sig[:10]}... swap info: {res}")

asyncio.run(main())
