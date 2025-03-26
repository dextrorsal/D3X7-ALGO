#!/usr/bin/env python3
"""
Test script for directly testing Binance handler   ******Error in test: 'BinanceHandler' object has no attribute 'get_markets'******
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from src.core.config import ExchangeConfig, ExchangeCredentials
from src.core.models import TimeRange
from src.exchanges.binance.binance import BinanceHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Testing Binance Handler")
    
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