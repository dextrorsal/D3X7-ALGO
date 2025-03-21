#!/usr/bin/env python3
"""
Test to check available markets on Drift devnet.
"""

import asyncio
import logging
import os
from src.trading.devnet.drift_account_manager import DriftAccountManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Make sure we're using devnet
os.environ["DEVNET_RPC_ENDPOINT"] = "https://api.devnet.solana.com"

async def check_markets():
    """Check available markets on devnet"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Get spot markets
        logger.info("Available Spot Markets:")
        spot_markets = manager.drift_client.get_spot_market_accounts()
        for market in spot_markets:
            logger.info(f"Index: {market.market_index}, Name: {bytes(market.name).decode('utf-8').strip()}, Decimals: {market.decimals}")
        
        # Get perp markets
        logger.info("\nAvailable Perp Markets:")
        perp_markets = manager.drift_client.get_perp_market_accounts()
        for market in perp_markets:
            logger.info(f"Index: {market.market_index}, Name: {bytes(market.name).decode('utf-8').strip()}")
            
    finally:
        # Clean up
        if manager.drift_client:
            await manager.drift_client.unsubscribe()
            logger.info("Unsubscribed from Drift client")

if __name__ == "__main__":
    # Run the test directly
    asyncio.run(check_markets()) 