#!/usr/bin/env python3
"""
Dynamic On-Chain Cabal Hunt & Wallet Profiling Utility
cook45 & clack // Systems & MEV

Features:
1. Robust Sliding-Window Timestamp Clustering (Bypasses NULL slots from RPC streams).
2. Identifies wallets buying within a 2.5-second window of early genesis launches.
3. Scores snipers by frequency and flags multi-token serial snipers.
4. Automatically updates trades.db (wallets_intel, wallet_clusters) and insider_wallets.json.
"""

import os
import json
import sqlite3
import time
from typing import Dict, List, Set, Tuple
from colorama import Fore, Style, init

init(autoreset=True)

DB_PATH = "trades.db"
INSIDER_DB = "insider_wallets.json"

def hunt_cabals():
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================")
    print(f"{Fore.MAGENTA}          CABAL HUNTER - ON-CHAIN AUDIT          ")
    print(f"{Fore.MAGENTA}                  cook45 & clack                  ")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}==================================================\n")

    if not os.path.exists(DB_PATH):
        print(f"{Fore.RED}[X] SQLite Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fetch all BUY swaps sorted by token and timestamp
    cursor.execute("""
        SELECT wallet_address, mint_address, amount_sol, timestamp, signature
        FROM raw_swaps
        WHERE direction = 'BUY' AND mint_address IS NOT NULL AND mint_address != ''
        ORDER BY mint_address, timestamp ASC
    """)
    buys = cursor.fetchall()
    print(f"[+] Loaded {len(buys)} raw buy transactions from database.")

    # Group buys by token
    token_buys: Dict[str, List[dict]] = {}
    for wallet, mint, sol, ts, sig in buys:
        if mint not in token_buys:
            token_buys[mint] = []
        token_buys[mint].append({
            "wallet": wallet,
            "sol": sol,
            "timestamp": ts,
            "signature": sig
        })

    # 2. Timing similarity sliding window (2.5 seconds delta for genesis sniping)
    clusters_detected = []
    wallet_snipe_counts: Dict[str, Set[str]] = {} # wallet -> set of token mints

    print(f"[+] Scanning {len(token_buys)} unique token launches...")
    
    for mint, buys_list in token_buys.items():
        if len(buys_list) < 2:
            continue
            
        # The earliest recorded buy represents genesis entry time
        genesis_time = buys_list[0]["timestamp"]
        
        # We only care about frontrunning snipers buying within the first 10 seconds of launch
        early_buys = [b for b in buys_list if b["timestamp"] <= genesis_time + 10.0]
        if len(early_buys) < 2:
            continue

        # Group early buys into sliding timing windows (delta <= 2.5 seconds)
        for i, anchor in enumerate(early_buys):
            window_wallets = []
            window_details = []
            
            for b in early_buys[i:]:
                if b["timestamp"] - anchor["timestamp"] <= 2.5:
                    if b["wallet"] not in window_wallets:
                        window_wallets.append(b["wallet"])
                        window_details.append(b)
                else:
                    break
                    
            if len(window_wallets) >= 2:
                # Timing cluster found!
                cluster_id = f"cabal_ts_{mint[:6]}_{int(anchor['timestamp'])}"
                
                # Track statistics
                for w in window_wallets:
                    if w not in wallet_snipe_counts:
                        wallet_snipe_counts[w] = set()
                    wallet_snipe_counts[w].add(mint)
                
                # Check if this cluster is already recorded or highly overlapping
                overlap = False
                for c in clusters_detected:
                    if c["mint"] == mint and set(c["wallets"]) == set(window_wallets):
                        overlap = True
                        break
                        
                if not overlap:
                    cabal_score = 50.0 + min(len(window_wallets) * 10, 50.0) # Up to 100 max
                    clusters_detected.append({
                        "cluster_id": cluster_id,
                        "mint": mint,
                        "wallets": window_wallets,
                        "timestamp": anchor["timestamp"],
                        "cabal_score": cabal_score,
                        "details": window_details
                    })

    print(f"[OK] Found {len(clusters_detected)} timing-cabal clusters across launches.")

    # 3. Save clusters to SQLite database
    print("\n[+] Updating SQLite Intelligence Database...")
    for cluster in clusters_detected:
        cluster_id = cluster["cluster_id"]
        wallets_json = json.dumps(cluster["wallets"])
        
        # Insert into wallet_clusters
        cursor.execute("""
            INSERT OR REPLACE INTO wallet_clusters (cluster_id, wallets, creation_time, cabal_score, associated_token)
            VALUES (?, ?, ?, ?, ?)
        """, (cluster_id, wallets_json, cluster["timestamp"], cluster["cabal_score"], cluster["mint"]))
        
        # Link wallets to cluster
        for w in cluster["wallets"]:
            cursor.execute("""
                INSERT OR REPLACE INTO wallets_intel (wallet_address, cluster_id, first_seen, total_trades, wallet_score)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET 
                    cluster_id = excluded.cluster_id,
                    total_trades = total_trades + 1,
                    wallet_score = MAX(wallet_score, excluded.wallet_score)
            """, (w, cluster_id, cluster["timestamp"], len(wallet_snipe_counts.get(w, [])), cluster["cabal_score"]))

    conn.commit()

    # 4. Filter Serial Snipers (wallets sniped 2 or more distinct launches)
    serial_snipers = []
    for w, mints in wallet_snipe_counts.items():
        if len(mints) >= 2:
            serial_snipers.append((w, len(mints)))
            
    serial_snipers.sort(key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 65)
    print(f"      HUNTED DOWN HIGH-FIDELITY SERIAL SNIPERS ({len(serial_snipers)} WALLETS)")
    print("=" * 65)
    print(f"{'Wallet Address':<48} | {'Launches Sniped':<15}")
    print("-" * 65)
    
    hunted_list = []
    for wallet, count in serial_snipers:
        hunted_list.append(wallet)
        print(f"{Fore.GREEN}{wallet:<48}{Style.RESET_ALL} | {Fore.LIGHTCYAN_EX}{count:<15}{Style.RESET_ALL}")
    print("=" * 65)

    # 5. Append new serial snipers to insider_wallets.json
    if os.path.exists(INSIDER_DB):
        try:
            with open(INSIDER_DB, "r") as f:
                insider_data = json.load(f)
        except Exception:
            insider_data = {"wallets": []}
    else:
        insider_data = {"wallets": []}

    current_wallets = set(insider_data.get("wallets", []))
    new_added = 0
    for w in hunted_list:
        if w not in current_wallets:
            insider_data["wallets"].append(w)
            new_added += 1

    if new_added > 0:
        with open(INSIDER_DB, "w") as f:
            json.dump(insider_data, f, indent=4)
        print(f"\n[OK] Automatically appended {new_added} newly hunted Alpha/Cabal wallets to {INSIDER_DB}!")
    else:
        print("\n[~] No new wallets added to insider list (all already cataloged).")

    conn.close()

if __name__ == "__main__":
    hunt_cabals()
