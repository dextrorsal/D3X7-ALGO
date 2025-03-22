#!/usr/bin/env python3
"""
D3X7-ALGO Data Fetcher

A script to fetch data from cryptocurrency exchanges.

Example usage:
    # Show available exchanges and markets
    python fetch.py data list
    
    # Fetch historical data for the last 7 days
    python fetch.py data fetch --mode historical --markets BTC-PERP ETH-PERP SOL-PERP --resolution 1D
    
    # Fetch historical data with specific date range
    python fetch.py data fetch --mode historical --markets BTC-PERP --start-time "2023-01-01" --end-time "2023-01-31"
    
    # Start live data fetching
    python fetch.py data fetch --mode live --markets BTC-PERP ETH-PERP --resolution 15
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

# Import the main function from the new CLI package
from src.cli import main

if __name__ == "__main__":
    try:
        # On Windows, use a different event loop policy to avoid issues
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Disable test mode globally
        os.environ['DISABLE_TEST_MODE'] = '1'
        
        # Prepend 'data' command if not provided
        if len(sys.argv) == 1 or sys.argv[1] not in ['data', 'wallet', 'trade']:
            sys.argv.insert(1, 'data')
        
        # Run the main CLI
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)