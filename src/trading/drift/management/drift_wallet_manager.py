#!/usr/bin/env python3
"""
Drift wallet and subaccount manager.
Manages multiple Drift subaccounts with encryption support.
"""

import os
import json
import logging
import shutil
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import traceback

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from anchorpy.provider import Wallet
from driftpy.drift_client import DriftClient
from driftpy.drift_user import DriftUser
from driftpy.decode.utils import decode_name
from driftpy.types import TxParams
from driftpy.keypair import load_keypair
from driftpy.account_subscription_config import AccountSubscriptionConfig
from anchorpy.provider import Provider

from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.encryption import WalletEncryption
from src.utils.wallet.sol_rpc import get_network, get_client, NETWORK_URLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DriftWalletManager:
    """
    Manages Drift wallets and subaccounts with encryption support.
    Integrates with the SolanaWallet manager for wallet loading.
    """
    
    def __init__(self, config_dir: str, rpc_url: str):
        """
        Initialize the DriftWalletManager.
        
        Args:
            config_dir: Directory for storing configurations
            rpc_url: RPC URL for connecting to Solana
        """
        self.config_dir = config_dir
        self.rpc_url = rpc_url
        self.network = "mainnet"  # Default to mainnet
        self.wallet_manager = WalletManager()
        self.subaccount_configs = {}
        self.load_subaccount_configs()
        
    def load_subaccount_configs(self) -> None:
        """Load all subaccount configurations from disk"""
        try:
            # Clear existing configs
            self.subaccount_configs = {}
            
            # List all config files
            for file in os.listdir(self.config_dir):
                if not file.endswith('.json'):
                    continue
                    
                try:
                    # Parse filename (format: wallet_subaccount.json)
                    parts = file[:-5].split('_')  # Remove .json and split
                    if len(parts) != 2:
                        continue
                        
                    wallet_name = parts[0].upper()
                    subaccount_id = int(parts[1])
                    
                    # Load config
                    config_path = os.path.join(self.config_dir, file)
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        
                    # Initialize wallet dict if needed
                    if wallet_name not in self.subaccount_configs:
                        self.subaccount_configs[wallet_name] = {}
                        
                    # Store config
                    self.subaccount_configs[wallet_name][subaccount_id] = config
                    
                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"Error loading config {file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading subaccount configs: {e}")
            
    def save_subaccount_config(self, wallet_name: str, subaccount_id: int, 
                              config: Dict[str, Any]) -> bool:
        """
        Save an encrypted subaccount configuration.
        
        Args:
            wallet_name: Name of the wallet (MAIN, AG_TRADE, etc.)
            subaccount_id: Subaccount ID (0-255)
            config: Subaccount configuration dictionary
            
        Returns:
            bool: True if saved successfully
        """
        try:
            wallet_name = wallet_name.upper()
            
            # Validate subaccount ID
            if not (0 <= subaccount_id <= 255):
                logger.error(f"Invalid subaccount ID: {subaccount_id}")
                return False
                
            # Get encryption password
            password = os.getenv("WALLET_PASSWORD")
            if not password:
                logger.error("WALLET_PASSWORD environment variable not set")
                return False
                
            # Create encryption instance
            encryption = WalletEncryption(password)
            
            # Add timestamp to config
            config['last_updated'] = datetime.now().isoformat()
            
            # Save encrypted config
            filename = f"{wallet_name.lower()}_{subaccount_id}.enc"
            filepath = os.path.join(self.config_dir, filename)
            
            if encryption.save_encrypted_config(config, filepath):
                # Update in-memory config
                if wallet_name not in self.subaccount_configs:
                    self.subaccount_configs[wallet_name] = {}
                self.subaccount_configs[wallet_name][subaccount_id] = config
                logger.info(f"Saved subaccount {subaccount_id} for wallet {wallet_name}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error saving subaccount config: {e}")
            return False
            
    async def create_subaccount(self, wallet_name: str, subaccount_id: int, name: str = None) -> bool:
        """Create a new subaccount for the given wallet"""
        drift_client = None
        try:
            # Load wallet
            wallet = await self.load_wallet(wallet_name)
            if not wallet:
                logger.error(f"Failed to load wallet {wallet_name}")
                return False

            # Get network and RPC URL
            network = get_network()
            rpc_url = NETWORK_URLS[network]
            logger.info(f"Using network: {network}")
            
            # Create basic connection and drift client
            connection = AsyncClient(rpc_url)
            drift_client = DriftClient(
                connection,
                wallet,
                "mainnet",  # Use string directly instead of variable
                account_subscription=AccountSubscriptionConfig("cached")
            )

            # Subscribe to get updates
            await drift_client.subscribe()
            
            try:
                # Get all user accounts for this authority
                logger.info(f"Fetching user accounts for authority: {wallet.public_key}...")
                
                # First try to get user directly
                logger.info("Attempting to get user account directly...")
                try:
                    drift_user = drift_client.get_user()
                    if drift_user:
                        user = drift_user.get_user_account()
                        if user:
                            subaccount_id = user.sub_account_id
                            name = decode_name(user.name) if user.name else f"Subaccount {subaccount_id}"
                            found_accounts = [{
                                'wallet': wallet_name,
                                'subaccount_id': subaccount_id,
                                'name': name,
                                'network': network,
                                'status': 'active',
                                'authority': str(wallet.public_key)
                            }]
                            logger.info(f"Found subaccount {subaccount_id}: {name}")
                            return found_accounts
                except Exception as e:
                    logger.info(f"Direct user fetch failed, falling back to program accounts: {e}")
                
                # Fallback to getting all accounts
                logger.info("Fetching all program accounts...")
                user_accounts = await drift_client.program.account["User"].all()
                logger.info(f"Found {len(user_accounts)} total user accounts")
                
                found_accounts = []
                for account in user_accounts:
                    try:
                        logger.debug(f"Checking account authority: {account.account.authority}")
                        if account.account.authority == wallet.public_key:
                            subaccount_id = account.account.sub_account_id
                            name = decode_name(account.account.name) if account.account.name else f"Subaccount {subaccount_id}"
                            
                            found_accounts.append({
                                'wallet': wallet_name,
                                'subaccount_id': subaccount_id,
                                'name': name,
                                'network': network,
                                'status': 'active',
                                'authority': str(account.account.authority)
                            })
                            logger.info(f"Found subaccount {subaccount_id}: {name}")
                    except Exception as e:
                        logger.debug(f"Error processing account: {e}")
                        continue
                
                if not found_accounts:
                    logger.info(f"No existing subaccounts found for wallet {wallet_name}")
                return found_accounts
                
            finally:
                # Clean up
                await drift_client.unsubscribe()

            # Save basic config
            config = {
                "name": name if name else "Main Account",
                "wallet": wallet_name,
                "subaccount_id": subaccount_id,
                "network": network,
                "created_at": datetime.now().isoformat()
            }
            self.save_subaccount_config(wallet_name, subaccount_id, config)
            logger.info(f"Subaccount {subaccount_id} created and config saved")
            return True

        except Exception as e:
            logger.error(f"Failed to create subaccount: {e}")
            traceback.print_exc()
            return False

    async def list_subaccounts(self, wallet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all subaccounts from the blockchain, optionally filtered by wallet name."""
        try:
            logging.info(f"Using network: {self.network}")
            logging.info(f"Using RPC URL: {self.rpc_url}")
            
            # Load the wallet if specified
            wallet = await self.load_wallet(wallet_name)
            if wallet_name and not wallet:
                logging.error(f"Failed to load wallet {wallet_name}")
                return []
            
            if wallet:
                logging.info(f"Using wallet with public key: {wallet.public_key}")
            
            connection = AsyncClient(self.rpc_url)
            logging.info("Initializing DriftClient...")
            
            drift_client = DriftClient(
                connection,
                wallet,
                "mainnet",
                account_subscription=AccountSubscriptionConfig("cached")
            )
            
            try:
                # Subscribe first
                logging.info("Subscribing to DriftClient...")
                await drift_client.subscribe()
                
                # Get user directly
                logging.info("Getting user account...")
                drift_user = drift_client.get_user()
                if not drift_user:
                    logging.info("No user account found")
                    return []
                
                user = drift_user.get_user_account()
                if not user:
                    logging.info("No user account data found")
                    return []
                
                name = decode_name(user.name) if user.name else f"Subaccount {user.sub_account_id}"
                found_account = {
                    "subaccount_id": user.sub_account_id,
                    "name": name,
                    "authority": str(wallet.public_key),
                    "created_at": user.created_at,
                    "status": user.status
                }
                logging.info(f"Found subaccount: {found_account}")
                return [found_account]
                
            finally:
                # Unsubscribe and close connection
                logging.info("Unsubscribing from DriftClient...")
                await drift_client.unsubscribe()
                await connection.close()
            
        except Exception as e:
            logging.error(f"Error listing subaccounts: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return []

    async def load_wallet(self, wallet_name: Optional[str] = None) -> Optional[Wallet]:
        """Load a wallet for use with Drift."""
        try:
            if not wallet_name:
                return None
            
            wallet = self.wallet_manager.get_wallet(wallet_name)
            if not wallet:
                logging.error(f"Failed to load wallet {wallet_name}")
                return None
            
            # Convert bytes to Keypair if needed
            if isinstance(wallet.keypair, bytes):
                keypair = Keypair.from_bytes(wallet.keypair)
            else:
                keypair = wallet.keypair
            
            return Wallet(keypair)
        except Exception as e:
            logging.error(f"Error loading wallet: {e}")
            return None