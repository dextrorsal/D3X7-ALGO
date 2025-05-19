"""
Test script for DriftHandler functionality using DriftPy SDK.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from driftpy.constants.config import configs
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
        
        # Get devnet config
        config = configs["devnet"]
        
        # Set up exchange config
        exchange_config = ExchangeConfig(
            name="drift",
            base_url="https://api.devnet.solana.com",  # Use devnet URL
            rate_limit=10,  # 10 requests per second
            markets=["SOL-PERP", "BTC-PERP"],  # Example markets to test with
            credentials=ExchangeCredentials(
                api_key=None,  # Not needed for Drift
                api_secret=None
            )
        )
        
        # Initialize handler with devnet config
        handler = DriftHandler(exchange_config, wallet_manager, config)
        await handler.start()  # Start the handler
        
        # Test market validation
        valid_market = "SOL-PERP"
        invalid_market = "INVALID"
        
        logger.info("Testing market validation...")
        assert handler.validate_market(valid_market), f"Market {valid_market} should be valid"
        assert not handler.validate_market(invalid_market), f"Market {invalid_market} should be invalid"
        
        # Test getting available markets
        logger.info("Testing get_available_markets...")
        markets = await handler.get_markets()
        assert len(markets) > 0, "Should have at least one market"
        assert "SOL-PERP" in markets, "SOL-PERP should be available"
        
        # Debug: Check market account directly
        logger.info("Checking market account directly...")
        market_index = handler.client.get_market_index("SOL-PERP")
        logger.info(f"Market index for SOL-PERP: {market_index}")
        
        market_account = handler.client.client.get_perp_market_account(market_index)
        logger.info(f"Market account: {market_account}")
        
        if market_account:
            logger.info(f"Market AMM: {market_account.amm}")
            logger.info(f"Market oracle: {market_account.amm.oracle}")
        
        # Test fetching historical data
        logger.info("Testing historical data fetching...")
        # Use current time minus 24 hours to ensure we have data
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        time_range = TimeRange(start=start, end=end)
        
        logger.info(f"Fetching historical data from {start} to {end}")
        
        try:
            candles = await handler.fetch_historical_candles("SOL-PERP", time_range, "1h")
            assert len(candles) > 0, "Should have received some candles"
            logger.info(f"Received {len(candles)} candles")
            
            # Validate candle data
            for candle in candles:
                assert candle.timestamp is not None, "Candle should have timestamp"
                assert candle.open > 0, "Candle should have valid open price"
                assert candle.high >= candle.low, "High should be >= low"
                assert candle.volume >= 0, "Volume should be >= 0"
                
                # Log first candle for debugging
                if candles.index(candle) == 0:
                    logger.info(f"First candle: {candle}")
                    logger.info(f"First candle additional info: {candle.additional_info}")
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise
        
        # Test fetching live data
        logger.info("Testing live data fetching...")
        try:
            live_candle = await handler.fetch_live_candles("SOL-PERP", "1h")
            assert live_candle is not None, "Should have received a live candle"
            assert live_candle.timestamp is not None, "Live candle should have timestamp"
            assert live_candle.open > 0, "Live candle should have valid open price"
            assert live_candle.high >= live_candle.low, "High should be >= low"
            assert live_candle.volume >= 0, "Volume should be >= 0"
            logger.info(f"Successfully fetched live candle: {live_candle}")
            logger.info(f"Live candle additional info: {live_candle.additional_info}")
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
        await wallet_manager.close()

if __name__ == "__main__":
    asyncio.run(test_drift_handler()) 