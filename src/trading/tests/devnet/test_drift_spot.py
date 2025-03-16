#!/usr/bin/env python3
"""
Drift DEX spot trading test implementation for devnet.
Focuses on SOL, BTC, and ETH spot markets.
"""

import asyncio
import logging
from typing import Optional, Dict, List
from decimal import Decimal

from .drift_auth import DriftHelper
from driftpy.constants.spot_markets import devnet_spot_market_configs
from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    PositionDirection,
)
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from solders.keypair import Keypair

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define our supported markets
SUPPORTED_MARKETS = {
    "SOL/USDC": {"market_index": 1, "min_order_size": 0.1, "price_decimals": 3},
    "BTC/USDC": {"market_index": 2, "min_order_size": 0.0001, "price_decimals": 1},
    "ETH/USDC": {"market_index": 3, "min_order_size": 0.001, "price_decimals": 2},
    "USDC/USDC": {"market_index": 0, "min_order_size": 1.0, "price_decimals": 6}
}

class DriftSpotTester:
    def __init__(self):
        self.drift_helper = DriftHelper()
        self.drift_client = None
        self.market_configs = {}
        
    async def setup(self):
        """Initialize the Drift client and load market configs"""
        self.drift_client = await self.drift_helper.initialize_drift()
        await self._load_market_configs()
        logger.info("Spot trader initialized successfully")
        
    async def _load_market_configs(self):
        """Load and validate spot market configurations"""
        try:
            # Get all spot markets from the client
            spot_markets = self.drift_client.get_spot_market_accounts()
            
            # Map market names to their configurations
            for market in spot_markets:
                market_name = bytes(market.name).decode('utf-8').strip()
                market_index = market.market_index
                
                # Add to our configs
                for key in SUPPORTED_MARKETS:
                    base_asset = key.split('/')[0]
                    if market_name.upper() == base_asset:
                        SUPPORTED_MARKETS[key]["market_index"] = market_index
                        logger.info(f"Found {market_name} at index {market_index}")
                
                # Store the market config
                self.market_configs[market_index] = market
                
            logger.info(f"Loaded {len(self.market_configs)} market configurations")
                    
        except Exception as e:
            logger.error(f"Error loading market configs: {str(e)}")
            raise

    async def get_market_price(self, market_name: str) -> float:
        """Get current market price"""
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            if market_name not in SUPPORTED_MARKETS:
                raise ValueError(f"Unsupported market: {market_name}")
                
            market_index = SUPPORTED_MARKETS[market_name]["market_index"]
            market = self.drift_client.get_spot_market_account(market_index)
            
            # Calculate price from oracle
            oracle_price = market.historical_oracle_data.last_oracle_price / (10 ** 6)
            
            logger.info(f"Current {market_name} price: ${oracle_price:,.2f}")
            
            return oracle_price
            
        except Exception as e:
            logger.error(f"Error getting price for {market_name}: {str(e)}")
            raise

    async def place_spot_market_order(self,
                                    market_name: str,
                                    side: str,
                                    size: float) -> str:
        """
        Place a spot market order
        
        Args:
            market_name: Market symbol (e.g., "SOL/USDC")
            side: "buy" or "sell"
            size: Order size in base currency
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            if market_name not in SUPPORTED_MARKETS:
                raise ValueError(f"Unsupported market: {market_name}")
                
            # Validate minimum order size
            min_size = SUPPORTED_MARKETS[market_name]["min_order_size"]
            if size < min_size:
                raise ValueError(f"Size {size} below minimum {min_size} for {market_name}")
            
            # Convert side to direction enum
            direction = (PositionDirection.LONG if side.lower() == "buy"
                       else PositionDirection.SHORT)
            
            # Get market details
            market_index = SUPPORTED_MARKETS[market_name]["market_index"]
            market = self.drift_client.get_spot_market_account(market_index)
            
            # Convert size to proper precision
            size_in_precision = int(size * (10 ** market.decimals))
            
            # Create order parameters
            order_params = OrderParams(
                order_type=OrderType.MARKET,
                market_type=MarketType.SPOT,
                direction=direction,
                base_asset_amount=size_in_precision,
                market_index=market_index
            )
            
            # Get current price for logging
            price = await self.get_market_price(market_name)
            
            # Place the order
            logger.info(f"Placing {side} market order for {size} {market_name.split('/')[0]} " +
                       f"at ~${price:,.2f}")
            tx_sig = await self.drift_client.place_order(order_params)
            logger.info(f"Order placed successfully! Tx: {tx_sig}")
            
            # Get updated user info
            await self.drift_helper.get_user_info()
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error placing market order: {str(e)}")
            raise

    async def place_spot_limit_order(self,
                                   market_name: str,
                                   side: str,
                                   size: float,
                                   price: float) -> str:
        """
        Place a spot limit order
        
        Args:
            market_name: Market symbol (e.g., "SOL/USDC")
            side: "buy" or "sell"
            size: Order size in base currency
            price: Limit price in USDC
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            if market_name not in SUPPORTED_MARKETS:
                raise ValueError(f"Unsupported market: {market_name}")
                
            # Validate minimum order size
            min_size = SUPPORTED_MARKETS[market_name]["min_order_size"]
            if size < min_size:
                raise ValueError(f"Size {size} below minimum {min_size} for {market_name}")
            
            # Convert side to direction enum
            direction = (PositionDirection.LONG if side.lower() == "buy"
                       else PositionDirection.SHORT)
            
            # Get market details
            market_index = SUPPORTED_MARKETS[market_name]["market_index"]
            market = self.drift_client.get_spot_market_account(market_index)
            
            # Convert size to proper precision
            size_in_precision = int(size * (10 ** market.decimals))
            
            # Create order parameters
            order_params = OrderParams(
                order_type=OrderType.LIMIT,
                market_type=MarketType.SPOT,
                direction=direction,
                base_asset_amount=size_in_precision,
                market_index=market_index,
                price=int(price * 1e6)  # USDC has 6 decimals
            )
            
            # Get current market price for comparison
            market_price = await self.get_market_price(market_name)
            price_diff = ((price - market_price) / market_price) * 100
            
            # Place the order
            logger.info(f"Placing {side} limit order for {size} {market_name.split('/')[0]} " +
                       f"at ${price:,.2f} ({price_diff:+.2f}% from market)")
            tx_sig = await self.drift_client.place_order(order_params)
            logger.info(f"Order placed successfully! Tx: {tx_sig}")
            
            # Get updated user info
            await self.drift_helper.get_user_info()
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error placing limit order: {str(e)}")
            raise

    async def deposit_sol(self, amount: float) -> str:
        """
        Deposit SOL into the Drift account
        
        Args:
            amount: Amount of SOL to deposit
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            logger.info(f"Attempting to deposit {amount} SOL...")
            
            # Get the SOL market index
            market_index = SUPPORTED_MARKETS["SOL/USDC"]["market_index"]
            market = self.drift_client.get_spot_market_account(market_index)
            
            # Convert amount to proper precision
            amount_in_precision = int(amount * (10 ** market.decimals))
            
            # Execute deposit
            tx_sig = await self.drift_client.deposit(
                amount=amount_in_precision,
                spot_market_index=market_index,
                user_token_account=None  # Will use associated token account
            )
            
            logger.info(f"Deposit successful! Tx: {tx_sig}")
            
            # Get updated user info
            await self.drift_helper.get_user_info()
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error depositing SOL: {str(e)}")
            raise
            
    async def swap_tokens(self, 
                        from_market: str, 
                        to_market: str, 
                        amount: float) -> str:
        """
        Swap tokens on Drift
        
        Args:
            from_market: Source market symbol (e.g., "SOL/USDC")
            to_market: Destination market symbol (e.g., "USDC/USDC")
            amount: Amount of source token to swap
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            if from_market not in SUPPORTED_MARKETS:
                raise ValueError(f"Unsupported source market: {from_market}")
                
            if to_market not in SUPPORTED_MARKETS:
                raise ValueError(f"Unsupported destination market: {to_market}")
            
            # Get market indices
            from_market_index = SUPPORTED_MARKETS[from_market]["market_index"]
            to_market_index = SUPPORTED_MARKETS[to_market]["market_index"]
            
            # Get market details
            from_market_data = self.drift_client.get_spot_market_account(from_market_index)
            
            # Convert amount to proper precision
            amount_in_precision = int(amount * (10 ** from_market_data.decimals))
            
            logger.info(f"Swapping {amount} {from_market.split('/')[0]} to {to_market.split('/')[0]}...")
            
            # Get swap quote
            quote = await self.drift_client.get_swap_quote(
                input_mint=from_market_index,
                output_mint=to_market_index,
                input_amount=amount_in_precision,
                output_amount=0,  # We're specifying input amount, not output
                swap_mode=0  # 0 = ExactIn (we specify input amount)
            )
            
            # Log the quote details
            to_market_data = self.drift_client.get_spot_market_account(to_market_index)
            output_amount = quote.output_amount / (10 ** to_market_data.decimals)
            fee_amount = quote.fee_amount / (10 ** from_market_data.decimals)
            
            logger.info(f"Swap Quote:")
            logger.info(f"- Input: {amount} {from_market.split('/')[0]}")
            logger.info(f"- Output: {output_amount} {to_market.split('/')[0]}")
            logger.info(f"- Fee: {fee_amount} {from_market.split('/')[0]}")
            
            # Execute the swap
            tx_sig = await self.drift_client.swap(quote)
            logger.info(f"Swap successful! Tx: {tx_sig}")
            
            # Get updated user info
            await self.drift_helper.get_user_info()
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error swapping tokens: {str(e)}")
            raise

async def main():
    """Run spot trading tests"""
    tester = DriftSpotTester()
    
    try:
        await tester.setup()
        
        # Test SOL-USDC swap
        logger.info("\n=== Testing SOL to USDC Swap ===")
        amount = 0.1  # Small test amount
        logger.info(f"Attempting to swap {amount} SOL to USDC...")
        tx_sig = await tester.swap_tokens("SOL-SPOT", "USDC-SPOT", amount)
        logger.info(f"Swap successful! Transaction: {tx_sig}")
        
        # Test USDC-SOL swap
        logger.info("\n=== Testing USDC to SOL Swap ===")
        usdc_amount = 1  # 1 USDC
        logger.info(f"Attempting to swap {usdc_amount} USDC to SOL...")
        tx_sig = await tester.swap_tokens("USDC-SPOT", "SOL-SPOT", usdc_amount)
        logger.info(f"Swap successful! Transaction: {tx_sig}")
        
    except Exception as e:
        logger.error(f"Error in spot tests: {str(e)}")
        raise
    finally:
        if tester.drift_client:
            await tester.drift_client.unsubscribe()
            logger.info("Successfully unsubscribed from Drift")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}") 