"""
Multi-wallet manager for handling multiple Solana wallets.
Integrates with existing SolanaWallet class for wallet operations.
"""

import os
import json
import logging
import shutil
from typing import Dict, Optional, List
from pathlib import Path
from src.utils.wallet.sol_wallet import SolanaWallet

logger = logging.getLogger(__name__)

class WalletManager:
    """
    Manages multiple Solana wallets for different trading strategies.
    Provides functionality to add, remove, and switch between wallets.
    """
    
    # Mapping of wallet names to environment variable names
    WALLET_ENV_VARS = {
        "MAIN": "MAIN_KEY_PATH",
        "AG_TRADE": "AG_KEY_PATH",
        "KP_TRADE": "KP_KEY_PATH",
        "DRIFT": "DRIFT_PRIVATE_KEY_PATH"
    }
    
    def __init__(self):
        """Initialize wallet manager"""
        # Set logging to WARNING level temporarily
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        
        try:
            self.wallets = {}
            self.current_wallet = None
            self.load_wallet_configs()
        finally:
            # Restore original logging level
            root_logger.setLevel(original_level)
    
    def load_wallet_configs(self):
        """Load wallet configurations from environment variables"""
        loaded_wallets = 0
        
        # Check if we're in a test environment
        is_test_env = os.environ.get("PYTEST_CURRENT_TEST") is not None
        
        # Try to load wallets from environment variables
        for wallet_name, env_var in self.WALLET_ENV_VARS.items():
            keypair_path = os.getenv(env_var)
            if not keypair_path:
                continue
                
            try:
                if self.add_wallet(wallet_name, keypair_path, is_main=(wallet_name == "MAIN")):
                    loaded_wallets += 1
            except Exception as e:
                if is_test_env:
                    # In test environment, just log at debug level to avoid cluttering test output
                    logger.debug(f"Failed to load {wallet_name} wallet: {str(e)}")
                else:
                    # In production, log as error
                    logger.error(f"Failed to load {wallet_name} wallet: {str(e)}")
        
        if loaded_wallets == 0:
            log_func = logger.debug if is_test_env else logger.warning
            log_func("No wallet configurations found in environment variables")
    
    def get_wallet(self, name: str) -> Optional[SolanaWallet]:
        """Get a wallet by name"""
        return self.wallets.get(name.upper())
    
    def add_wallet(self, name: str, keypair_path: str, is_main: bool = False) -> bool:
        """
        Add a new wallet
        
        Args:
            name: Name for the wallet
            keypair_path: Path to keypair file
            is_main: Whether this is the main wallet
            
        Returns:
            bool: True if wallet was added successfully
        """
        try:
            name = name.upper()
            logger.info(f"Attempting to add wallet {name} from {keypair_path}")
            
            if not os.path.exists(keypair_path):
                logger.error(f"Keypair file not found: {keypair_path}")
                return False
                
            # Load keypair directly from JSON file
            try:
                with open(keypair_path, 'r') as f:
                    keypair_data = json.load(f)
                    keypair = bytes(keypair_data)
                    logger.info(f"Loaded keypair from {keypair_path}")
            except Exception as e:
                logger.error(f"Failed to read keypair file {keypair_path}: {str(e)}")
                return False
                
            # Create wallet object with the loaded keypair
            self.wallets[name] = SolanaWallet(
                name=name,
                keypair_path=keypair_path,
                keypair=keypair,
                is_main=is_main
            )
            
            if is_main:
                self.current_wallet = self.wallets[name]
                
            pubkey = self.wallets[name].get_public_key()
            logger.info(f"Successfully added wallet {name} with pubkey {pubkey}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to add wallet {name}: {e}")
            return False
    
    def remove_wallet(self, name: str) -> bool:
        """
        Remove a wallet
        
        Args:
            name: Name of wallet to remove
            
        Returns:
            bool: True if wallet was removed
        """
        try:
            name = name.upper()
            if name not in self.wallets:
                logger.error(f"Wallet {name} not found")
                return False
                
            # Remove from wallets dict
            del self.wallets[name]
            
            # Reset current wallet if needed
            if self.current_wallet and self.current_wallet.name == name:
                self.current_wallet = self.wallets.get("MAIN")
                
            return True
        except Exception as e:
            logger.error(f"Failed to remove wallet {name}: {e}")
            return False
    
    def switch_wallet(self, name: str) -> bool:
        """
        Switch to a different wallet
        
        Args:
            name: Name of wallet to switch to
            
        Returns:
            bool: True if switch was successful
        """
        name = name.upper()
        if name not in self.wallets:
            logger.error(f"Wallet {name} not found")
            return False
            
        self.current_wallet = self.wallets[name]
        return True
    
    def get_current_wallet(self) -> Optional[SolanaWallet]:
        """Get the currently selected wallet"""
        return self.current_wallet
    
    def list_wallets(self) -> List[str]:
        """Get list of wallet names"""
        return list(self.wallets.keys())
    
    async def load_wallet(self, name: str) -> bool:
        """
        Load a wallet from environment variable
        
        Args:
            name: Name of the wallet to load (main, kp_trade, etc.)
            
        Returns:
            bool: True if wallet was loaded successfully
        """
        name = name.upper()
        env_var = self.WALLET_ENV_VARS.get(name)
        if not env_var:
            logger.error(f"Unknown wallet name: {name}")
            return False
            
        # Try to get keypair path from environment variable
        keypair_path = os.getenv(env_var)
        
        # If environment variable is not set, use default paths
        if not keypair_path:
            if name == "MAIN":
                # Use default path for main wallet
                keypair_path = os.path.join(os.path.expanduser("~"), ".config/solana/keys/id.json")
                logger.info(f"Environment variable {env_var} not set, using default path: {keypair_path}")
            else:
                logger.error(f"Environment variable {env_var} not set and no default path is available")
                return False
        
        # Check if the file exists
        if not os.path.exists(keypair_path):
            logger.error(f"Keypair file not found at {keypair_path}")
            return False
            
        # Set the environment variable so other components can find it
        os.environ[env_var] = keypair_path
        
        return self.add_wallet(name, keypair_path, is_main=(name == "MAIN"))
    
    async def close(self):
        """
        Close all wallet connections
        
        This method closes any active RPC connections associated with the wallets.
        """
        try:
            for wallet_name, wallet in self.wallets.items():
                if hasattr(wallet, 'client') and wallet.client:
                    try:
                        await wallet.client.close()
                        logger.info(f"Closed connection for wallet {wallet_name}")
                    except Exception as e:
                        logger.error(f"Error closing connection for wallet {wallet_name}: {e}")
            logger.info("All wallet connections closed")
        except Exception as e:
            logger.error(f"Error closing wallet connections: {e}") 