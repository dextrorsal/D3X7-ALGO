#!/usr/bin/env python3
"""
D3X7-ALGO Data Fetcher

A script to fetch data from cryptocurrency exchanges.

Example usage:
    # Show available exchanges and markets
    python fetch.py list
    
    # Fetch historical data for the last 7 days
    python fetch.py historical --days 7 --markets BTC-PERP ETH-PERP SOL-PERP --resolution 1D
    
    # Fetch historical data with specific date range
    python fetch.py historical --start-date "2023-01-01" --end-date "2023-01-31" --markets BTC-PERP --exchanges drift
    
    # Start live data fetching
    python fetch.py live --markets BTC-PERP ETH-PERP --resolution 15 --interval 30
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

# Import necessary modules
from src.core.config import Config
from src.core.models import TimeRange
from src.ultimate_fetcher import UltimateDataFetcher
from src.utils.log_setup import setup_logging

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch cryptocurrency data")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available exchanges and markets")
    
    # Historical data command
    hist_parser = subparsers.add_parser("historical", help="Fetch historical data")
    hist_parser.add_argument("--markets", nargs="+", required=True, help="Market symbols to fetch")
    hist_parser.add_argument("--exchanges", nargs="+", default=None, help="Exchanges to fetch from (default: all)")
    hist_parser.add_argument("--resolution", default="1D", help="Candle resolution (e.g., 1, 15, 60, 1D)")
    
    # Time range options (either days or start/end date)
    time_group = hist_parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument("--days", type=int, help="Number of days to fetch")
    time_group.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    
    # End date (only required if start-date is specified)
    hist_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    
    # Live data command
    live_parser = subparsers.add_parser("live", help="Fetch live data")
    live_parser.add_argument("--markets", nargs="+", required=True, help="Market symbols to fetch")
    live_parser.add_argument("--exchanges", nargs="+", default=None, help="Exchanges to fetch from (default: all)")
    live_parser.add_argument("--resolution", default="15", help="Candle resolution (e.g., 1, 15, 60, 1D)")
    live_parser.add_argument("--interval", type=int, default=60, help="Fetch interval in seconds")
    
    return parser.parse_args()

async def list_exchanges_and_markets(fetcher):
    """List all available exchanges and their markets."""
    print("\nAvailable Exchanges:")
    for name, handler in fetcher.exchange_handlers.items():
        print(f"\n{name.upper()}:")
        try:
            markets = await handler.get_markets()
            if markets:
                for market in sorted(markets):
                    print(f"  - {market}")
            else:
                print("  No markets available")
        except Exception as e:
            print(f"  Error fetching markets: {e}")

async def fetch_historical_data(fetcher, args):
    """Fetch historical data based on command line arguments."""
    # Process time range
    if args.days:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=args.days)
    else:
        start_time = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end_date:
            end_time = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            end_time = datetime.now(timezone.utc)
    
    time_range = TimeRange(start=start_time, end=end_time)
    
    print(f"\nFetching historical data:")
    print(f"Markets: {args.markets}")
    print(f"Time range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Resolution: {args.resolution}")
    if args.exchanges:
        print(f"Exchanges: {args.exchanges}")
    else:
        print("Exchanges: all available")
    
    await fetcher.fetch_historical_data(
        markets=args.markets,
        time_range=time_range,
        resolution=args.resolution,
        exchanges=args.exchanges
    )
    
    print("\nFetch completed!")

async def fetch_live_data(fetcher, args):
    """Start live data fetching based on command line arguments."""
    print(f"\nStarting live data fetching:")
    print(f"Markets: {args.markets}")
    print(f"Resolution: {args.resolution}")
    print(f"Interval: {args.interval} seconds")
    if args.exchanges:
        print(f"Exchanges: {args.exchanges}")
    else:
        print("Exchanges: all available")
    
    try:
        await fetcher.start_live_fetching(
            markets=args.markets,
            resolution=args.resolution,
            exchanges=args.exchanges,
            interval_seconds=args.interval
        )
    except KeyboardInterrupt:
        print("\nLive fetching stopped by user")

async def main():
    """Main entry point for the fetch script."""
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    setup_logging()
    
    # Print environment variables for debugging
    print(f"MAIN_KEY_PATH: {os.environ.get('MAIN_KEY_PATH')}")
    
    # Disable test mode
    os.environ['DISABLE_TEST_MODE'] = '1'
    
    # Initialize fetcher
    config = Config()
    fetcher = UltimateDataFetcher(config)
    
    # Start the fetcher
    await fetcher.start()
    
    try:
        if args.command == "list":
            await list_exchanges_and_markets(fetcher)
        elif args.command == "historical":
            await fetch_historical_data(fetcher, args)
        elif args.command == "live":
            await fetch_live_data(fetcher, args)
        else:
            print("Unknown command. Use --help for usage information.")
    finally:
        # Stop the fetcher
        await fetcher.stop()

if __name__ == "__main__":
    try:
        # On Windows, use a different event loop policy to avoid issues
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)