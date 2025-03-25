"""Test Drift data provider functionality."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from solders.keypair import Keypair

from src.exchanges.drift.client import DriftClient
from src.exchanges.drift.data import DriftDataProvider
from src.core.models import TimeRange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_historical_data():
    """Test fetching historical data."""
    
    # Create dummy wallet for read-only operations
    dummy_wallet = Keypair()
    
    # Initialize client and data provider
    client = DriftClient(network="mainnet", wallet=dummy_wallet)
    data_provider = DriftDataProvider(client)
    
    # Set up time range for current and previous month
    now = datetime.now(timezone.utc)
    
    # Calculate end time (start of current month)
    end_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate start time (start of previous month)
    if end_time.month == 1:  # If January, go to December of previous year
        start_time = end_time.replace(year=end_time.year - 1, month=12)
    else:
        start_time = end_time.replace(month=end_time.month - 1)
    
    # For testing, use March 2024 data since it's more likely to exist
    test_time = datetime(2024, 3, 1, tzinfo=timezone.utc)
    start_time = test_time.replace(month=2)  # February 2024
    end_time = test_time  # March 1st, 2024
    
    logger.info(f"Fetching data from {start_time} to {end_time}")
    time_range = TimeRange(start=start_time, end=end_time)
    
    try:
        # Get available markets
        markets = await data_provider.get_markets()
        logger.info(f"Available markets: {markets}")
        
        if not markets:
            logger.error("No markets found")
            return
            
        # Test with first available market
        market = markets[0]
        logger.info(f"Testing with market: {market}")
        
        # Fetch historical candles
        candles = await data_provider.fetch_historical_candles(
            market=market,
            time_range=time_range,
            resolution="1h"
        )
        
        logger.info(f"Fetched {len(candles)} candles")
        
        # Print first few candles
        for candle in candles[:5]:
            logger.info(f"Candle: {candle}")
            
        # Test live candle
        live_candle = await data_provider.fetch_live_candle(
            market=market,
            resolution="1m"
        )
        
        if live_candle:
            logger.info(f"Live candle: {live_candle}")
        else:
            logger.warning("No live candle available")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
        
    finally:
        # Cleanup
        await data_provider.cleanup()

if __name__ == "__main__":
    asyncio.run(test_historical_data()) 