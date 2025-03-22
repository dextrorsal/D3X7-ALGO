"""
Solana RPC client configuration and network management
"""

import os
import logging
import json
from typing import Optional
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from dotenv import load_dotenv
from solana.rpc.api import Client
from pathlib import Path

# Load environment variables
load_dotenv()

# Comment out logging setup
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# Network configuration
NETWORK_URLS = {
    "mainnet": os.getenv("MAINNET_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com"),
    "devnet": os.getenv("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com"),
    "testnet": os.getenv("TESTNET_RPC_URL", "https://api.testnet.solana.com")
}

# Wallet path configuration - using only .env values
WALLET_PATHS = {
    "main": os.getenv("PRIVATE_KEY_PATH"),  # main.enc
    "kp_trade": os.getenv("KP_PATH"),       # kp_trade.enc
    "ag_trade": os.getenv("AG_PATH"),       # ag_trade.enc
    "drift": os.getenv("DRIFT_PRIVATE_KEY_PATH")  # drift wallet
}

# Base directories
BASE_CONFIG_DIR = os.path.expanduser("~/.config/solana")
TRADING_CONFIG_DIR = os.path.join(BASE_CONFIG_DIR, "trading")
DRIFT_CONFIG_DIR = os.path.join(BASE_CONFIG_DIR, "drift")

# Configuration file path (using trading directory from .env paths)
CONFIG_FILE = os.path.join(os.path.dirname(WALLET_PATHS["main"]), "network_config.json")

def get_wallet_path(wallet_name: str = "main") -> str:
    """Get the wallet path for the specified wallet name
    
    Args:
        wallet_name (str): Name of the wallet (main, kp, ag_trade, drift)
        
    Returns:
        str: Path to the wallet file
    """
    if wallet_name.lower() not in WALLET_PATHS:
        raise ValueError(f"Unknown wallet: {wallet_name}. Must be one of: {', '.join(WALLET_PATHS.keys())}")
    
    path = WALLET_PATHS[wallet_name.lower()]
    if not path:
        raise ValueError(f"Wallet path not found in .env: {wallet_name}")
    
    return path

def get_rpc_url(network: Optional[str] = None) -> str:
    """Get the RPC URL for the specified network or current network"""
    if network is None:
        network = get_network()
        
    # First try environment variables
    if network == "mainnet":
        return os.getenv("MAINNET_RPC_ENDPOINT", NETWORK_URLS["mainnet"])
    elif network == "devnet":
        return os.getenv("DEVNET_RPC_ENDPOINT", NETWORK_URLS["devnet"])
    else:  # testnet
        return os.getenv("TESTNET_RPC_URL", NETWORK_URLS["testnet"])

def load_network_config() -> str:
    """Load network configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('network', 'devnet')
    except Exception:
        pass
    return 'devnet'  # Default to devnet if no config exists

def save_network_config(network: str) -> bool:
    """Save network configuration to file"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'network': network}, f)
        return True
    except Exception:
        return False

# Global state
_current_network = load_network_config()  # Load from config file
_network_client = None

class SolanaRPC:
    """Solana RPC client wrapper"""
    def __init__(self):
        self._network = None
        self._client = None
        self.set_network(_current_network)
        
    def set_network(self, network: str):
        """Set the Solana network to use"""
        if network not in ["mainnet", "devnet", "testnet"]:
            raise ValueError("Invalid network. Must be 'mainnet', 'devnet', or 'testnet'")
            
        if network != self._network:
            self._network = network
            self._client = None  # Force client recreation
            save_network_config(network)  # Persist network choice
            
    def get_network(self) -> str:
        """Get the current network"""
        return self._network
        
    def get_client(self) -> Client:
        """Get the Solana RPC client"""
        if not self._client:
            if self._network == "mainnet":
                rpc_url = os.getenv("MAINNET_RPC_URL", NETWORK_URLS["mainnet"])
            elif self._network == "devnet":
                rpc_url = os.getenv("DEVNET_RPC_URL", NETWORK_URLS["devnet"])
            else:  # testnet
                rpc_url = os.getenv("TESTNET_RPC_URL", NETWORK_URLS["testnet"])
                
            self._client = Client(rpc_url, commitment=Confirmed)
            
        return self._client

# Global RPC client instance
_rpc_client = SolanaRPC()

def set_network(network: str) -> bool:
    """Set the Solana network to use"""
    try:
        network = network.lower()  # Convert to lowercase for consistency
        if network not in NETWORK_URLS:
            return False
            
        _rpc_client.set_network(network)
        return True
    except Exception:
        return False

def get_network() -> str:
    """Get the current network"""
    return _rpc_client.get_network()

def get_client() -> Client:
    """Get the Solana RPC client"""
    return _rpc_client.get_client()

async def get_solana_client(network: Optional[str] = None) -> AsyncClient:
    """Get the Solana RPC client
    
    Args:
        network (Optional[str]): Optional network to use ('mainnet' or 'devnet').
                               If not specified, uses the current network.
    
    Returns:
        AsyncClient: Solana RPC client configured for the specified network
    """
    global _network_client, _current_network
    
    # Update network if specified
    if network:
        set_network(network)
    
    if not _network_client:
        rpc_url = get_rpc_url(_current_network)
        _network_client = AsyncClient(rpc_url, commitment=Confirmed)
        try:
            await _network_client.get_version()
        except Exception as e:
            _network_client = None
            raise
            
    return _network_client

def get_solana_network() -> str:
    """Get the current Solana network"""
    return _rpc_client.get_network()

def set_solana_network(network: str):
    """Set the Solana network for the global client"""
    _rpc_client.set_network(network)
    # Also update the persisted config
    save_network_config(network)

if __name__ == "__main__":
    import asyncio
    
    async def test_rpc():
        try:
            # Test connection
            client = await get_solana_client()
            version = await client.get_version()
            print(f"Connected to {get_network()} network")
            print("Solana Node Version:", version)
            
            # Test network switching
            set_network("mainnet")
            client = await get_solana_client()
            version = await client.get_version()
            print(f"\nSwitched to {get_network()} network")
            print("Solana Node Version:", version)
        except Exception as e:
            print("Error:", str(e))
            
    asyncio.run(test_rpc())
