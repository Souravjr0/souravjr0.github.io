import sys
import httpx
import json

def main():
    print("========================================================================")
    print("           QUICKNODE PUMP.FUN / METIS ADD-ON DIAGNOSTIC")
    print("               cook45 & clack // Zero-Latency MEV Systems")
    print("========================================================================")
    
    if len(sys.argv) < 2:
        print("Usage: python scratch/test_quicknode_addon.py <YOUR_QUICKNODE_METIS_URL>")
        print("Example: python scratch/test_quicknode_addon.py https://jupiter-swap-api.quiknode.pro/38e6fb2d-your-endpoint-key/")
        sys.exit(1)
        
    metis_url = sys.argv[1].strip()
    if not metis_url.endswith("/"):
        metis_url += "/"
        
    # Standard test mint (SOL/WIF or active pump mint)
    test_mint = "AgWxFGwpZcKAZ9oV3rd2MW9q61KSjgsmnRvykEmzpump"
    quote_url = f"{metis_url}pump-fun/quote"
    
    print(f"\n[1/2] Sending test GET request to Quote API...")
    print(f"URL: {quote_url}")
    
    params = {
        "type": "BUY",
        "mint": test_mint,
        "amount": "1000000"  # 0.001 SOL input in lamports
    }
    
    try:
        resp = httpx.get(quote_url, params=params, timeout=10.0)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print(f"{unicode('⚡', errors='ignore')} [SUCCESS] Quote received successfully!")
            data = resp.json()
            print("Response Data:")
            print(json.dumps(data, indent=2))
        elif resp.status_code == 403:
            print("[-] [FORBIDDEN] This key does not have the Metis / Pump.fun API add-on enabled or active.")
            print(f"Response: {resp.text}")
        elif resp.status_code == 404:
            print("[-] [NOT FOUND] The path /pump-fun/quote was not found on this endpoint.")
            print("Ensure you copied the correct 'Metis - Jupiter Swap API' URL from your QuickNode Add-ons tab.")
        else:
            print(f"[-] [ERROR] Unexpected status code: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        sys.exit(1)
        
    # Test Swap construction endpoint
    swap_url = f"{metis_url}pump-fun/swap"
    print(f"\n[2/2] Testing swap construction endpoint (dry-run request)...")
    print(f"URL: {swap_url}")
    
    payload = {
        "wallet": "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb",
        "type": "BUY",
        "mint": test_mint,
        "inAmount": "1000000" # 0.001 SOL
    }
    
    try:
        resp = httpx.post(swap_url, json=payload, timeout=10.0)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("  [SUCCESS] Serialized swap transaction generated successfully!")
        else:
            print(f"  [-] Response: {resp.text[:150]}")
    except Exception as e:
        print(f"  [-] Connection failed: {e}")
        
    print("\n========================================================================")

if __name__ == "__main__":
    main()
