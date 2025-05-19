#!/usr/bin/env python
"""
Fix keys by copying the JSON key file to the .enc location.
This is a temporary solution until we can identify what's loading from .enc files.
"""

import os
import shutil
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Copy JSON keys to .enc locations."""
    # Get paths from environment variables
    main_key_path = os.environ.get('MAIN_KEY_PATH', os.path.expanduser('~/.config/solana/keys/id.json'))
    main_enc_path = os.environ.get('MAIN_EC_PATH', os.path.expanduser('~/.config/solana/trading/main.enc'))
    kp_key_path = os.environ.get('KP_KEY_PATH', os.path.expanduser('~/.config/solana/keys/kp_trade.json'))
    kp_enc_path = os.path.expanduser('~/.config/solana/trading/kp_trade.enc')
    ag_key_path = os.environ.get('AG_KEY_PATH', os.path.expanduser('~/.config/solana/keys/ag_trade.json'))
    ag_enc_path = os.path.expanduser('~/.config/solana/trading/ag_trade.enc')
    
    # Ensure trading directory exists
    trading_dir = os.path.dirname(main_enc_path)
    if not os.path.exists(trading_dir):
        os.makedirs(trading_dir, exist_ok=True)
        logger.info(f"Created directory: {trading_dir}")
    
    # For each key pair, copy the JSON file to .enc location with the same content
    copy_keys(main_key_path, main_enc_path)
    copy_keys(kp_key_path, kp_enc_path)
    copy_keys(ag_key_path, ag_enc_path)
    
    logger.info("Key copying completed.")

def copy_keys(json_path, enc_path):
    """Copy a JSON key file to .enc location."""
    try:
        if not os.path.exists(json_path):
            logger.warning(f"Source key file doesn't exist: {json_path}")
            return
            
        logger.info(f"Processing: {json_path} -> {enc_path}")
        
        # Create a backup of the .enc file if it exists
        if os.path.exists(enc_path):
            backup_path = f"{enc_path}.backup"
            shutil.copy2(enc_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Read the JSON file
        with open(json_path, 'r') as f:
            key_data = json.load(f)
            
        # Write the same JSON data to the .enc file
        with open(enc_path, 'w') as f:
            json.dump(key_data, f)
            
        logger.info(f"Successfully copied key data from {json_path} to {enc_path}")
        
    except Exception as e:
        logger.error(f"Error copying {json_path} to {enc_path}: {e}")

if __name__ == "__main__":
    main() 