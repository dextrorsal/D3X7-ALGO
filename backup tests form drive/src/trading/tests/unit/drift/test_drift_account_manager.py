import asyncio
import argparse
from src.trading.drift.account_manager import DriftAccountManager

async def test_account_initialization():
    """Test that we can initialize the Drift account manager"""
    manager = DriftAccountManager()
    await manager.setup()
    
    # Check that client is initialized
    assert manager.drift_client is not None
    print("✓ Client initialized successfully")
    
    # Check that we can get user info
    drift_user = manager.drift_client.get_user()
    assert drift_user is not None
    print("✓ User info retrieved successfully")
    
    user = drift_user.get_user_account()
    assert user is not None
    print("✓ User account retrieved successfully")
    
    # Clean up
    await manager.drift_client.unsubscribe()

async def test_show_balances():
    """Test that we can fetch account balances"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Should run without errors
        await manager.show_balances()
        print("✓ Balances shown successfully")
    finally:
        await manager.drift_client.unsubscribe()

async def test_deposit_sol():
    """Test SOL deposit functionality"""
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Get initial balance
        drift_user = manager.drift_client.get_user()
        initial_collateral = drift_user.get_spot_market_asset_value(None, include_open_orders=True)
        print(f"Initial collateral: {initial_collateral}")
        
        # Try small deposit
        amount = 0.1  # 0.1 SOL
        await manager.deposit_sol(amount)
        print(f"Deposited {amount} SOL")
        
        # Check new balance
        drift_user = manager.drift_client.get_user()
        final_collateral = drift_user.get_spot_market_asset_value(None, include_open_orders=True)
        print(f"Final collateral: {final_collateral}")
        
        # Balance should have increased
        assert final_collateral > initial_collateral
        print("✓ Balance increased after deposit")
        
    finally:
        await manager.drift_client.unsubscribe()

async def run_tests(should_deposit=False):
    """Run all tests"""
    print("\nRunning account initialization test...")
    await test_account_initialization()
    
    print("\nRunning show balances test...")
    await test_show_balances()
    
    if should_deposit:
        print("\nRunning deposit SOL test...")
        await test_deposit_sol()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Drift Account Manager")
    parser.add_argument('--deposit', action='store_true', help='Run deposit test (WARNING: Will use real SOL)')
    
    args = parser.parse_args()
    asyncio.run(run_tests(should_deposit=args.deposit)) 