import httpx
import asyncio
import json

async def main():
    amount = 362363 
    input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC
    output_mint = "So11111111111111111111111111111111111111112" # SOL
    quote_url = f"https://api.jup.ag/swap/v2/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps=100"
    
    async with httpx.AsyncClient() as client:
        # Get Quote
        resp = await client.get(quote_url)
        quote_data = resp.json()
        
        wallet = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
        
        # Payload 1: userPublicKey
        print("\n--- Testing with userPublicKey ---")
        payload1 = {
            "quoteResponse": quote_data,
            "userPublicKey": wallet
        }
        r1 = await client.post("https://api.jup.ag/swap/v2/swap", json=payload1)
        print("Status:", r1.status_code)
        print("Response:", r1.text[:300])
        
        # Payload 2: taker
        print("\n--- Testing with taker ---")
        payload2 = {
            "quoteResponse": quote_data,
            "taker": wallet
        }
        r2 = await client.post("https://api.jup.ag/swap/v2/swap", json=payload2)
        print("Status:", r2.status_code)
        print("Response:", r2.text[:300])

if __name__ == "__main__":
    asyncio.run(main())
