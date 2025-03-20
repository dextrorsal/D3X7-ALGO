#!/usr/bin/env python3
"""
Basic example of using the enhanced Drift client manager
"""

import asyncio
import logging
from src.trading.drift.drift_client import DriftClientManager
from src.utils.wallet.sol_rpc import set_network

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Example usage of DriftClientManager"""
    try:
        # Create client manager
        manager = DriftClientManager()
        
        # Set network (devnet or mainnet)
        set_network("devnet")  # Change to mainnet when ready
        
        logger.info("Initializing Drift client...")
        
        # Initialize with default wallet (MAIN)
        drift_client = await manager.initialize()
        
        # Get user information
        user_info = await manager.get_user_info()
        
        # Print account details
        logger.info("\n=== Account Information ===")
        logger.info(f"Spot Collateral: ${user_info['spot_collateral']:,.2f}")
        logger.info(f"Unrealized PnL: ${user_info['unrealized_pnl']:,.2f}")
        logger.info(f"Total Collateral: ${user_info['total_collateral']:,.2f}")
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if 'manager' in locals():
            await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 