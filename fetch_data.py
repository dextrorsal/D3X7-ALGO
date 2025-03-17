#!/usr/bin/env python3
"""
Launcher script for the data fetching functionality.
This script simply imports and runs the main function from the fetch.py module.
"""

import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main function from the fetch module
from src.utils.improved_cli import main

if __name__ == "__main__":
    try:
        # On Windows, use a different event loop policy
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run the async main function properly
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)