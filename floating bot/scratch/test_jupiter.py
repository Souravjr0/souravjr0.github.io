import asyncio
import httpx

async def main():
    mint = "DZbgq3yE3r41EFszV3XastvyS8j8QnmNT37nsq7sxR66"
    # Or another one: 7JCe3GHwkEr3feHgtLXnmuJ1yB3A7coSeyynxTBgdG8k
    
    async with httpx.AsyncClient() as client:
        # Test 0.0005 SOL
        resp = await client.get(
            "https://api.jup.ag/swap/v1/quote",
            params={
                "inputMint": "So11111111111111111111111111111111111111112",
                "outputMint": mint,
                "amount": "500000",
                "slippageBps": "100"
            }
        )
        print("0.0005 SOL Status:", resp.status_code)
        print("0.0005 SOL Body:", resp.text)

        # Test 0.005 SOL
        resp2 = await client.get(
            "https://api.jup.ag/swap/v1/quote",
            params={
                "inputMint": "So11111111111111111111111111111111111111112",
                "outputMint": mint,
                "amount": "5000000",
                "slippageBps": "100"
            }
        )
        print("0.005 SOL Status:", resp2.status_code)
        print("0.005 SOL Body:", resp2.text)

        # Test 0.01 SOL
        resp3 = await client.get(
            "https://api.jup.ag/swap/v1/quote",
            params={
                "inputMint": "So11111111111111111111111111111111111111112",
                "outputMint": mint,
                "amount": "10000000",
                "slippageBps": "100"
            }
        )
        print("0.01 SOL Status:", resp3.status_code)
        print("0.01 SOL Body:", resp3.text)

asyncio.run(main())
