import os
from datetime import datetime
from solders.keypair import Keypair
from dotenv import load_dotenv

def audit_keys():
    print("=== AUDITING PRIVATE KEY & WALLET ===")
    load_dotenv(dotenv_path="../.env")
    pk_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not pk_str:
        print("[-] SOLANA_PRIVATE_KEY not found in .env!")
        return
    
    try:
        kp = Keypair.from_base58_string(pk_str)
        pubkey = str(kp.pubkey())
        print(f"[+] Decoded Public Key from .env: {pubkey}")
        expected_pubkey = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
        if pubkey == expected_pubkey:
            print("[+] SUCCESS: Private key in .env matches your wallet address 9M8yBZ88!")
        else:
            print(f"[!] WARNING: Private key corresponds to a DIFFERENT public key: {pubkey} !!!")
    except Exception as e:
        print(f"[-] Error decoding private key: {e}")

def check_file_modifications():
    print("\n=== FILE MODIFICATION TIMES ===")
    bot_dir = ".."
    for filename in sorted(os.listdir(bot_dir)):
        filepath = os.path.join(bot_dir, filename)
        if os.path.isdir(filepath):
            continue
        mtime = os.path.getmtime(filepath)
        mtime_dt = datetime.fromtimestamp(mtime)
        print(f"  {filename:<25} : {mtime_dt.strftime('%Y-%m-%d %H:%M:%S')} ({os.path.getsize(filepath)} bytes)")

if __name__ == "__main__":
    audit_keys()
    check_file_modifications()
