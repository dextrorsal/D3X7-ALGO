#!/usr/bin/env python3
"""
Test script for Jupiter account management
"""

import asyncio
import logging
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
sys.path.insert(0, project_root)

from src.trading.jup.account_manager import JupiterAccountManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Check Jupiter account details"""
    try:
        # Initialize account manager with your wallet address
        # Replace with your actual wallet address
        wallet_address = "wgfSHTWx1woRXhsWijj1kcpCP8tmbmK2KnouFVAuoc6"
        
        print("\nChecking Jupiter account details...")
        account_manager = JupiterAccountManager(wallet_address)
        await account_manager.print_account_summary()
        
    except Exception as e:
        logger.error(f"Error checking account: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")