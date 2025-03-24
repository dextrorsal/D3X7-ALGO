"""
Test file to verify the new Drift structure works correctly.
"""

import asyncio
import logging
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exchanges.drift.client import DriftClient
from src.exchanges.drift.auth import DriftAuth
from src.trading.drift.drift_adapter import DriftAdapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_drift_integration():
    """Test the integration of our new Drift structure."""
    try:
        logger.info("Initializing DriftAdapter...")
        adapter = DriftAdapter(network='devnet')
        
        logger.info("Connecting to Drift...")
        success = await adapter.connect()
        logger.info(f'Connection success: {success}')
        
        if success:
            # Test market data
            logger.info("Fetching SOL-PERP position...")
            position = await adapter.get_position('SOL-PERP')
            logger.info(f'Position data: {position}')
            
            # Test market fetching
            logger.info("Fetching available markets...")
            markets = await adapter.client.get_markets()
            logger.info(f'Available markets: {markets}')
            
            # Cleanup
            logger.info("Cleaning up...")
            await adapter.cleanup()
            return True
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

async def main():
    """Main test function."""
    success = await test_drift_integration()
    print(f"\nTest {'passed' if success else 'failed'}")

if __name__ == "__main__":
    asyncio.run(main()) 