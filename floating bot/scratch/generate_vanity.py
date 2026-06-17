#!/usr/bin/env python3
"""
Solana Vanity Wallet Address Grinder
cook45 & clack // Systems & MEV

Usage:
    .venv\Scripts\python.exe scratch/generate_vanity.py <PREFIX>

Example:
    .venv\Scripts\python.exe scratch/generate_vanity.py clack
"""

import sys
import time
import threading
from solders.keypair import Keypair

# Base58 check (Solana address charset)
B58_CHARSET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def check_prefix(prefix: str) -> bool:
    for char in prefix:
        if char not in B58_CHARSET:
            return False
    return True

class VanityGrinder:
    def __init__(self, prefix: str, num_threads: int = 4):
        self.prefix = prefix
        self.num_threads = num_threads
        self.stop_event = threading.Event()
        self.total_attempts = 0
        self.lock = threading.Lock()
        self.start_time = 0
        self.found_keypair = None

    def grind_worker(self):
        local_attempts = 0
        while not self.stop_event.is_set():
            kp = Keypair()
            pubkey_str = str(kp.pubkey())
            local_attempts += 1
            
            # Case-sensitive prefix match
            if pubkey_str.startswith(self.prefix):
                self.found_keypair = kp
                self.stop_event.set()
                break
                
            # Log progress periodically
            if local_attempts >= 10000:
                with self.lock:
                    self.total_attempts += local_attempts
                local_attempts = 0

    def start(self):
        if not check_prefix(self.prefix):
            print(f"\n[X] Error: Prefix '{self.prefix}' contains illegal base58 characters!")
            print("Solana addresses cannot contain '0', 'O', 'I', or 'l'.")
            return

        print(f"\n[+] Starting vanity grind for prefix: '{self.prefix}' (Case-Sensitive)")
        print(f"[+] Grinding on {self.num_threads} threads...")
        
        self.start_time = time.time()
        
        threads = []
        for _ in range(self.num_threads):
            t = threading.Thread(target=self.grind_worker)
            t.daemon = True
            t.start()
            threads.append(t)

        try:
            # Monitor progress in main thread
            while not self.stop_event.is_set():
                time.sleep(0.5)
                elapsed = time.time() - self.start_time
                with self.lock:
                    speed = self.total_attempts / elapsed if elapsed > 0 else 0
                print(f"\r-> Attempts: {self.total_attempts:,} | Time: {elapsed:.2f}s | Speed: {speed:.0f} keys/sec", end="", flush=True)
                
            # Wait for threads to clean up
            for t in threads:
                t.join(timeout=1.0)
                
            elapsed = time.time() - self.start_time
            print(f"\n\n[OK] Success! Found matching keypair in {elapsed:.2f} seconds!")
            print(f"     Attempts required: {self.total_attempts:,}")
            print(f"     Public Key:  {self.found_keypair.pubkey()}")
            print(f"     Private Key (base58): {self.found_keypair}")
            
            # Save keypair to file
            filename = f"vanity_{self.prefix}.json"
            with open(filename, "w") as f:
                # Save keypair bytes array
                f.write(str(list(bytes(self.found_keypair))))
            print(f"[+] Keypair bytes saved to {filename}")
            
        except KeyboardInterrupt:
            print("\n[~] Grinding aborted by user.")
            self.stop_event.set()

if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "clack"
    import os
    # Default to 4 threads or CPU count
    num_threads = min(os.cpu_count() or 4, 8)
    grinder = VanityGrinder(prefix, num_threads)
    grinder.start()
