"""
Core Drift client implementation.
"""

import os
import logging
import json
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from anchorpy import Wallet, Provider
from driftpy.drift_client import DriftClient as DriftPyClient
from driftpy.types import TxParams
from driftpy.constants.perp_markets import mainnet_perp_market_configs, devnet_perp_market_configs

from src.core.exceptions import ExchangeError, NotInitializedError

logger = logging.getLogger(__name__)

class DriftClient:
    """
    Core Drift client for interacting with the Drift protocol.
    Handles client initialization, connection management, and market lookups.
    """
    
    def __init__(self, network: str = "devnet", keypair_path: Optional[str] = None):
        """Initialize the Drift client."""
        load_dotenv()
        self.network = network.lower()
        
        # Try different keypair paths in order of priority
        self.keypair_path = (
            keypair_path or  # Explicitly provided path
            os.getenv("DEVNET_KEYPAIR_PATH") or  # Environment variable for devnet
            os.getenv("MAIN_KEY_PATH") or  # Main keypair path
            "/home/dex/.config/solana/keys/id.json"  # Default path
        )
        
        self.rpc_url = (
            os.getenv('MAINNET_RPC_ENDPOINT', "https://api.mainnet-beta.solana.com")
            if network == 'mainnet' 
            else os.getenv('DEVNET_RPC_ENDPOINT', "https://api.devnet.solana.com")
        )
        
        self.client: Optional[DriftPyClient] = None
        self.connection: Optional[AsyncClient] = None
        self.keypair: Optional[Keypair] = None
        
        # Market lookup tables
        self.market_configs = mainnet_perp_market_configs if network == 'mainnet' else devnet_perp_market_configs
        self.market_name_lookup: Dict[str, int] = {}
        self.market_index_lookup: Dict[int, str] = {}
        
        # Initialize market lookups
        for market in self.market_configs:
            # Store both with and without -PERP suffix for flexibility
            base_symbol = market.symbol.replace("-PERP", "")
            self.market_name_lookup[base_symbol] = market.market_index
            self.market_name_lookup[f"{base_symbol}-PERP"] = market.market_index
            self.market_index_lookup[market.market_index] = f"{base_symbol}-PERP"
            
        logger.info(f"Available markets in {network}: {list(self.market_name_lookup.keys())}")
        
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Drift client connection."""
        if not self.keypair_path:
            raise ExchangeError("No keypair path provided and DEVNET_KEYPAIR_PATH environment variable not set")
            
        if not os.path.exists(self.keypair_path):
            raise ExchangeError(f"Keypair not found at {self.keypair_path}")
            
        try:
            # Load keypair
            with open(self.keypair_path, 'r') as f:
                keypair_bytes = bytes(json.load(f))
                
            self.keypair = Keypair.from_bytes(keypair_bytes)
            logger.info(f"Loaded keypair from {self.keypair_path}")
            
            # Initialize Solana connection
            self.connection = AsyncClient(self.rpc_url)
            logger.info(f"Connected to Solana RPC at {self.rpc_url}")
            
            # Initialize Drift client with transaction parameters
            tx_params = TxParams(
                compute_units_price=85_000,  # Default from example
                compute_units=1_400_000      # Default from example
            )
            
            self.client = DriftPyClient(
                self.connection,
                Wallet(self.keypair),
                self.network,
                tx_params=tx_params
            )
            
            # Initialize user account if needed
            try:
                await self.client.initialize_user()
                logger.info("Initialized new Drift user account")
            except Exception as e:
                if "already in use" in str(e):
                    logger.info("User account already exists")
                else:
                    raise e
            
            # Add user and subscribe
            try:
                await self.client.add_user(0)  # Add default subaccount
                await self.client.subscribe()  # Subscribe to updates
                logger.info("Added user and subscribed to updates")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info("User already exists, subscribing to updates")
                    await self.client.subscribe()
                else:
                    raise e
            
            self.initialized = True
            logger.info("Successfully initialized Drift client")
            
        except Exception as e:
            logger.error(f"Failed to initialize Drift client: {e}")
            await self.cleanup()
            raise ExchangeError(f"Failed to initialize: {e}")
    
    def get_market_index(self, market_name: str) -> Optional[int]:
        """Get market index from market name."""
        # Try exact match first
        market_index = self.market_name_lookup.get(market_name)
        if market_index is not None:
            return market_index
            
        # Try without -PERP suffix
        base_name = market_name.replace("-PERP", "")
        return self.market_name_lookup.get(base_name)
    
    async def get_market_name(self, market_index: int) -> str:
        """Get market name from index"""
        return self.market_index_lookup.get(market_index)
    
    async def get_markets(self) -> list:
        """Get list of available markets"""
        return list(self.market_name_lookup.keys())
    
    async def get_position(self, market_name: str):
        try:
            market_index = self.get_market_index(market_name)
            if market_index is None:
                raise ValueError(f"Market not found: {market_name}")
                
            user = self.client.get_user()
            if user is None:
                raise ValueError("User account not initialized")
                
            position = user.get_perp_position(market_index)
            return position
        except Exception as e:
            logger.error(f"Error getting position: {str(e)}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup client resources."""
        if self.client:
            await self.client.unsubscribe()
            
        if self.connection:
            await self.connection.close()
            self.connection = None
        
        self.client = None
        self.keypair = None
        self.initialized = False
