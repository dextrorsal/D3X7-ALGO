#!/usr/bin/env python3
"""
Script to fetch data from all exchanges with the correct symbols for each.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

from src.core.config import Config
from src.core.models import TimeRange
from src.ultimate_fetcher import UltimateDataFetcher
from src.utils.log_setup import setup_logging
import logging

async def fetch_all_exchanges():
    """Fetch data from all exchanges with the correct symbols for each."""
    # Setup logging
    setup_logging()
    logging.getLogger().setLevel(logging.INFO)
    
    # Initialize fetcher with config
    config = Config(".env")
    fetcher = UltimateDataFetcher(config)
    
    # Start the fetcher
    await fetcher.start()
    
    try:
        # Define time range (last 7 days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Define resolution
        resolution = "15"
        
        # Define exchange-specific markets
        exchange_markets = {
            "binance": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "coinbase": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "drift": ["SOL", "BTC", "ETH", "SOL-PERP", "BTC-PERP", "ETH-PERP"]
        }
        
        # Fetch data for each exchange with its specific markets
        for exchange_name, markets in exchange_markets.items():
            if exchange_name in fetcher.exchange_handlers:
                print(f"\nFetching data for {exchange_name.upper()} with markets: {markets}")
                
                # Check if the exchange handler is working
                handler = fetcher.exchange_handlers.get(exchange_name)
                if not handler:
                    print(f"  ✗ Exchange {exchange_name} not initialized, skipping")
                    continue
                
                # Try to fetch data for each market
                for market in markets:
                    try:
                        print(f"  Fetching {market} from {exchange_name}...")
                        
                        # Validate the market
                        is_valid = False
                        try:
                            if hasattr(handler, 'validate_standard_symbol'):
                                result = handler.validate_standard_symbol(market)
                                if asyncio.iscoroutine(result):
                                    is_valid = await result
                                else:
                                    is_valid = result
                            else:
                                is_valid = handler.validate_market(market)
                        except Exception as e:
                            print(f"  ✗ Error validating {market}: {str(e)}")
                            continue
                        
                        if not is_valid:
                            print(f"  ✗ Market {market} not supported by {exchange_name}, skipping")
                            continue
                        
                        # Fetch historical data
                        candles = await handler.fetch_historical_candles(market, time_range, resolution)
                        
                        if not candles:
                            print(f"  ✗ No data returned for {market}")
                            continue
                        
                        # Store the data
                        await fetcher.raw_storage.store_candles(
                            exchange_name,
                            market,
                            resolution,
                            candles
                        )
                        
                        await fetcher.processed_storage.store_candles(
                            exchange_name,
                            market,
                            resolution,
                            candles
                        )
                        
                        print(f"  ✓ Stored {len(candles)} candles for {market}")
                        
                    except Exception as e:
                        print(f"  ✗ Error fetching {market}: {str(e)}")
            else:
                print(f"\n✗ Exchange {exchange_name} not available")
        
        print("\nFetch completed!")
        
    finally:
        # Stop the fetcher
        await fetcher.stop()

if __name__ == "__main__":
    # On Windows, use a different event loop policy to avoid issues
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the fetch async function
    asyncio.run(fetch_all_exchanges()) 