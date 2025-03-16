#!/usr/bin/env python3
"""
Convert a Solana keypair JSON file to base58 format for Phantom wallet.
"""

import json
import base58
import sys
import os

def convert_keypair_to_base58(keypair_path):
    """
    Convert a Solana keypair JSON file to base58 format for Phantom wallet.
    
    Args:
        keypair_path: Path to the keypair JSON file
        
    Returns:
        Base58-encoded private key (first 32 bytes)
    """
    # Read the keypair file
    with open(os.path.expanduser(keypair_path), 'r') as f:
        keypair_json = json.load(f)
    
    # Convert the array to bytes
    keypair_bytes = bytes(keypair_json)
    
    # For Phantom wallet, we need only the first 32 bytes (private key)
    private_key_bytes = keypair_bytes[:32]
    
    # Encode to base58
    base58_key = base58.b58encode(private_key_bytes).decode('utf-8')
    
    return base58_key, str(keypair_bytes[32:])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to the standard Solana keypair location if no path provided
        keypair_path = "~/.config/solana/id.json"
        print(f"No keypair path provided, using default: {keypair_path}")
    else:
        keypair_path = sys.argv[1]
    
    private_key, public_key_part = convert_keypair_to_base58(keypair_path)
    
    print("\n=== WALLET INFORMATION ===")
    print(f"Private key for Phantom wallet (first 32 bytes):")
    print(private_key)
    print("\nIMPORTANT: Keep your private key secure! Never share it with anyone!")
    print("\nTo import into Phantom:")
    print("1. Open Phantom wallet")
    print("2. Click on the hamburger menu (top left)")
    print("3. Select 'Add/Connect Wallet'")
    print("4. Choose 'Import Private Key'")
    print("5. Paste the private key shown above")
    
    print("\nYou can also use this key in your .env file as:")
    print(f"DRIFT_PRIVATE_KEY={private_key}")