#!/usr/bin/env python3
"""
Launcher script for the data fetching functionality.
This script simply imports and runs the main function from the fetch.py module.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main function from the fetch module
from src.scripts.fetching.fetch import main

if __name__ == "__main__":
    sys.exit(main())