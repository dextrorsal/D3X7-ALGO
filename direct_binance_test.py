#!/usr/bin/env python3
"""
Direct test script for Binance handler without loading other exchange modules
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# This prevents the entire src.exchanges module from being loaded
# which would trigger the solana/solders keypair import error in drift.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import only what we need directly
from src.core.config import ExchangeConfig, ExchangeCredentials
from src.core.models import TimeRange

# Direct import of BinanceHandler from file
# This avoids loading __init__.py which imports all exchange handlers
sys.modules['src.exchanges'] = type('MockModule', (), {})
sys.modules['src.exchanges.base'] = type('MockModule', (), {})

# Import BaseExchangeHandler directly
from src.exchanges.base import BaseExchangeHandler
# Now import BinanceHandler 
from src.exchanges.binance import BinanceHandler

async def main():
    logger.info("Testing Binance Handler directly")
    
    try:
        # Create a simple configuration for Binance
        exchange_config = ExchangeConfig(
            name="binance",
            credentials=ExchangeCredentials(),  # Empty credentials for public API
            rate_limit=5,
            markets=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            base_url="https://api.binance.com",
            enabled=True
        )
        
        # Initialize the exchange handler
        handler = BinanceHandler(exchange_config)
        
        # Connect to the exchange
        logger.info("Starting Binance handler")
        await handler.start()
        logger.info("Successfully connected to Binance")
        
        try:
            # Test getting markets
            logger.info("Getting available markets from Binance...")
            markets = await handler.get_markets()
            logger.info(f"Found {len(markets)} markets. First 5: {markets[:5]}")
            
            # Define a time range for the last 2 days
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=2)
            time_range = TimeRange(start=start_time, end=end_time)
            
            # Try to fetch candles for BTC/USDT
            logger.info(f"Fetching BTC/USDT data from {start_time} to {end_time}")
            candles = await handler.fetch_historical_candles(
                market="BTCUSDT",
                time_range=time_range,
                resolution="1h"  # 1-hour timeframe
            )
            
            if candles and len(candles) > 0:
                logger.info(f"Successfully fetched {len(candles)} candles")
                # Print sample data from first candle
                sample = candles[0]
                logger.info(f"Sample candle: timestamp={sample.timestamp}, open={sample.open}, close={sample.close}")
            else:
                logger.warning("No candles fetched")
                
        finally:
            # Disconnect from the exchange
            logger.info("Stopping Binance handler")
            await handler.stop()
            logger.info("Disconnected from Binance")
    
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 