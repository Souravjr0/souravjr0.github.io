import httpx
import json

async def main():
    amount = 362363 
    input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC
    output_mint = "So11111111111111111111111111111111111111112" # SOL
    quote_url = f"https://api.jup.ag/swap/v2/quote?inputMint={input_mint}&outputMint={output_mint}&amount={amount}&slippageBps=100"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(quote_url)
        print("Quote Status Code:", resp.status_code)
        print("Quote Response:")
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
