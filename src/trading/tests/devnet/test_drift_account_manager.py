import pytest
import asyncio
from src.trading.drift.account_manager import DriftAccountManager

@pytest.mark.asyncio
async def test_account_initialization():
    """Test that we can initialize the Drift account manager"""
    manager = DriftAccountManager()
    await manager.setup()
    
    # Check that client is initialized
    assert manager.drift_client is not None
    
    # Check that we can get user info
    drift_user = manager.drift_client.get_user()
    assert drift_user is not None
    
    user = drift_user.get_user_account()
    assert user is not None
    
    # Clean up
    await manager.drift_client.unsubscribe()

@pytest.mark.asyncio
async def test_show_balances():
    """Test that we can fetch account balances"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Should run without errors
        await manager.show_balances()
    finally:
        await manager.drift_client.unsubscribe()

@pytest.mark.asyncio
async def test_deposit_sol():
    """Test SOL deposit functionality"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Get initial balance
        drift_user = manager.drift_client.get_user()
        initial_collateral = drift_user.get_spot_market_asset_value(None, include_open_orders=True)
        
        # Try small deposit
        amount = 0.1  # 0.1 SOL
        await manager.deposit_sol(amount)
        
        # Check new balance
        drift_user = manager.drift_client.get_user()
        final_collateral = drift_user.get_spot_market_asset_value(None, include_open_orders=True)
        
        # Balance should have increased
        assert final_collateral > initial_collateral
        
    finally:
        await manager.drift_client.unsubscribe()

if __name__ == "__main__":
    asyncio.run(pytest.main([__file__])) 