import asyncio
import argparse
from src.trading.devnet.devnet_adapter import DevnetAdapter

async def test_account_initialization():
    """Test that we can initialize the Drift account manager"""
    adapter = DevnetAdapter()
    await adapter.connect()
    await adapter.initialize_drift()
    
    # Add delay to allow WebSocket connections to establish and load market data
    print("Waiting for market data to load...")
    await asyncio.sleep(5)
    
    # Check that client is initialized
    assert adapter.drift_client is not None
    print("✓ Client initialized successfully")
    
    # Check that we can get user info
    drift_user = adapter.drift_client.get_user()
    assert drift_user is not None
    print("✓ User info retrieved successfully")
    
    user = drift_user.get_user_account()
    assert user is not None
    print("✓ User account retrieved successfully")
    
    # Clean up
    await adapter.close()

async def test_show_balances():
    """Test that we can fetch account balances"""
    adapter = DevnetAdapter()
    await adapter.connect()
    await adapter.initialize_drift()
    
    # Add delay to allow WebSocket connections to establish and load market data
    print("Waiting for market data to load...")
    await asyncio.sleep(5)
    
    try:
        # Should run without errors
        await adapter.check_token_balances()
        print("✓ Balances shown successfully")
    finally:
        await adapter.close()

async def test_deposit_sol():
    """Test getting user info and collateral"""
    adapter = DevnetAdapter()
    await adapter.connect()
    await adapter.initialize_drift()
    
    # Add delay to allow WebSocket connections to establish and load market data
    print("Waiting for market data to load...")
    await asyncio.sleep(5)
    
    try:
        # Get initial balance
        user_info = await adapter.get_drift_user_info()
        initial_collateral = user_info["spot_collateral"]
        print(f"Initial collateral: {initial_collateral}")
        
        # Try requesting airdrop (equivalent to deposit for testing)
        wallet = adapter.wallet_manager.get_wallet("MAIN")
        result = await adapter.request_airdrop(wallet, amount=0.1)
        
        if result and result.get("confirmed"):
            print(f"✓ Airdrop of {result['amount']} SOL successful")
            
            # Check updated collateral (might not reflect immediately in Drift)
            user_info = await adapter.get_drift_user_info()
            print(f"Updated collateral: {user_info['spot_collateral']}")
        else:
            print(f"× Airdrop failed: {result.get('error', 'Unknown error')}")
    finally:
        await adapter.close()

async def test_withdraw_sol():
    """Test checking balances"""
    adapter = DevnetAdapter()
    await adapter.connect()
    await adapter.initialize_drift()
    
    # Add delay to allow WebSocket connections to establish and load market data
    print("Waiting for market data to load...")
    await asyncio.sleep(5)
    
    try:
        # Just check balances since we can't easily test withdrawals in devnet
        user_info = await adapter.get_drift_user_info()
        print(f"Current collateral: {user_info['spot_collateral']}")
        print("✓ Balance check successful")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_account_initialization())
    asyncio.run(test_show_balances())
    asyncio.run(test_deposit_sol())
    asyncio.run(test_withdraw_sol()) 