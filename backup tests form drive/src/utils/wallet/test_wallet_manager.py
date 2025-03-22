"""
Test script for demonstrating WalletManager functionality.
"""

import os
import json
import logging
from pathlib import Path
from wallet_manager import WalletManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize wallet manager
    wallet_manager = WalletManager("config/test_wallets")
    
    # Example: Create test wallets
    test_wallets = [
        ("main_wallet", "/home/dex/.config/solana/id.json", "main_strategy"),
        ("test_wallet", "/home/dex/.config/solana/test.json", "test_strategy"),
    ]
    
    # Add test wallets
    for name, path, strategy in test_wallets:
        if os.path.exists(path):
            success = wallet_manager.add_wallet(name, path, strategy)
            if success:
                logger.info(f"Added wallet: {name}")
            else:
                logger.error(f"Failed to add wallet: {name}")
    
    # List all wallets
    logger.info("\nConfigured wallets:")
    for wallet_info in wallet_manager.list_wallets():
        logger.info(f"- {wallet_info['name']}:")
        logger.info(f"  Public key: {wallet_info['public_key']}")
        logger.info(f"  Strategy: {wallet_info.get('strategy', 'None')}")
        logger.info(f"  Active: {wallet_info['is_active']}")
    
    # Example: Switch between wallets
    if len(wallet_manager.list_wallets()) > 1:
        # Switch to test wallet
        if wallet_manager.switch_wallet("test_wallet"):
            logger.info("\nSwitched to test wallet")
            active_wallet = wallet_manager.get_wallet()
            if active_wallet:
                logger.info(f"Active wallet pubkey: {active_wallet.get_public_key()}")
        
        # Switch back to main wallet
        if wallet_manager.switch_wallet("main_wallet"):
            logger.info("\nSwitched back to main wallet")
            active_wallet = wallet_manager.get_wallet()
            if active_wallet:
                logger.info(f"Active wallet pubkey: {active_wallet.get_public_key()}")

if __name__ == "__main__":
    main() 