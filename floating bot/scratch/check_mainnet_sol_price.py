import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Fetch from Jupiter Price API
        url = "https://api.jup.ag/price/v2?ids=So11111111111111111111111111111111111111112"
        try:
            response = await client.get(url, timeout=10)
            data = response.json()
            print("Jupiter Price API:")
            print(data)
        except Exception as e:
            print(f"Jupiter API failed: {e}")
            
        # Fetch from Binance API
        url2 = "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"
        try:
            response2 = await client.get(url2, timeout=10)
            data2 = response2.json()
            print("\nBinance Price SOL/USDT:")
            print(data2)
        except Exception as e:
            print(f"Binance API failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
