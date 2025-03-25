"""
Test script for DriftHandler functionality.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from src.core.config import ExchangeConfig, ExchangeCredentials
from src.core.models import TimeRange
from src.exchanges.drift.handler import DriftHandler
from src.utils.wallet.wallet_manager import WalletManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_drift_handler():
    try:
        # Initialize wallet manager
        wallet_manager = WalletManager()
        
        # Set up exchange config
        config = ExchangeConfig(
            name="drift",
            base_url="https://mainnet.helius-rpc.com",
            rate_limit=10,  # 10 requests per second
            markets=["SOL-PERP", "BTC-PERP"],  # Example markets to test with
            credentials=ExchangeCredentials(
                api_key="fc50351b-ef76-49bd-b978-d9b9ba37ebd5",
                api_secret=None
            )
        )
        
        # Initialize handler
        handler = DriftHandler(config, wallet_manager)
        await handler.start()  # Start the handler
        
        # Test market validation
        valid_market = "SOL-PERP"
        invalid_market = "INVALID"
        
        logger.info("Testing market validation...")
        assert handler.validate_market(valid_market), f"Market {valid_market} should be valid"
        assert not handler.validate_market(invalid_market), f"Market {invalid_market} should be invalid"
        
        # Test getting available markets
        logger.info("Testing get_available_markets...")
        markets = await handler.get_markets()  # Changed from get_available_markets
        assert len(markets) > 0, "Should have at least one market"
        assert "SOL-PERP" in markets, "SOL-PERP should be available"
        
        # Test fetching historical data
        logger.info("Testing historical data fetching...")
        # Use March 15th, 2024 as a known date with data
        end = datetime(2024, 3, 15, tzinfo=timezone.utc)
        start = end - timedelta(days=1)
        time_range = TimeRange(start=start, end=end)
        
        try:
            candles = await handler.fetch_historical_candles("SOL-PERP", time_range, "1h")
            assert len(candles) > 0, "Should have received some candles"
            logger.info(f"Received {len(candles)} candles")
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise
        
        # Test fetching live data
        logger.info("Testing live data fetching...")
        try:
            live_candle = await handler.fetch_live_candles("SOL-PERP", "1h")  # Changed from fetch_live_candle
            assert live_candle is not None, "Should have received a live candle"
            logger.info("Successfully fetched live candle")
        except Exception as e:
            logger.error(f"Error fetching live data: {e}")
            raise
        
        # Test error handling for invalid market
        logger.info("Testing error handling for invalid market...")
        try:
            await handler.fetch_historical_candles("INVALID", time_range, "1h")
            assert False, "Should have raised an error for invalid market"
        except ValueError:
            logger.info("Successfully caught invalid market error")
        
        # Test error handling for invalid resolution
        logger.info("Testing error handling for invalid resolution...")
        try:
            await handler.fetch_historical_candles("SOL-PERP", time_range, "INVALID")
            assert False, "Should have raised an error for invalid resolution"
        except ValueError:
            logger.info("Successfully caught invalid resolution error")
        
        logger.info("All tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Cleanup
        if 'handler' in locals():
            await handler.stop()
        await wallet_manager.close()  # Added await

if __name__ == "__main__":
    asyncio.run(test_drift_handler()) 