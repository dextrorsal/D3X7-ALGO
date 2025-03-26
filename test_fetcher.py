#!/usr/bin/env python3
"""
Simple test script for UltimateDataFetcher    *****DRIFT SOL 1D NOT FETCHING*****
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from src.core.config import Config
from src.core.models import TimeRange
from src.ultimate_fetcher import UltimateDataFetcher
from src.utils.log_setup import setup_logging

async def main():
    # Set up logging
    setup_logging()
    logging.getLogger().setLevel(logging.INFO)
    
    # Initialize configuration from .env file
    print("Initializing config...")
    config = Config(".env")
    
    # Print available exchanges
    print("Available exchanges:")
    for exchange_name, exchange_config in config.exchanges.items():
        if exchange_config.enabled:
            print(f"  - {exchange_name} (enabled)")
        else:
            print(f"  - {exchange_name} (disabled)")
    
    # Create fetcher
    print("Creating data fetcher...")
    fetcher = UltimateDataFetcher(config)
    
    # Start fetcher
    print("Starting data fetcher...")
    await fetcher.start()
    
    try:
        # Define time range for past 7 days
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Choose one exchange and one market
        exchange = input("Enter exchange name to test (e.g., binance): ").strip()
        market = input("Enter market symbol to test (e.g., BTC-USDT): ").strip()
        resolution = input("Enter resolution (e.g., 1D, 15, 1): ").strip() or "1D"
        
        # Fetch data
        print(f"Fetching {market} data from {exchange} with {resolution} resolution...")
        print(f"Time range: {start_time.date()} to {end_time.date()}")
        
        await fetcher.fetch_historical_data(
            markets=[market],
            time_range=time_range,
            resolution=resolution,
            exchanges=[exchange]
        )
        
        print("Data fetching completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Stop fetcher
        print("Stopping data fetcher...")
        await fetcher.stop()

if __name__ == "__main__":
    asyncio.run(main()) 