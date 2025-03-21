"""
Drift DEX adapter for live trading
Implements the specific functionality needed to interact with Drift protocol
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import base64
import os
from pathlib import Path
from src.utils.wallet.sol_rpc import get_solana_client

client = get_solana_client()
version_info = client.get_version()
print("Connected Solana node version:", version_info)


logger = logging.getLogger(__name__)

class DriftAdapter:
    """
    Adapter for Drift DEX protocol
    Handles the specific logic for interacting with Drift smart contracts
    """
    
    def __init__(self, config_path: str = None, keypair_path: str = None):
        """
        Initialize Drift adapter
        
        Args:
            config_path: Path to configuration file
            keypair_path: Path to Solana keypair file
        """
        self.config_path = config_path
        self.keypair_path = keypair_path
        self.connected = False
        self.client = None
        self.wallet = None
        
        # Market configuration
        self.markets = {
            "SOL-PERP": {
                "market_index": 0,
                "base_decimals": 9,
                "quote_decimals": 6
            },
            "BTC-PERP": {
                "market_index": 1,
                "base_decimals": 8,
                "quote_decimals": 6
            },
            "ETH-PERP": {
                "market_index": 2,
                "base_decimals": 8,
                "quote_decimals": 6
            }
        }
        
        # Load spot markets too
        self.spot_markets = {
            "SOL-USDC": {
                "market_index": 0,
                "base_decimals": 9,
                "quote_decimals": 6
            },
            "BTC-USDC": {
                "market_index": 1,
                "base_decimals": 8,
                "quote_decimals": 6
            },
            "ETH-USDC": {
                "market_index": 2,
                "base_decimals": 8,
                "quote_decimals": 6
            }
        }
    
    async def connect(self) -> bool:
        """
        Connect to Drift protocol
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # In a real implementation, this would import the necessary
            # dependencies and connect to the Drift protocol using the
            # official Drift Python SDK
            
            # Mock connection for demonstration
            logger.info("Connecting to Drift protocol...")
            
            # Load keypair
            if self.keypair_path and os.path.exists(self.keypair_path):
                logger.info(f"Loading keypair from {self.keypair_path}")
                # In a real implementation, this would load the keypair
                # keypair = Keypair.from_file(self.keypair_path)
                # self.wallet = keypair
            else:
                logger.warning("No keypair file found, using mock wallet")
                # Generate mock wallet with public key
                self.wallet = {"pubkey": "DRiFtXXXmockXXXwalletXXXaddressXXX"}
            
            # Connect to Drift client
            # In a real implementation, this would initialize the Drift client
            # self.client = DriftClient(
            #     keypair=self.wallet,
            #     env="mainnet"  # or "devnet" based on config
            # )
            
            # Mock client for demonstration
            self.client = {"connected": True}
            
            # Simulate connection delay
            await asyncio.sleep(1)
            
            self.connected = True
            logger.info("Connected to Drift protocol successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Drift: {e}")
            self.connected = False
            return False
    
    async def get_market_price(self, market: str) -> float:
        """
        Get current market price from Drift
        
        Args:
            market: Market symbol (e.g., "SOL-PERP" or "SOL-USDC")
            
        Returns:
            Current market price
        """
        if not self.connected:
            await self.connect()
            
        try:
            # Check if it's a perp or spot market
            market_config = None
            if market in self.markets:
                market_config = self.markets[market]
                market_type = "perp"
            elif market in self.spot_markets:
                market_config = self.spot_markets[market]
                market_type = "spot"
            else:
                raise ValueError(f"Unknown market: {market}")
                
            market_index = market_config["market_index"]
            
            # In a real implementation, this would call the Drift client
            # if market_type == "perp":
            #     price_data = await self.client.get_perp_market_price(market_index)
            # else:
            #     price_data = await self.client.get_spot_market_price(market_index)
            # return price_data.price
            
            # Mock implementation for demonstration
            # Simulate some realistic prices
            base_prices = {
                "SOL-PERP": 80.25,
                "BTC-PERP": 42500.75,
                "ETH-PERP": 2275.50,
                "SOL-USDC": 80.30,
                "BTC-USDC": 42525.25,
                "ETH-USDC": 2270.75
            }
            
            # Add small random variation to simulate price movement
            import random
            base_price = base_prices.get(market, 100.0)
            variation = random.uniform(-0.5, 0.5) / 100  # -0.5% to +0.5%
            return base_price * (1 + variation)
            
        except Exception as e:
            logger.error(f"Error getting price for {market}: {e}")
            raise
    
    async def get_account_balances(self) -> Dict[str, float]:
        """
        Get account balances from Drift
        
        Returns:
            Dictionary of token balances
        """
        if not self.connected:
            await self.connect()
            
        try:
            # In a real implementation, this would call the Drift client
            # user_account = await self.client.get_user_account()
            # balances = {}
            # for token in user_account.tokens:
            #     balances[token.symbol] = token.balance
            # return balances
            
            # Mock implementation for demonstration
            return {
                "USDC": 1000.0,
                "SOL": 10.0,
                "BTC": 0.02,
                "ETH": 0.5
            }
            
        except Exception as e:
            logger.error(f"Error getting account balances: {e}")
            raise
    
    async def get_positions(self) -> List[Dict]:
        """
        Get current open positions
        
        Returns:
            List of position details
        """
        if not self.connected:
            await self.connect()
            
        try:
            # In a real implementation, this would call the Drift client
            # positions = await self.client.get_user_positions()
            # return [p.to_dict() for p in positions]
            
            # Mock implementation for demonstration
            return []  # Empty list for no positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    async def place_spot_order(self, 
                             market: str, 
                             side: str, 
                             size: float, 
                             price: Optional[float] = None,
                             order_type: str = "market") -> Dict:
        """
        Place a spot order on Drift
        
        Args:
            market: Market symbol (e.g., "SOL-USDC")
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            price: Limit price (optional, for limit orders)
            order_type: Order type ("market" or "limit")
            
        Returns:
            Order details
        """
        if not self.connected:
            await self.connect()
            
        try:
            if market not in self.spot_markets:
                raise ValueError(f"Unknown spot market: {market}")
                
            market_config = self.spot_markets[market]
            market_index = market_config["market_index"]
            
            # Get current price if not provided
            if price is None or order_type == "market":
                price = await self.get_market_price(market)
            
            # In a real implementation, this would call the Drift client
            # order_params = {
            #     "market_index": market_index,
            #     "direction": 0 if side == "buy" else 1,  # 0 for long, 1 for short
            #     "base_asset_amount": size,
            #     "price": price,
            #     "order_type": 0 if order_type == "market" else 1,  # 0 for market, 1 for limit
            #     "reduce_only": False
            # }
            # order = await self.client.place_spot_order(order_params)
            # return order.to_dict()
            
            # Mock implementation for demonstration
            order_id = f"{side}_{market}_{int(time.time())}"
            
            # Calculate quote amount
            quote_amount = size * price
            
            # Wait to simulate order execution
            await asyncio.sleep(0.5)
            
            # Return order details
            return {
                "order_id": order_id,
                "market": market,
                "side": side,
                "size": size,
                "price": price,
                "quote_amount": quote_amount,
                "type": order_type,
                "status": "filled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing {side} order for {market}: {e}")
            raise
    
    async def place_perp_order(self, 
                             market: str, 
                             side: str, 
                             size: float, 
                             price: Optional[float] = None,
                             order_type: str = "market",
                             reduce_only: bool = False) -> Dict:
        """
        Place a perpetual futures order on Drift
        
        Args:
            market: Market symbol (e.g., "SOL-PERP")
            side: Order side ("buy" or "sell")
            size: Order size in base currency
            price: Limit price (optional, for limit orders)
            order_type: Order type ("market" or "limit")
            reduce_only: Whether the order should only reduce position
            
        Returns:
            Order details
        """
        if not self.connected:
            await self.connect()
            
        try:
            if market not in self.markets:
                raise ValueError(f"Unknown perpetual market: {market}")
                
            market_config = self.markets[market]
            market_index = market_config["market_index"]
            
            # Get current price if not provided
            if price is None or order_type == "market":
                price = await self.get_market_price(market)
            
            # In a real implementation, this would call the Drift client
            # order_params = {
            #     "market_index": market_index,
            #     "direction": 0 if side == "buy" else 1,  # 0 for long, 1 for short
            #     "base_asset_amount": size,
            #     "price": price,
            #     "order_type": 0 if order_type == "market" else 1,  # 0 for market, 1 for limit
            #     "reduce_only": reduce_only
            # }
            # order = await self.client.place_perp_order(order_params)
            # return order.to_dict()
            
            # Mock implementation for demonstration
            order_id = f"{side}_{market}_{int(time.time())}"
            
            # Calculate notional value
            notional_value = size * price
            
            # Wait to simulate order execution
            await asyncio.sleep(0.5)
            
            # Return order details
            return {
                "order_id": order_id,
                "market": market,
                "side": side,
                "size": size,
                "price": price,
                "notional_value": notional_value,
                "type": order_type,
                "reduce_only": reduce_only,
                "status": "filled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing {side} order for {market}: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            await self.connect()
            
        try:
            # In a real implementation, this would call the Drift client
            # await self.client.cancel_order(order_id)
            
            # Mock implementation for demonstration
            await asyncio.sleep(0.2)  # Simulate network delay
            
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Dict:
        """
        Get status of an order
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Order status details
        """
        if not self.connected:
            await self.connect()
            
        try:
            # In a real implementation, this would call the Drift client
            # order = await self.client.get_order(order_id)
            # return order.to_dict()
            
            # Mock implementation for demonstration
            # Parse order ID to extract details (our mock format: {side}_{market}_{timestamp})
            parts = order_id.split('_')
            if len(parts) >= 3:
                side = parts[0]
                market = parts[1]
                timestamp = int(parts[2])
                
                # Most orders are filled in our mock
                return {
                    "order_id": order_id,
                    "market": market,
                    "side": side,
                    "status": "filled",
                    "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                    "filled_size": 1.0  # Mock value
                }
            else:
                return {"order_id": order_id, "status": "unknown"}
            
        except Exception as e:
            logger.error(f"Error getting status for order {order_id}: {e}")
            raise
    
    async def close_position(self, market: str) -> Dict:
        """
        Close an open position
        
        Args:
            market: Market to close position for
            
        Returns:
            Order details from closing the position
        """
        if not self.connected:
            await self.connect()
            
        try:
            # Get current positions
            positions = await self.get_positions()
            
            # Find the position for this market
            position = None
            for p in positions:
                if p.get("market") == market:
                    position = p
                    break
                    
            if not position:
                logger.warning(f"No open position found for {market}")
                return {"status": "no_position", "market": market}
                
            # Determine side for closing
            side = "sell" if position.get("side") == "buy" else "buy"
            size = abs(position.get("size", 0))
            
            # Place order to close position
            if "PERP" in market:
                return await self.place_perp_order(
                    market=market,
                    side=side,
                    size=size,
                    reduce_only=True
                )
            else:
                return await self.place_spot_order(
                    market=market,
                    side=side,
                    size=size
                )
                
        except Exception as e:
            logger.error(f"Error closing position for {market}: {e}")
            raise
    
    async def disconnect(self):
        """
        Disconnect from Drift protocol
        """
        if self.connected:
            # In a real implementation, this would close the client connection
            # await self.client.close()
            
            # Mock implementation
            logger.info("Disconnecting from Drift protocol")
            self.connected = False
            self.client = None
    
    def __del__(self):
        """
        Clean up resources when the adapter is garbage collected
        """
        # Ensure client is disconnected
        if hasattr(self, 'connected') and self.connected:
            # We can't use await in __del__, so we just log a warning
            logger.warning("DriftAdapter was not properly disconnected")