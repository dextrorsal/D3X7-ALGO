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
from dotenv import load_dotenv

from anchorpy.provider import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.types import TxParams
from driftpy.keypair import load_keypair

from src.utils.wallet.wallet_manager import WalletManager

# Load environment variables
load_dotenv()

# Configure logging with more detail from minimal_maker.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DriftHelper:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wallet_manager = WalletManager()
        
        # Get RPC URL from environment variables based on DRIFT_NETWORK
        network = os.getenv('DRIFT_NETWORK', 'devnet').strip().split('#')[0].strip()
        
        # Validate network value
        if network not in ['devnet', 'mainnet-beta']:
            self.logger.warning(f"Invalid network value '{network}', defaulting to devnet")
            network = 'devnet'
            
        self.network = network
        if self.network == 'devnet':
            self.rpc_url = os.getenv('DEVNET_RPC_ENDPOINT', 'https://api.devnet.solana.com').strip()
        else:
            self.rpc_url = os.getenv('MAINNET_RPC_ENDPOINT', 'https://api.mainnet-beta.solana.com').strip()
            
        self.logger.info(f"Using {self.network} network with RPC URL: {self.rpc_url}")
        
    async def initialize_drift(self, tx_params: Optional[TxParams] = None) -> DriftClient:
        """Initialize Drift client with wallet and RPC connection"""
        try:
            # Load wallet using WalletManager
            wallet = self.wallet_manager.get_wallet("MAIN")  # Use MAIN wallet
            if not wallet:
                raise Exception("Failed to load MAIN wallet")
                
            # Get keypair from wallet
            if hasattr(wallet, 'keypair') and wallet.keypair:
                if isinstance(wallet.keypair, bytes):
                    keypair = Keypair.from_bytes(wallet.keypair)
                else:
                    keypair = wallet.keypair
            else:
                raise Exception("No keypair available in wallet")
                
            self.logger.info(f"Loaded wallet: {keypair.pubkey()}")
            
            # Set up RPC connection with URL from environment
            self.logger.info(f"Connecting to {self.network} RPC: {self.rpc_url}")
            connection = AsyncClient(self.rpc_url)
            
            # Initialize Drift client with transaction parameters
            if tx_params is None:
                tx_params = TxParams(
                    compute_units_price=85_000,  # Default from example
                    compute_units=1_400_000      # Default from example
                )
                
            self.logger.info("Initializing Drift client...")
            drift_client = DriftClient(
                connection,
                Wallet(keypair),
                env=self.network,  # Use network from environment
                tx_params=tx_params,
                account_subscription=AccountSubscriptionConfig("websocket")
            )
            
            # Add users after client initialization
            for subaccount_id in range(5):
                try:
                    await drift_client.add_user(subaccount_id)
                    self.logger.info(f"Added subaccount {subaccount_id} to client")
                except Exception as e:
                    self.logger.warning(f"Could not add subaccount {subaccount_id}: {str(e)}")
            
            self.logger.info(f"Drift client initialized successfully on {self.network}")
            return drift_client
            
        except Exception as e:
            self.logger.error(f"Error initializing Drift client: {str(e)}")
            raise

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