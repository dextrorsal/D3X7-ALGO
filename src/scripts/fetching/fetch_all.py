#!/usr/bin/env python3
"""
Script to fetch data from Drift exchange with SOL-PERP market.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

from src.core.config import Config
from src.core.models import TimeRange
from src.ultimate_fetcher import UltimateDataFetcher
from src.utils.log_setup import setup_logging
import logging

async def fetch_drift_data():
    """Fetch SOL-PERP data from Drift exchange."""
    # Setup logging
    setup_logging()
    logging.getLogger().setLevel(logging.INFO)
    
    # Print environment variables for debugging
    print(f"MAIN_KEY_PATH: {os.environ.get('MAIN_KEY_PATH', 'Not set')}")
    
    # Initialize fetcher with config
    config = Config(".env")
    fetcher = UltimateDataFetcher(config)
    
    # Start the fetcher
    await fetcher.start()
    
    try:
        # Define time range (last 365 days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=365)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Define resolution (30 minutes)
        resolution = "30"
        
        # Define market (just SOL-PERP)
        markets = ["SOL-PERP"]
        
        # Define exchanges (just drift)
        exchanges = ["drift"]
        
        print(f"\nFetching SOL-PERP data from Drift for the last 365 days with 30-minute resolution")
        
        # Check if the drift handler is available
        if "drift" in fetcher.exchange_handlers:
            # Fetch historical data
            await fetcher.fetch_historical_data(
                markets=markets,
                time_range=time_range,
                resolution=resolution,
                exchanges=exchanges
            )
            
            print("\nFetch completed!")
        else:
            print("\n✗ Drift exchange not available")
        
    finally:
        # Stop the fetcher
        await fetcher.stop()

if __name__ == "__main__":
    # On Windows, use a different event loop policy to avoid issues
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the fetch async function
    asyncio.run(fetch_drift_data()) 