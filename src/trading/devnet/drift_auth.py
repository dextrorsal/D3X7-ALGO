#!/usr/bin/env python3
"""
Drift authentication helper module.
Handles client initialization and user setup.
"""

import asyncio
import logging
import os
import json
from typing import Optional

from anchorpy.provider import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.types import TxParams
from driftpy.keypair import load_keypair

# Configure logging with more detail from minimal_maker.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DriftHelper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def initialize_drift(self, tx_params: Optional[TxParams] = None) -> DriftClient:
        """Initialize Drift client with wallet and RPC connection"""
        # Load keypair from default location
        keypair_path = os.path.expanduser("~/.config/solana/id.json")
        if not os.path.exists(keypair_path):
            raise FileNotFoundError(f"Keypair not found at {keypair_path}")
            
        with open(keypair_path, 'r') as f:
            keypair_bytes = bytes(json.load(f))
            
        keypair = Keypair.from_bytes(keypair_bytes)
        self.logger.info(f"Loaded wallet: {keypair.pubkey()}")
        
        # Set up provider with RPC connection
        connection = AsyncClient("https://api.devnet.solana.com")
        provider = Provider(connection, Wallet(keypair))
        
        # Initialize Drift client with transaction parameters
        if tx_params is None:
            tx_params = TxParams(
                compute_units_price=85_000,  # Default from example
                compute_units=1_400_000      # Default from example
            )
            
        drift_client = DriftClient(
            connection,
            Wallet(keypair),
            env="devnet",
            tx_params=tx_params
        )
        
        return drift_client

    async def get_user_info(self):
        """Get user account information using patterns from view.py"""
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            drift_user = self.drift_client.get_user()
            user = drift_user.get_user_account()
            
            # Get collateral info
            spot_collateral = drift_user.get_spot_market_asset_value(
                None,
                include_open_orders=True,
            )
            
            # Get PnL
            unrealized_pnl = drift_user.get_unrealized_pnl(False)
            
            # Get total collateral
            total_collateral = drift_user.get_total_collateral()
            
            logger.info("\n=== User Account Info ===")
            logger.info(f"Spot Collateral: ${spot_collateral / QUOTE_PRECISION:,.2f}")
            logger.info(f"Unrealized PnL: ${unrealized_pnl / QUOTE_PRECISION:,.2f}")
            logger.info(f"Total Collateral: ${total_collateral / QUOTE_PRECISION:,.2f}")
            
        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            raise

async def main():
    helper = DriftHelper()
    try:
        logger.info("Initializing Drift client...")
        drift_client = await helper.initialize_drift()
        logger.info("Drift client initialized successfully!")
        
        # Get initial user info
        await helper.get_user_info()
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if helper.drift_client:
            await helper.drift_client.unsubscribe()
            logger.info("Successfully unsubscribed from Drift")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if helper.drift_client:
            await helper.drift_client.unsubscribe()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")