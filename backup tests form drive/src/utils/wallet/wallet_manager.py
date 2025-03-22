"""
Multi-wallet manager for handling multiple Solana wallets.
Integrates with existing SolanaWallet class for wallet operations.
"""

import os
import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
from src.utils.wallet.sol_wallet import SolanaWallet

logger = logging.getLogger(__name__)

class WalletManager:
    """
    Manages multiple Solana wallets for different trading strategies.
    Provides functionality to add, remove, and switch between wallets.
    """
    
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
        try:
            # Load wallet paths from environment variables
            wallet_paths = {
                "MAIN": os.getenv('PRIVATE_KEY_PATH'),
                "AG_TRADE": os.getenv('AG_PATH'),
                "KP_TRADE": os.getenv('KP_PATH')
            }
            
            # Add each configured wallet
            for wallet_name, keypair_path in wallet_paths.items():
                if keypair_path and os.path.exists(keypair_path):
                    try:
                        self.wallets[wallet_name] = SolanaWallet(
                            name=wallet_name,
                            keypair_path=keypair_path,
                            is_main=wallet_name == "MAIN"
                        )
                        if wallet_name == "MAIN":
                            self.current_wallet = self.wallets[wallet_name]
                        logger.info(f"Loaded {wallet_name} wallet from environment")
                    except Exception as e:
                        logger.error(f"Failed to load {wallet_name} wallet: {e}")
            
            if not self.wallets:
                logger.warning("No wallet configurations found in environment variables")
                
        except Exception as e:
            logger.error(f"Error loading wallet configurations: {e}")
    
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
            trading_dir = os.path.expanduser("~/.config/solana/trading")
            os.makedirs(trading_dir, exist_ok=True)
            
            # Load keypair - try JSON, raw byte array, and binary formats
            try:
                # First try as binary
                with open(keypair_path, 'rb') as f:
                    binary_content = f.read()
                    try:
                        # Try to parse as JSON first
                        keypair = json.loads(binary_content)
                    except json.JSONDecodeError:
                        # If not JSON, try as raw byte array
                        try:
                            # Try to decode as UTF-8 string
                            content = binary_content.decode('utf-8').strip()
                            # Parse array-like string to list of integers
                            content = content.strip('[]')
                            keypair = [int(x.strip()) for x in content.split(',')]
                        except UnicodeDecodeError:
                            # If can't decode as UTF-8, treat as raw bytes
                            keypair = list(binary_content)
            except Exception as e:
                logger.error(f"Failed to read keypair file {keypair_path}: {e}")
                return False
                
            # Get encryption password
            password = os.getenv("WALLET_PASSWORD")
            if not password:
                logger.error("WALLET_PASSWORD not set")
                return False
                
            # Create wallet config
            config = {
                "name": name,
                "keypair": keypair,
                "keypair_path": keypair_path,
                "is_main": is_main
            }
            
            # Encrypt and save config
            encryption = WalletEncryption(password)
            enc_path = os.path.join(trading_dir, f"{name.lower()}.enc")
            if encryption.save_encrypted_config(config, enc_path):
                # Create wallet object
                self.wallets[name] = SolanaWallet(
                    name=name,
                    keypair_path=keypair_path,
                    keypair=keypair,
                    is_main=is_main
                )
                if is_main:
                    self.current_wallet = self.wallets[name]
                return True
            return False
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
                
            # Delete encrypted config
            trading_dir = os.path.expanduser("~/.config/solana/trading")
            enc_path = os.path.join(trading_dir, f"{name.lower()}.enc")
            if os.path.exists(enc_path):
                os.remove(enc_path)
                
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
    
    def encrypt_wallet(self, name: str) -> bool:
        """
        Encrypt a wallet configuration
        
        Args:
            name: Name of the wallet to encrypt
            
        Returns:
            bool: True if encryption was successful
        """
        try:
            name = name.upper()
            trading_dir = os.path.expanduser("~/.config/solana/trading")
            os.makedirs(trading_dir, exist_ok=True)
            
            # Get wallet path
            if name == "MAIN":
                wallet_path = os.path.expanduser("~/.config/solana/id.json")
            else:
                wallet_path = os.path.join(trading_dir, f"{name.lower()}.json")
                
            if not os.path.exists(wallet_path):
                logger.error(f"Wallet file {wallet_path} not found")
                return False
                
            # Get encryption password
            password = os.getenv("WALLET_PASSWORD")
            if not password:
                logger.error("WALLET_PASSWORD not set")
                return False
                
            # Create backup
            backup_path = wallet_path + ".bak"
            shutil.copy2(wallet_path, backup_path)
            logger.info(f"Created backup at {backup_path}")
            
            try:
                # Load keypair
                with open(wallet_path) as f:
                    keypair = json.load(f)
                    
                # Create config
                config = {
                    "name": name,
                    "keypair": keypair,
                    "keypair_path": wallet_path,
                    "is_main": name == "MAIN"
                }
                
                # Encrypt config
                encryption = WalletEncryption(password)
                enc_path = os.path.join(trading_dir, f"{name.lower()}.enc")
                if encryption.save_encrypted_config(config, enc_path):
                    logger.info(f"Successfully encrypted wallet {name}")
                    
                    # Verify encryption
                    try:
                        test_encryption = WalletEncryption(password)
                        test_config = test_encryption.load_encrypted_config(enc_path)
                        if test_config["name"] == name:
                            logger.info("Verified encryption successful")
                            # Delete original file
                            os.remove(wallet_path)
                            logger.info(f"Deleted original file {wallet_path}")
                            return True
                    except Exception as e:
                        logger.error(f"Failed to verify encryption: {e}")
                        
                # If we get here, something went wrong
                logger.error("Failed to verify encryption, restoring from backup")
                shutil.copy2(backup_path, wallet_path)
                if os.path.exists(enc_path):
                    os.remove(enc_path)
                return False
                
            except Exception as e:
                logger.error(f"Failed to encrypt wallet: {e}")
                # Restore from backup
                shutil.copy2(backup_path, wallet_path)
                logger.info("Restored from backup")
                return False
                
            finally:
                # Clean up backup
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                    
        except Exception as e:
            logger.error(f"Failed to encrypt wallet {name}: {e}")
            return False 