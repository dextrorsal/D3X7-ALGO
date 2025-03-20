#!/usr/bin/env python3
"""
Test script to set up ag_trade wallet's subaccount on Devnet.
This will initialize the wallet, create a subaccount, and verify it's working.
"""

import asyncio
import logging
import os
import json
from typing import Optional

from driftpy.drift_client import DriftClient
from driftpy.accounts import get_perp_market_account, get_spot_market_account
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.types import TxParams
from anchorpy.provider import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from src.trading.devnet.drift_auth import DriftHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class AgTradeSetup:
    def __init__(self):
        self.drift_helper = DriftHelper()
        self.drift_client = None
        self.keypair = None
        
    async def load_ag_trade_wallet(self):
        """Load the ag_trade wallet keypair"""
        try:
            # Load ag_trade keypair from the config directory
            keypair_path = os.path.expanduser("~/.config/ultimate_data_fetcher/ag_trade.json")
            if not os.path.exists(keypair_path):
                raise FileNotFoundError(f"ag_trade keypair not found at {keypair_path}")
            
            with open(keypair_path, 'r') as f:
                keypair_data = json.load(f)
                self.keypair = Keypair.from_bytes(bytes(keypair_data))
            
            logger.info(f"Successfully loaded ag_trade wallet: {self.keypair.pubkey()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ag_trade wallet: {e}")
            return False
    
    async def initialize_drift_client(self):
        """Initialize Drift client with ag_trade wallet"""
        try:
            # Initialize RPC client (devnet)
            rpc_client = AsyncClient("https://api.devnet.solana.com")
            provider = Provider(rpc_client, Wallet(self.keypair))
            
            # Initialize Drift client
            self.drift_client = await DriftClient.create(
                provider,
                use_mainnet=False  # Use devnet
            )
            
            logger.info("Successfully initialized Drift client for ag_trade wallet")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Drift client: {e}")
            return False
    
    async def create_subaccount(self, subaccount_id: int = 0):
        """Create a subaccount for ag_trade wallet"""
        try:
            # Initialize user if not already done
            await self.drift_client.initialize_user(subaccount_id)
            
            # Get user account to verify
            user = self.drift_client.get_user()
            user_account = user.get_user_account()
            
            logger.info(f"Successfully created subaccount {subaccount_id} for ag_trade wallet")
            logger.info(f"User account authority: {user_account.authority}")
            logger.info(f"User account subaccount_id: {user_account.sub_account_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create subaccount: {e}")
            return False

async def main():
    """Main function to set up ag_trade wallet's subaccount"""
    setup = AgTradeSetup()
    
    # Step 1: Load wallet
    if not await setup.load_ag_trade_wallet():
        return
    
    # Step 2: Initialize Drift client
    if not await setup.initialize_drift_client():
        return
    
    # Step 3: Create subaccount
    if not await setup.create_subaccount():
        return
    
    logger.info("Successfully completed ag_trade wallet setup!")

if __name__ == "__main__":
    asyncio.run(main()) 