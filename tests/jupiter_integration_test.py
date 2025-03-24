"""
Test file to verify the new Jupiter structure works correctly.
"""

import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.trading.jup.adapter import JupiterAdapter, SOL_MINT, USDC_MINT

async def test_jupiter_integration():
    """Test the integration of our new Jupiter structure."""
    try:
        logger.info("Initializing JupiterAdapter...")
        adapter = JupiterAdapter(network='mainnet')  # Using mainnet since Jupiter API is mainnet-only
        
        logger.info("Connecting to Jupiter...")
        success = await adapter.connect()
        logger.info(f'Connection success: {success}')
        
        if success:
            # Test quote fetching
            logger.info("Fetching SOL -> USDC quote...")
            quote = await adapter.get_quote(
                input_token=SOL_MINT,
                output_token=USDC_MINT,
                amount=100_000_000  # 0.1 SOL
            )
            logger.info(f'Quote data: {quote}')
            
            if quote:
                # Don't actually execute the swap in test
                logger.info("Quote fetched successfully - swap execution skipped for test")
            
            # Cleanup
            logger.info("Cleaning up...")
            await adapter.cleanup()
            return True
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

async def main():
    """Main test function."""
    success = await test_jupiter_integration()
    print(f"\nTest {'passed' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main()) 