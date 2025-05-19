#!/usr/bin/env python
"""
Simple script to check what wallet files exist on the system.
"""

import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Check what wallet files exist and their formats."""
    # Common wallet directories
    solana_config_dir = os.path.expanduser("~/.config/solana")
    solana_keys_dir = os.path.join(solana_config_dir, "keys")
    solana_trading_dir = os.path.join(solana_config_dir, "trading")
    
    # Print environment variables
    env_vars = [
        "MAIN_KEY_PATH", 
        "MAIN_EC_PATH", 
        "KP_KEY_PATH", 
        "AG_KEY_PATH", 
        "DRIFT_PRIVATE_KEY_PATH"
    ]
    
    logger.info("Environment variables:")
    for var in env_vars:
        value = os.environ.get(var)
        logger.info(f"{var}: {value}")
        if value and os.path.exists(value):
            logger.info(f"  File exists: {os.path.exists(value)}")
            try:
                with open(value, 'r') as f:
                    data = f.read()
                    if data.startswith('[') and data.endswith(']'):
                        logger.info(f"  Appears to be JSON array format")
                        # Try to load as JSON
                        try:
                            json_data = json.loads(data)
                            logger.info(f"  Valid JSON: {type(json_data)}")
                        except json.JSONDecodeError:
                            logger.info(f"  Invalid JSON")
                    else:
                        logger.info(f"  Not JSON array format, may be encrypted")
            except Exception as e:
                logger.info(f"  Error reading file: {e}")
    
    # Check solana config directories
    logger.info(f"\nSolana config directories:")
    logger.info(f"Main config directory ({solana_config_dir}) exists: {os.path.exists(solana_config_dir)}")
    logger.info(f"Keys directory ({solana_keys_dir}) exists: {os.path.exists(solana_keys_dir)}")
    logger.info(f"Trading directory ({solana_trading_dir}) exists: {os.path.exists(solana_trading_dir)}")
    
    # List files in each directory
    for directory in [solana_config_dir, solana_keys_dir, solana_trading_dir]:
        if os.path.exists(directory) and os.path.isdir(directory):
            logger.info(f"\nFiles in {directory}:")
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                logger.info(f"  - {file} (is_file: {os.path.isfile(file_path)})")
                
                # For .enc files, check if they can be opened
                if file.endswith('.enc') and os.path.isfile(file_path):
                    try:
                        with open(file_path, 'rb') as f:
                            data = f.read()
                            logger.info(f"    Read {len(data)} bytes, starts with: {data[:10].hex()}")
                    except Exception as e:
                        logger.info(f"    Error reading file: {e}")

if __name__ == "__main__":
    main() 