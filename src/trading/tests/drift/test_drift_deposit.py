#!/usr/bin/env python3
"""
Test for depositing SOL into Drift on devnet.
This follows the testing approach from the DriftPy documentation.
"""

import pytest
import asyncio
import logging
import os
from src.trading.devnet.drift_account_manager import DriftAccountManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Make sure we're using devnet
os.environ["DEVNET_RPC_ENDPOINT"] = "https://api.devnet.solana.com"

@pytest.mark.asyncio
async def test_deposit_sol():
    """Test SOL deposit functionality on devnet"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Show initial balances
        logger.info("Initial account state:")
        await manager.show_balances()
        
        # Deposit a small amount of SOL
        amount = 0.01  # 0.01 SOL
        logger.info(f"Depositing {amount} SOL...")
        
        # Execute the deposit
        tx_sig = await manager.deposit_sol(amount)
        logger.info(f"Deposit successful! Tx: {tx_sig}")
        
        # Show updated balances
        logger.info("Updated account state after deposit:")
        await manager.show_balances()
        
        # Verify the deposit was successful
        drift_user = manager.drift_client.get_user()
        final_collateral = drift_user.get_spot_market_asset_value(None, include_open_orders=True)
        
        # Assert that we have some collateral now
        assert final_collateral > 0, "Deposit did not increase collateral"
        
    finally:
        # Clean up
        if manager.drift_client:
            await manager.drift_client.unsubscribe()
            logger.info("Unsubscribed from Drift client")

if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_deposit_sol()) 