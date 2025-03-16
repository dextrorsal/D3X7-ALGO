#!/usr/bin/env python3
"""
Jupiter DEX test trades implementation for devnet.
Tests Jupiter integration with Drift protocol for token swaps.
"""

import asyncio
import logging
from typing import Optional, Dict
from pathlib import Path

from .drift_auth import DriftHelper
from driftpy.constants.spot_markets import devnet_spot_market_configs
from driftpy.types import TxParams

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_market_by_symbol(symbol: str):
    """Get market config by symbol"""
    for market in devnet_spot_market_configs:
        if market.symbol == symbol:
            return market
    raise Exception(f"Market {symbol} not found")

class JupiterTestTrader:
    def __init__(self):
        self.drift_helper = DriftHelper()
        self.drift_client = None
        
    async def setup(self):
        """Initialize the Drift client for Jupiter testing"""
        self.drift_client = await self.drift_helper.initialize_drift()
        logger.info("Jupiter test trader initialized successfully")
        
    async def get_swap_quote(self,
                           in_token: str,
                           out_token: str,
                           amount: float,
                           slippage_bps: int = 100) -> Dict:
        """
        Get a swap quote from Jupiter
        
        Args:
            in_token: Input token symbol
            out_token: Output token symbol
            amount: Amount to swap in input token units
            slippage_bps: Slippage tolerance in basis points (1 bps = 0.01%)
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            # Get market indices
            in_market = get_market_by_symbol(in_token)
            out_market = get_market_by_symbol(out_token)
            
            # Get quote using Jupiter integration
            quote = await self.drift_client.get_jupiter_quote(
                in_market_index=in_market.market_index,
                out_market_index=out_market.market_index,
                amount=amount,
                slippage_bps=slippage_bps
            )
            
            logger.info(f"Got quote: {amount} {in_token} -> {quote.out_amount} {out_token}")
            logger.info(f"Price impact: {quote.price_impact:.2%}")
            
            return quote
            
        except Exception as e:
            logger.error(f"Error getting swap quote: {str(e)}")
            raise
            
    async def execute_test_swap(self,
                              in_token: str,
                              out_token: str,
                              amount: float,
                              slippage_bps: int = 100) -> str:
        """
        Execute a test token swap using Jupiter
        
        Args:
            in_token: Input token symbol
            out_token: Output token symbol
            amount: Amount to swap in input token units
            slippage_bps: Slippage tolerance in basis points
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            # Get market indices
            in_market = get_market_by_symbol(in_token)
            out_market = get_market_by_symbol(out_token)
            
            # Get swap instructions
            logger.info(f"Getting swap instructions for {amount} {in_token} -> {out_token}...")
            swap_ix, swap_lookups = await self.drift_client.get_jupiter_swap_ix_v6(
                in_market_idx=in_market.market_index,
                out_market_idx=out_market.market_index,
                amount=amount,
                slippage_bps=slippage_bps
            )
            
            # Execute swap
            logger.info("Executing swap...")
            tx_sig = await self.drift_client.send_ixs(
                ixs=swap_ix,
                lookup_tables=swap_lookups
            )
            logger.info(f"Swap executed successfully! Tx: {tx_sig}")
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error executing test swap: {str(e)}")
            raise

async def main():
    """Run some basic test swaps"""
    trader = JupiterTestTrader()
    try:
        # Initialize
        await trader.setup()
        
        # Get initial account info
        await trader.drift_helper.get_user_info()
        
        # Test a small USDC -> SOL swap
        await trader.execute_test_swap(
            in_token="USDC",
            out_token="SOL",
            amount=1.0,  # 1 USDC
            slippage_bps=100  # 1% slippage
        )
        
        # Check updated account info
        await trader.drift_helper.get_user_info()
        
        # Test a small SOL -> USDC swap
        await trader.execute_test_swap(
            in_token="SOL",
            out_token="USDC",
            amount=0.1,  # 0.1 SOL
            slippage_bps=100
        )
        
        # Final account check
        await trader.drift_helper.get_user_info()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if trader.drift_client:
            await trader.drift_client.unsubscribe()
    except Exception as e:
        logger.error(f"Error in test swaps: {str(e)}")
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