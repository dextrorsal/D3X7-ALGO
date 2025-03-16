#!/usr/bin/env python3
"""
Launcher script for the live trading functionality.
This script simply imports and runs the main function from the trade.py module.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main function from the trade module
from src.scripts.trading.trade import main

if __name__ == "__main__":
    sys.exit(main())