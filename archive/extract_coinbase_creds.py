#!/usr/bin/env python3
"""
Script to extract Coinbase API credentials from key file and add them to .env file.
"""

import os
import json
import logging
from dotenv import load_dotenv, set_key, find_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_credentials(key_path):
    """Load API credentials from JSON file."""
    try:
        with open(key_path, 'r') as f:
            creds = json.load(f)
        return creds.get('name'), creds.get('privateKey')
    except Exception as e:
        logger.error(f"Failed to load credentials from {key_path}: {e}")
        return None, None

def main():
    # Load environment variables
    load_dotenv()
    
    # Try both key paths
    key_paths = [
        os.getenv("CDP_KEY_PATH"),
        os.getenv("CDP_KEY_PATH2")
    ]
    
    # Try each key path
    for key_path in key_paths:
        if not key_path:
            continue
            
        logger.info(f"Trying credentials from: {key_path}")
        api_key, api_secret = load_credentials(key_path)
        
        if not api_key or not api_secret:
            logger.warning(f"Could not load credentials from {key_path}")
            continue
        
        # Write to .env file
        dotenv_path = find_dotenv()
        if not dotenv_path:
            dotenv_path = os.path.join(os.getcwd(), '.env')
            logger.info(f"Creating new .env file at {dotenv_path}")
            with open(dotenv_path, 'a'):
                pass
                
        # Set the environment variables in the .env file
        logger.info(f"Writing API credentials to {dotenv_path}")
        set_key(dotenv_path, "COINBASE_API_KEY", api_key)
        set_key(dotenv_path, "COINBASE_API_SECRET", api_secret)
        
        logger.info("✅ Successfully added Coinbase API credentials to .env file")
        return True
            
    logger.error("Could not find valid API credentials in any of the key files")
    return False

if __name__ == "__main__":
    main() 