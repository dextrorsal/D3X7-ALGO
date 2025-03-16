#!/usr/bin/env python3
"""
Test script for Drift account manager functionality
"""

import asyncio
import logging
from drift_account_manager import DriftAccountManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Test Drift account manager functionality"""
    try:
        # Initialize account manager
        logger.info("Initializing DriftAccountManager...")
        account_manager = DriftAccountManager()
        
        # Setup the account manager
        logger.info("Setting up DriftAccountManager...")
        await account_manager.setup()
        
        # Check balances
        logger.info("\nChecking account balances...")
        await account_manager.show_balances()
        
    except Exception as e:
        logger.error(f"Error testing account manager: {e}")
        raise
    finally:
        if 'account_manager' in locals() and account_manager.drift_client:
            await account_manager.drift_client.unsubscribe()
            logger.info("Successfully unsubscribed from Drift")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error: {e}")