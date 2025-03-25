#!/usr/bin/env python3
"""
Standalone test script for Binance handler that avoids import issues
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Define minimal required classes to avoid importing problematic modules
class TimeRange:
    """Minimal TimeRange class to avoid imports"""
    def __init__(self, start, end):
        self.start = start
        self.end = end

class StandardizedCandle:
    """Minimal StandardizedCandle class to test the handler"""
    def __init__(self, timestamp, open, high, low, close, volume, market, resolution, source, 
                 trade_count=None, additional_info=None):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.market = market
        self.resolution = resolution
        self.source = source
        self.trade_count = trade_count
        self.additional_info = additional_info or {}

class ExchangeCredentials:
    """Simple credentials class"""
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET', '')

class ExchangeConfig:
    """Simplified config class"""
    def __init__(self, name, credentials=None, rate_limit=5, markets=None, base_url=None, enabled=True):
        self.name = name
        self.credentials = credentials or ExchangeCredentials()
        self.rate_limit = rate_limit
        self.markets = markets or []
        self.base_url = base_url
        self.enabled = enabled

class BaseExchangeHandler:
    """Minimal BaseExchangeHandler to avoid imports"""
    def __init__(self, config):
        self.config = config
        self.name = config.name
        self.credentials = config.credentials
        self.rate_limit = config.rate_limit
        self.markets = config.markets
        self.base_url = config.base_url
    
    async def start(self):
        """Start handler"""
        logger.info(f"Started {self.name} exchange handler")
    
    async def stop(self):
        """Stop handler"""
        logger.info(f"Stopped {self.name} exchange handler")

# Import exceptions
class ExchangeError(Exception):
    """Base error for exchange-related issues"""
    pass

class RateLimitError(ExchangeError):
    """Rate limit exceeded error"""
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

# Now we can safely import the BinanceHandler
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now, let's modify the BinanceHandler class to use our simplified base classes
from src.exchanges.binance.binance import BinanceHandler as OriginalBinanceHandler

# Override imports in the binance module
sys.modules['src.core.models'] = type('models', (), {
    'StandardizedCandle': StandardizedCandle,
    'TimeRange': TimeRange,
})

sys.modules['src.core.exceptions'] = type('exceptions', (), {
    'ExchangeError': ExchangeError,
    'RateLimitError': RateLimitError,
})

sys.modules['src.exchanges.base'] = type('base', (), {
    'BaseExchangeHandler': BaseExchangeHandler,
    'ExchangeConfig': ExchangeConfig,
})

# Now define our test function
async def test_binance():
    """Test Binance handler functionality"""
    logger.info("Testing Binance Handler")
    
    try:
        # Create a simple configuration for Binance
        exchange_config = ExchangeConfig(
            name="binance",
            credentials=ExchangeCredentials(),
            rate_limit=5,
            markets=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            base_url="https://api.binance.com",
            enabled=True
        )
        
        # Initialize the handler with our config
        handler = OriginalBinanceHandler(exchange_config)
        
        # Start the handler
        logger.info("Starting Binance handler")
        await handler.start()
        logger.info("Successfully started Binance handler")
        
        try:
            # Test market validation
            test_markets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "INVALID"]
            logger.info("Testing market validation...")
            for market in test_markets:
                is_valid = handler.validate_market(market)
                logger.info(f"Market {market} is {'valid' if is_valid else 'invalid'}")
            
            # Define a time range for testing
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
            time_range = TimeRange(start=start_time, end=end_time)
            
            # Test ticker functionality using the client directly
            logger.info("Testing ticker data...")
            ticker_data = handler.client.ticker_24hr("BTCUSDT")
            logger.info(f"BTC/USDT 24hr Ticker: Price: ${float(ticker_data['lastPrice']):.2f}, Volume: {float(ticker_data['volume']):.2f} BTC")
            
            # Fetch some candles
            logger.info(f"Fetching BTC/USDT candles from {start_time} to {end_time}")
            try:
                candles = await handler.fetch_historical_candles(
                    market="BTCUSDT",
                    time_range=time_range,
                    resolution="1h"
                )
                
                if candles:
                    logger.info(f"Successfully fetched {len(candles)} candles")
                    if len(candles) > 0:
                        sample = candles[0]
                        logger.info(f"Sample candle: timestamp={sample.timestamp}, open={sample.open}, close={sample.close}")
                else:
                    logger.warning("No candles returned")
            except Exception as e:
                logger.error(f"Error fetching candles: {e}")
                
        finally:
            # Stop the handler
            logger.info("Stopping Binance handler")
            await handler.stop()
            logger.info("Successfully stopped Binance handler")
            
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_binance()) 