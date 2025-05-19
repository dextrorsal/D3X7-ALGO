#!/usr/bin/env python
"""
Debug script to check how the keypair path is being resolved.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Examine keypair paths from environment variables."""
    # Get all environment variables related to keypaths
    logger.info(f"MAIN_KEY_PATH: {os.environ.get('MAIN_KEY_PATH')}")
    logger.info(f"MAIN_EC_PATH: {os.environ.get('MAIN_EC_PATH')}")
    logger.info(f"PRIVATE_KEY_PATH: {os.environ.get('PRIVATE_KEY_PATH')}")
    
    # Check if the file exists
    main_key_path = os.environ.get('MAIN_KEY_PATH')
    if main_key_path:
        logger.info(f"File exists at MAIN_KEY_PATH: {os.path.exists(main_key_path)}")
        
        if os.path.exists(main_key_path):
            try:
                with open(main_key_path, 'r') as f:
                    content = f.read()
                    logger.info(f"File content type: {type(content)}")
                    logger.info(f"File content snippet: {content[:50]}...")
                    
                    # Try parsing as JSON
                    try:
                        data = json.loads(content)
                        logger.info(f"Parsed JSON successfully: {type(data)}")
                    except json.JSONDecodeError:
                        logger.info("Not valid JSON")
            except Exception as e:
                logger.error(f"Error reading file: {e}")
    
    # Check the trading config path
    trading_config_dir = os.path.expanduser("~/.config/solana/trading")
    main_enc_path = os.path.join(trading_config_dir, "main.enc")
    logger.info(f"main.enc path: {main_enc_path}")
    logger.info(f"File exists at main.enc path: {os.path.exists(main_enc_path)}")
    
    # Check the current working directory and Python path
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path}")
    
    # Check which wallet_manager module is being imported
    try:
        import importlib
        wallet_manager_spec = importlib.util.find_spec("src.utils.wallet.wallet_manager")
        logger.info(f"wallet_manager module location: {wallet_manager_spec.origin if wallet_manager_spec else 'Not found'}")
    except Exception as e:
        logger.error(f"Error checking module location: {e}")

if __name__ == "__main__":
    main()