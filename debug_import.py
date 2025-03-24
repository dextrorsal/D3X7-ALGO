#!/usr/bin/env python
"""
Debug script to trace file opens and find what code is trying to open main.enc
"""

import os
import sys
import builtins
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Save the original open function
original_open = builtins.open

def debug_open(*args, **kwargs):
    """Wrapper around open that logs certain filenames"""
    filename = args[0] if args else kwargs.get('file', None)
    
    if filename and isinstance(filename, str) and ".enc" in filename:
        stack = traceback.extract_stack()
        caller = stack[-2]  # The caller of open
        logger.info(f"Opening file: {filename}")
        logger.info(f"Called from: {caller.filename}:{caller.lineno} in {caller.name}")
        logger.info(f"Call stack:\n{traceback.format_stack()[-10:-1]}")
    
    # Call the original open function
    return original_open(*args, **kwargs)

# Replace the built-in open function with our debug version
builtins.open = debug_open

if __name__ == "__main__":
    # Import the module that will be using the open function
    import src.scripts.fetching.fetch
    
    # Run the fetch command with minimal parameters
    sys.argv = [
        'src/scripts/fetching/fetch.py',
        'historical',
        '--days', '1',
        '--markets', 'SOL-PERP',
        '--exchanges', 'drift',
        '--resolution', '300'
    ]
    
    # Execute the main function
    src.scripts.fetching.fetch.main() 