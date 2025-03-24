#!/usr/bin/env python3
"""
Test script for Jupiter account management using pytest
"""

import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_jupiter_account_details(jupiter_adapter):
    """Test retrieving Jupiter account details"""
    try:
        # Connect to Jupiter (this will initialize a wallet)
        if not jupiter_adapter.connected:
            await jupiter_adapter.connect()
        
        # Get and display account balances
        balances = await jupiter_adapter.get_account_balances()
        
        # Test assertions
        assert balances is not None
        assert isinstance(balances, dict)
        assert len(balances) > 0, "Should have at least one token balance"
        
        # Log balances for debugging
        logger.info("Account Balances:")
        for token, amount in balances.items():
            logger.info(f"{token}: {amount}")
        
        # Test getting market price - use SOL-TEST market for devnet
        sol_price = await jupiter_adapter.get_market_price("SOL-TEST")
        assert sol_price > 0, "SOL price should be positive"
        logger.info(f"SOL-TEST price: {sol_price}")
        
    except Exception as e:
        logger.error(f"Error checking account: {str(e)}")
        pytest.fail(f"Test failed: {str(e)}")