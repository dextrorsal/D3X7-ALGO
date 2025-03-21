"""
Simple Drift DEX adapter focused on core functionality
"""

import asyncio
import logging
import os
import json
from typing import Dict, Optional, Any
from dotenv import load_dotenv

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.drift_user import DriftUser
from driftpy.types import TxParams, OrderParams, OrderType, MarketType, PositionDirection
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.config import configs
from anchorpy import Provider, Wallet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriftAdapter:
    """
    Simplified Drift DEX adapter focusing on core functionality
    """
    
    def __init__(self, network="devnet", keypair_path=None, rpc_url=None):
        """Initialize the DriftAdapter.
        
        Args:
            network (str): The network to connect to ("devnet" or "mainnet")
            keypair_path (str): Path to the keypair file
            rpc_url (str): Optional RPC URL to override environment variables
        """
        load_dotenv()
        self.network = network
        self.keypair_path = keypair_path
        
        # Set RPC endpoint based on network or override
        if rpc_url:
            self.rpc_endpoint = rpc_url
        elif network == "devnet":
            self.rpc_endpoint = os.getenv("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
        else:
            self.rpc_endpoint = os.getenv("MAINNET_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com")
        
        logger.info(f"DriftAdapter initialized for {network} using {self.rpc_endpoint}")
        
        self.connection = None
        self.client = None
        self.user = None
        self.connected = False
        
        # Default transaction parameters
        self.tx_params = TxParams(
            compute_units=700_000,
            compute_units_price=10_000
        )
    
    async def connect(self) -> bool:
        """Connect to the Solana RPC endpoint and initialize Drift client"""
        try:
            logger.info(f"Connecting to {self.network} RPC at {self.rpc_endpoint}")
            self.connection = AsyncClient(self.rpc_endpoint)
            
            # Create a temporary wallet for testing
            wallet = Wallet(Keypair())
            logger.info(f"Created temporary wallet with public key: {wallet.public_key}")
            
            # Initialize Drift client with direct parameters
            logger.info(f"Initializing DriftClient with network: {self.network}")
            self.client = DriftClient(
                connection=self.connection,
                wallet=wallet,
                env=self.network
            )
            
            # Subscribe to updates
            logger.info("Subscribing to Drift client updates...")
            await self.client.subscribe()
            logger.info("Successfully subscribed to Drift client")
            
            # Check if we can get markets
            try:
                logger.info("Attempting to fetch perp markets...")
                perp_markets = self.client.get_perp_market_accounts()
                if asyncio.iscoroutine(perp_markets):
                    perp_markets = await perp_markets
                logger.info(f"Found {len(perp_markets) if perp_markets else 0} perp markets")
                
                logger.info("Attempting to fetch spot markets...")
                spot_markets = self.client.get_spot_market_accounts()
                if asyncio.iscoroutine(spot_markets):
                    spot_markets = await spot_markets
                logger.info(f"Found {len(spot_markets) if spot_markets else 0} spot markets")
            except Exception as market_error:
                logger.error(f"Error fetching markets: {market_error}")
            
            self.connected = True
            logger.info(f"Connected to {self.network} RPC")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.network}: {e}")
            return False
    
    async def initialize(self, keypair_path=None):
        """Initialize the connection to Drift.
        
        Args:
            keypair_path (str): Path to keypair file (overrides the one set in constructor)
        """
        try:
            # Use provided keypair path or the one from constructor
            keypair_file = keypair_path or self.keypair_path or os.getenv("DEVNET_KEYPAIR_PATH")
            if not keypair_file:
                raise ValueError("No keypair file specified. Please provide a keypair_path or set DEVNET_KEYPAIR_PATH env variable.")
                
            # Connect to Solana if not already connected
            if not self.connected:
                logger.info(f"Connecting to Solana network: {self.network}")
                self.connection = AsyncClient(self.rpc_endpoint)
            
            # Load keypair from file
            logger.info(f"Loading keypair from: {keypair_file}")
            with open(keypair_file, 'r') as f:
                keypair_data = json.load(f)
                # Convert JSON array to bytes
                keypair_bytes = bytes(keypair_data)
                wallet_keypair = Keypair.from_bytes(keypair_bytes)
            logger.info(f"Loaded wallet with public key: {wallet_keypair.pubkey()}")
            
            # Initialize Drift client
            logger.info("Initializing Drift client")
            self.client = DriftClient(
                connection=self.connection,
                wallet=wallet_keypair,
                account_subscription=AccountSubscriptionConfig("websocket"),
                env=self.network,
                tx_params=self.tx_params
            )
            
            # Subscribe to updates
            logger.info("Subscribing to Drift client updates...")
            await self.client.subscribe()
            logger.info("Successfully subscribed to Drift client updates")

            # Get user account
            logger.info("Getting user account...")
            self.user = self.client.get_user()
            logger.info("Successfully initialized Drift adapter")
            
        except Exception as e:
            logger.error(f"Error initializing Drift adapter: {str(e)}")
            if self.client:
                try:
                    await self.client.unsubscribe()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
            if self.connection:
                try:
                    await self.connection.close()
                except Exception as cleanup_error:
                    logger.error(f"Error closing connection: {cleanup_error}")
            self.connection = None
            self.client = None
            self.user = None
            raise Exception(f"Error initializing Drift adapter: {str(e)}")
    
    async def place_order(self,
                        market: str,
                        side: str,
                        size: float,
                        price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a simple market/limit order
        
        Args:
            market: Market symbol (e.g. "SOL-PERP")
            side: "buy" or "sell"
            size: Order size
            price: Optional limit price (None for market orders)
            
        Returns:
            Order details
        """
        if not self.client or not self.user:
            logger.error("Drift client not initialized")
            return None
        
        try:
            # Simple market mapping
            market_index = 0  # SOL-PERP
            if market == "BTC-PERP":
                market_index = 1
            elif market == "ETH-PERP":
                market_index = 2
            
            # Create order parameters
            order_params = OrderParams(
                market_index=market_index,
                market_type=MarketType.PERP,
                direction=PositionDirection.LONG if side.lower() == "buy" else PositionDirection.SHORT,
                base_asset_amount=int(size * BASE_PRECISION),
                price=int(price * QUOTE_PRECISION) if price else None,
                order_type=OrderType.LIMIT if price else OrderType.MARKET
            )
            
            # Place order
            tx_sig = await self.client.place_order(order_params)
            
            return {
                "transaction": str(tx_sig),
                "market": market,
                "side": side,
                "size": size,
                "price": price,
                "type": "limit" if price else "market"
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise
    
    async def get_position(self, market: str) -> Dict[str, Any]:
        """
        Get current position for a market
        
        Args:
            market: Market symbol (e.g. "SOL-PERP")
            
        Returns:
            Position details
        """
        if not self.client or not self.user:
            logger.error("Drift client not initialized")
            return None
        
        try:
            # Simple market mapping
            market_index = 0  # SOL-PERP
            if market == "BTC-PERP":
                market_index = 1
            elif market == "ETH-PERP":
                market_index = 2
            
            position = self.user.get_perp_position(market_index)
            if not position:
                return {"size": 0, "entry_price": 0, "unrealized_pnl": 0}
            
            return {
                "size": position.base_asset_amount / BASE_PRECISION,
                "entry_price": position.entry_price / QUOTE_PRECISION if position.entry_price else 0,
                "unrealized_pnl": position.unrealized_pnl / QUOTE_PRECISION if position.unrealized_pnl else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting position: {str(e)}")
            raise

    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            try:
                await self.client.unsubscribe()
                logger.info("Unsubscribed from Drift client")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
        
        if self.connection:
            try:
                await self.connection.close()
                logger.info("Closed Solana connection")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")