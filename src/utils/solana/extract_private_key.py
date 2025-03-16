#!/usr/bin/env python3
"""
Simple script to extract private key from Solana id.json file
for importing into Phantom wallet.
"""

import json
import os
import base58
from solders.keypair import Keypair

def extract_private_key():
    # Load keypair from default location
    keypair_path = os.path.expanduser("~/.config/solana/id.json")
    
    if not os.path.exists(keypair_path):
        print(f"Error: Keypair not found at {keypair_path}")
        return
    
    try:
        # Load the keypair bytes
        with open(keypair_path, 'r') as f:
            keypair_bytes = bytes(json.load(f))
        
        # Create a keypair object
        keypair = Keypair.from_bytes(keypair_bytes)
        
        # Get the public key in base58 format
        pubkey = keypair.pubkey()
        pubkey_base58 = str(pubkey)
        
        # Get the private key in base58 format (first 32 bytes of the keypair)
        # This is what Phantom wallet expects
        private_key_bytes = keypair_bytes[:32]
        private_key_base58 = base58.b58encode(private_key_bytes).decode('ascii')
        
        print("\n=== WALLET INFORMATION ===")
        print(f"Public Key: {pubkey_base58}")
        print(f"Private Key (for Phantom import): {private_key_base58}")
        print("\nIMPORTANT: Keep your private key secure! Never share it with anyone!")
        print("To import into Phantom:")
        print("1. Open Phantom wallet")
        print("2. Click on the hamburger menu (top left)")
        print("3. Select 'Add/Connect Wallet'")
        print("4. Choose 'Import Private Key'")
        print("5. Paste the private key shown above")
        
    except Exception as e:
        print(f"Error extracting private key: {e}")

if __name__ == "__main__":
    extract_private_key()