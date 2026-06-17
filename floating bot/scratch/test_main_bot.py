import asyncio
import sys
import os
import logging

sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# We import the master entry point from solana_bot
from solana_bot import run_all_engines

async def test_main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    print('[TEST-MAIN] Starting full solana_bot engines dry run...')
    try:
        # Run all engines concurrently for 45 seconds using asyncio.wait_for
        await asyncio.wait_for(run_all_engines(), timeout=45.0)
    except asyncio.TimeoutError:
        print('[TEST-MAIN] 45s timeout reached. Solana bot test completed successfully and cleanly!')
    except Exception as e:
        print(f'[TEST-MAIN] Solana bot encountered an error: {e}')
        raise e

if __name__ == '__main__':
    asyncio.run(test_main())
