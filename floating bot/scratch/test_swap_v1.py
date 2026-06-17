import httpx
import asyncio

async def main():
    amount = 362363 
    input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC
    output_mint = "So11111111111111111111111111111111111111112" # SOL
    
    async with httpx.AsyncClient() as client:
        # Quote V1
        q_v1_url = f"https://api.jup.ag/swap/v1/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps=100"
        r_q_v1 = await client.get(q_v1_url)
        print("V1 Quote Status:", r_q_v1.status_code)
        
        if r_q_v1.status_code == 200:
            quote_data = r_q_v1.json()
            wallet = "9M8yBZ881M9Q1ztKcd4sBPm2pi9n24wjGxosqfLuiofb"
            
            # Swap V1
            payload_v1 = {
                "quoteResponse": quote_data,
                "userPublicKey": wallet
            }
            r_s_v1 = await client.post("https://api.jup.ag/swap/v1/swap", json=payload_v1)
            print("V1 Swap Status (userPublicKey):", r_s_v1.status_code)
            print("V1 Swap Response:", r_s_v1.text[:300])

if __name__ == "__main__":
    asyncio.run(main())
