#!/usr/bin/env python3
"""
Drift DEX test trades implementation for devnet.
Implements test trading functionality using the Drift protocol on devnet.
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

from .drift_auth import DriftHelper
from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    PositionDirection,
    TxParams
)
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DriftTestTrader:
    def __init__(self):
        self.drift_helper = DriftHelper()
        self.drift_client = None
        
    async def setup(self):
        """Initialize the Drift client for testing"""
        self.drift_client = await self.drift_helper.initialize_drift()
        logger.info("Test trader initialized successfully")
        
    async def place_test_market_order(self, 
                                    market_index: int,
                                    direction: str,
                                    size: float) -> str:
        """
        Place a test market order
        
        Args:
            market_index: The market index to trade
            direction: "long" or "short"
            size: Order size in base currency
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            # Convert direction string to enum
            position_direction = (PositionDirection.Long() if direction.lower() == "long" 
                               else PositionDirection.Short())
            
            # Create order parameters
            order_params = OrderParams(
                order_type=OrderType.Market(),
                market_type=MarketType.Perp(),
                direction=position_direction,
                base_asset_amount=int(size * BASE_PRECISION),
                market_index=market_index
            )
            
            # Place the order
            logger.info(f"Placing {direction} market order for {size} contracts...")
            tx_sig = await self.drift_client.place_order(order_params)
            logger.info(f"Order placed successfully! Tx: {tx_sig}")
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error placing test order: {str(e)}")
            raise

    async def place_test_limit_order(self,
                                   market_index: int,
                                   direction: str,
                                   size: float,
                                   price: float) -> str:
        """
        Place a test limit order
        
        Args:
            market_index: The market index to trade
            direction: "long" or "short"
            size: Order size in base currency
            price: Limit price
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            # Convert direction string to enum
            position_direction = (PositionDirection.Long() if direction.lower() == "long" 
                               else PositionDirection.Short())
            
            # Create order parameters
            order_params = OrderParams(
                order_type=OrderType.Limit(),
                market_type=MarketType.Perp(),
                direction=position_direction,
                base_asset_amount=int(size * BASE_PRECISION),
                market_index=market_index,
                price=int(price * QUOTE_PRECISION)
            )
            
            # Place the order
            logger.info(f"Placing {direction} limit order for {size} contracts at {price}...")
            tx_sig = await self.drift_client.place_order(order_params)
            logger.info(f"Order placed successfully! Tx: {tx_sig}")
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error placing test order: {str(e)}")
            raise

async def main():
    """Run some basic test trades"""
    trader = DriftTestTrader()
    try:
        # Initialize
        await trader.setup()
        
        # Get initial account info
        await trader.drift_helper.get_user_info()
        
        # Place a small test market order
        await trader.place_test_market_order(
            market_index=0,  # SOL-PERP
            direction="long",
            size=0.1  # Small size for testing
        )
        
        # Check updated account info
        await trader.drift_helper.get_user_info()
        
        # Place a test limit order
        current_price = 80  # You would normally get this from the market
        await trader.place_test_limit_order(
            market_index=0,  # SOL-PERP
            direction="short",
            size=0.1,
            price=current_price * 1.02  # 2% above current price
        )
        
        # Final account check
        await trader.drift_helper.get_user_info()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if trader.drift_client:
            await trader.drift_client.unsubscribe()
    except Exception as e:
        logger.error(f"Error in test trades: {str(e)}")
        if trader.drift_client:
            await trader.drift_client.unsubscribe()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}") 