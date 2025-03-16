"""
Test wallet implementation for Jupiter testnet strategy testing.
This is completely separate from the main wallet implementation and is only used for testing.
"""

import os
import json
import base64
import logging
from pathlib import Path

# Update Solana imports to match the actual package structure
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client

logger = logging.getLogger(__name__)

class TestWallet:
    """A simple wallet implementation for testing on Solana testnet."""
    
    def __init__(self, config_dir="test_config", filename="test_wallet.json"):
        """Initialize the test wallet.
        
        Args:
            config_dir (str): Directory to store the wallet config
            filename (str): Name of the wallet config file
        """
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / filename
        self.keypair = None
        self.rpc_client = Client("https://api.testnet.solana.com")
        
        # Create config directory if it doesn't exist
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
            logger.info(f"Created test config directory: {self.config_dir}")
    
    def generate_new_keypair(self):
        """Generate a new random keypair for testing."""
        self.keypair = Keypair()
        logger.info(f"Generated new test keypair with public key: {self.keypair.pubkey()}")
        return self.keypair
    
    def save_keypair(self):
        """Save the current keypair to the config file."""
        if not self.keypair:
            raise ValueError("No keypair to save. Generate or load a keypair first.")
        
        # Convert the keypair to bytes for storage
        keypair_bytes = bytes(self.keypair.secret())
        keypair_b64 = base64.b64encode(keypair_bytes).decode('utf-8')
        
        # Create a config object with clear TEST labels
        config = {
            "TEST_WALLET": True,
            "TEST_NETWORK": "testnet",
            "keypair_b64": keypair_b64,
            "public_key": str(self.keypair.pubkey())
        }
        
        # Save to the config file
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved test keypair to {self.config_file}")
    
    def load_keypair(self):
        """Load a keypair from the config file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Test wallet config file not found: {self.config_file}")
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        # Verify this is a test wallet config
        if not config.get("TEST_WALLET", False):
            raise ValueError("This does not appear to be a test wallet config file")
        
        # Load the keypair from base64
        keypair_b64 = config.get("keypair_b64")
        if not keypair_b64:
            raise ValueError("No keypair found in config file")
        
        keypair_bytes = base64.b64decode(keypair_b64)
        # Create keypair from secret
        self.keypair = Keypair.from_bytes(keypair_bytes)
        
        logger.info(f"Loaded test keypair with public key: {self.keypair.pubkey()}")
        return self.keypair
    
    def get_public_key(self):
        """Get the public key of the current keypair."""
        if not self.keypair:
            raise ValueError("No keypair loaded. Generate or load a keypair first.")
        return self.keypair.pubkey()
    
    def get_balance(self):
        """Get the SOL balance of the current wallet on testnet."""
        if not self.keypair:
            raise ValueError("No keypair loaded. Generate or load a keypair first.")
        
        try:
            # The new Solana RPC response format is different
            response = self.rpc_client.get_balance(self.keypair.pubkey())
            # Handle the new response format
            if hasattr(response, 'value'):
                # New format
                balance = response.value / 1_000_000_000  # Convert lamports to SOL
            else:
                # Try the old format
                balance = response["result"]["value"] / 1_000_000_000
                
            logger.info(f"Test wallet balance: {balance} SOL")
            return balance
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return None
    
    def request_airdrop(self, amount_sol=1):
        """Request an airdrop of SOL from the testnet faucet.
        
        Args:
            amount_sol (float): Amount of SOL to request (max 1 SOL per request)
        
        Returns:
            str: Transaction signature or None if failed
        """
        if not self.keypair:
            raise ValueError("No keypair loaded. Generate or load a keypair first.")
        
        try:
            # Convert SOL to lamports (1 SOL = 1 billion lamports)
            amount_lamports = int(amount_sol * 1_000_000_000)
            
            # Request the airdrop
            response = self.rpc_client.request_airdrop(
                self.keypair.pubkey(), 
                amount_lamports
            )
            
            # Handle the new response format
            if hasattr(response, 'value'):
                # New format
                signature = str(response.value)
            else:
                # Try the old format
                signature = response["result"]
                
            logger.info(f"Requested airdrop of {amount_sol} SOL. Signature: {signature}")
            return signature
        except Exception as e:
            logger.error(f"Error requesting airdrop: {str(e)}")
            return None


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a test wallet
    wallet = TestWallet()
    
    # Check if a wallet config already exists
    try:
        wallet.load_keypair()
        print(f"Loaded existing test wallet: {wallet.get_public_key()}")
    except (FileNotFoundError, ValueError):
        # Generate a new wallet if none exists
        wallet.generate_new_keypair()
        wallet.save_keypair()
        print(f"Generated new test wallet: {wallet.get_public_key()}")
    
    # Check balance
    balance = wallet.get_balance()
    print(f"Current balance: {balance} SOL")
    
    # Request an airdrop if balance is low
    if balance is not None and balance < 0.5:
        print("Balance is low, requesting an airdrop...")
        signature = wallet.request_airdrop(1)
        if signature:
            print(f"Airdrop requested. Signature: {signature}")
            # Wait a moment and check the new balance
            import time
            time.sleep(5)
            new_balance = wallet.get_balance()
            print(f"New balance: {new_balance} SOL") 