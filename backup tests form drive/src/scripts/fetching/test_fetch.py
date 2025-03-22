#!/usr/bin/env python3
"""
Test script for the Ultimate Data Fetcher
"""

import asyncio
import logging
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

async def test_fetch():
    """Test fetching historical data for SOL across different exchanges."""
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
        
        # Define markets and resolution
        markets = ["SOLUSDT", "SOL", "SOL-USD"]
        resolution = "15"
        
        # Get available exchanges
        available_exchanges = []
        for exchange_name, handler in fetcher.exchange_handlers.items():
            if handler:
                try:
                    # Simple test to check if the exchange handler is working
                    print(f"Testing exchange {exchange_name}...")
                    is_valid = False
                    
                    # Try with the first market
                    for market in markets:
                        try:
                            if hasattr(handler, 'validate_standard_symbol'):
                                result = handler.validate_standard_symbol(market)
                                if asyncio.iscoroutine(result):
                                    is_valid = await result
                                else:
                                    is_valid = result
                                
                                if is_valid:
                                    print(f"  ✓ Market {market} is valid on {exchange_name}")
                                    break
                            else:
                                print(f"  ✗ Exchange {exchange_name} doesn't have validate_standard_symbol method")
                        except Exception as e:
                            print(f"  ✗ Error validating {market} on {exchange_name}: {str(e)}")
                    
                    if is_valid:
                        available_exchanges.append(exchange_name)
                        print(f"  ✓ Exchange {exchange_name} is available")
                    else:
                        print(f"  ✗ Exchange {exchange_name} is not available for any of the test markets")
                except Exception as e:
                    print(f"  ✗ Error testing {exchange_name}: {str(e)}")
        
        if not available_exchanges:
            print("No exchanges are available. Please check your configuration and network connection.")
            return
        
        print(f"\nUsing available exchanges: {available_exchanges}")
        
        # Fetch historical data
        print(f"\nFetching historical data for {markets} with resolution {resolution}...")
        await fetcher.fetch_historical_data(
            markets=markets,
            time_range=time_range,
            resolution=resolution,
            exchanges=available_exchanges
        )
        
        print("\nFetch completed successfully!")
        
    finally:
        # Stop the fetcher
        await fetcher.stop()

if __name__ == "__main__":
    # On Windows, use a different event loop policy to avoid issues
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the test async function
    asyncio.run(test_fetch()) 