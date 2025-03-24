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
import asyncio
from solana.exceptions import SolanaRpcException
from websockets.exceptions import InvalidStatusCode, WebSocketException

# Load environment variables
load_dotenv()

# Comment out logging setup
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# Network configuration
NETWORK_URLS = {
    "mainnet": os.getenv("MAINNET_RPC_ENDPOINT"),
    "devnet": os.getenv("DEVNET_RPC_ENDPOINT")
}

# Validate required RPC endpoints
if not NETWORK_URLS["mainnet"]:
    raise EnvironmentError("MAINNET_RPC_ENDPOINT environment variable not set")
if not NETWORK_URLS["devnet"]:
    raise EnvironmentError("DEVNET_RPC_ENDPOINT environment variable not set")

# Base directories
BASE_CONFIG_DIR = os.path.expanduser("~/.config/solana")
TRADING_CONFIG_DIR = os.path.join(BASE_CONFIG_DIR, "trading")
DRIFT_CONFIG_DIR = os.path.join(BASE_CONFIG_DIR, "drift")

# Wallet path configuration - using .env values with fallbacks to JSON files
WALLET_PATHS = {
    "main": os.getenv("MAIN_KEY_PATH", os.path.join(BASE_CONFIG_DIR, "keys/id.json")),
    "kp_trade": os.getenv("KP_KEY_PATH", os.path.join(TRADING_CONFIG_DIR, "kp_trade.json")),
    "ag_trade": os.getenv("AG_KEY_PATH", os.path.join(TRADING_CONFIG_DIR, "ag_trade.json")),
    "drift": os.getenv("DRIFT_PRIVATE_KEY_PATH", os.path.join(DRIFT_CONFIG_DIR, "drift.json"))
}

# Configuration file path
CONFIG_FILE = os.path.join(TRADING_CONFIG_DIR, "network_config.json")

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
        
    # Get URL from environment variables
    if network == "mainnet":
        url = os.getenv("MAINNET_RPC_ENDPOINT")
        if not url:
            raise EnvironmentError("MAINNET_RPC_ENDPOINT environment variable not set")
    else:  # devnet
        url = os.getenv("DEVNET_RPC_ENDPOINT")
        if not url:
            raise EnvironmentError("DEVNET_RPC_ENDPOINT environment variable not set")
    
    return url

def load_network_config() -> str:
    """Load network configuration from file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                network = config.get('network', 'devnet')
                # Convert testnet to devnet since we no longer support testnet
                if network == "testnet":
                    network = "devnet"
                return network
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
        if network not in ["mainnet", "devnet"]:
            raise ValueError("Invalid network. Must be 'mainnet' or 'devnet'")
            
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
                rpc_url = os.getenv("MAINNET_RPC_ENDPOINT", NETWORK_URLS["mainnet"])
            else:  # devnet
                rpc_url = os.getenv("DEVNET_RPC_ENDPOINT", NETWORK_URLS["devnet"])
                
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

class WebSocketRetry:
    def __init__(self, max_retries=3, initial_delay=1.0, max_delay=10.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.delay = initial_delay

    def reset(self):
        self.attempt = 0
        self.delay = self.initial_delay

    def next_delay(self) -> float:
        if self.attempt >= self.max_retries:
            return -1
        
        delay = min(self.delay * (2 ** self.attempt), self.max_delay)
        self.attempt += 1
        return delay

async def get_solana_client(network: str = None) -> Optional[AsyncClient]:
    """Get a Solana RPC client with retry logic for rate limits."""
    retry = WebSocketRetry()
    
    while True:
        try:
            url = get_rpc_url(network)
            client = AsyncClient(url)
            # Test the connection with a simple request
            await client.get_version()
            logging.info(f"Successfully connected to {network or 'current network'} RPC")
            return client
        except InvalidStatusCode as e:
            if e.status_code == 429:  # Rate limit
                delay = retry.next_delay()
                if delay < 0:
                    logging.error(f"Max retries exceeded for RPC connection")
                    return None
                logging.warning(f"Rate limited, retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                logging.error(f"Invalid status code: {e.status_code}")
                return None
        except WebSocketException as e:
            logging.error(f"WebSocket error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Failed to initialize Solana client: {str(e)}")
            return None

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
