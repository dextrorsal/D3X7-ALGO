"""
Simple Drift DEX adapter focused on core functionality
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Any
from dotenv import load_dotenv

from driftpy.types import OrderParams, OrderType, MarketType, PositionDirection
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION, MARGIN_PRECISION

from src.exchanges.drift.client import DriftClient
from src.exchanges.drift.auth import DriftAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriftAdapter:
    """
    Simplified Drift DEX adapter focusing on core functionality
    """
    
    def __init__(self, network="devnet", keypair_path=None):
        """Initialize the DriftAdapter.
        
        Args:
            network (str): The network to connect to ("devnet" or "mainnet")
            keypair_path (str): Path to the keypair file
        """
        load_dotenv()
        self.network = network
        self.keypair_path = keypair_path or os.getenv("DEVNET_KEYPAIR_PATH")
        
        self.auth = None
        self.client = None
        self.connected = False
        
        logger.info(f"DriftAdapter initialized for {network}")
    
    async def connect(self) -> bool:
        """Connect to Drift and initialize client"""
        try:
            # Initialize authentication
            self.auth = DriftAuth(
                network=self.network,
                keypair_path=self.keypair_path
            )
            
            # Authenticate
            await self.auth.authenticate()
            
            # Get initialized client
            self.client = self.auth.get_client()
            if not self.client:
                raise Exception("Failed to get initialized client")
            
            self.connected = True
            logger.info(f"Connected to {self.network}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
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
        if not self.client:
            logger.error("Drift client not initialized")
            return None
        
        try:
            # Get market index from client
            market_index = self.client.market_name_lookup.get(market)
            if market_index is None:
                raise ValueError(f"Market {market} not found")
            
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
        if not self.client:
            logger.error("Drift client not initialized")
            return None
        
        try:
            # Get market index from client
            market_index = self.client.market_name_lookup.get(market)
            if market_index is None:
                raise ValueError(f"Market {market} not found")
            
            # Get position from user account
            position = await self.client.get_position(market)
            if not position:
                return {
                    "market": market,
                    "size": 0,
                    "entry_price": 0,
                    "unrealized_pnl": 0,
                    "leverage": 0
                }
            
            # Get market price
            market_price = await self.client.get_market_price(market_index)
            
            # Calculate position details
            entry_price = position.entry_price / QUOTE_PRECISION
            size = position.base_asset_amount / BASE_PRECISION
            notional_size = size * market_price
            unrealized_pnl = position.unrealized_pnl / QUOTE_PRECISION
            leverage = position.leverage / MARGIN_PRECISION if hasattr(position, 'leverage') else 0
            
            return {
                "market": market,
                "size": size,
                "entry_price": entry_price,
                "mark_price": market_price,
                "notional_size": notional_size,
                "unrealized_pnl": unrealized_pnl,
                "leverage": leverage
            }
            
        except Exception as e:
            logger.error(f"Error getting position: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.auth:
            await self.auth.cleanup()
            self.auth = None
        self.client = None
        self.connected = False
        logger.info("Cleaned up DriftAdapter resources")