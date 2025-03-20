import os
import asyncio
import logging
from src.trading.drift.account_manager import DriftAccountManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_kp_wallet():
    """Test loading and basic functionality of the KP wallet"""
    try:
        # Initialize account manager with KP wallet
        account_manager = DriftAccountManager(wallet_name="KP_TRADE")
        
        # Attempt to load the wallet
        success = await account_manager.load_wallet()
        if not success:
            logger.error("Failed to load KP wallet")
            return False
            
        # Get wallet public key
        pubkey = account_manager.keypair.pubkey()
        logger.info(f"Successfully loaded KP wallet with pubkey: {pubkey}")
        
        # Initialize Drift client
        await account_manager.initialize_client()
        if not account_manager.drift_client:
            logger.error("Failed to initialize Drift client")
            return False
            
        # Get SOL balance
        balance = await account_manager.get_sol_balance()
        logger.info(f"SOL Balance: {balance}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing KP wallet: {e}")
        return False

async def main():
    """Main test function"""
    # Ensure WALLET_PASSWORD is set
    if not os.getenv("WALLET_PASSWORD"):
        logger.error("WALLET_PASSWORD environment variable not set")
        return
        
    success = await test_kp_wallet()
    if success:
        logger.info("KP wallet test completed successfully")
    else:
        logger.error("KP wallet test failed")

if __name__ == "__main__":
    asyncio.run(main()) 