#!/usr/bin/env python3
"""
Simple script to add a wallet for testing.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.wallet.wallet_manager import WalletManager

async def main():
    """Add a wallet for testing."""
    wallet_manager = WalletManager()
    
    # Add default wallet
    wallet_path = "/home/dex/.config/solana/keys/id.json"
    wallet_manager.add_wallet("DefaultWallet", wallet_path, is_main=True)
    wallet = wallet_manager.get_wallet("DefaultWallet")
    
    if wallet:
        balance = await wallet.get_balance()
        print(f"Added wallet DefaultWallet with address {wallet.pubkey}")
        print(f"Balance: {balance} SOL")
    else:
        print("Failed to add wallet")
    
    await wallet_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 