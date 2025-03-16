#!/usr/bin/env python3
"""
Export a Solana keypair specifically for Phantom wallet.
"""

import json
import base58
import os
from solders.keypair import Keypair

def export_for_phantom():
    """Export the keypair in formats that Phantom can import"""
    
    keypair_path = os.path.expanduser("~/.config/solana/id.json")
    if not os.path.exists(keypair_path):
        print(f"Error: Keypair not found at {keypair_path}")
        return
    
    # Load the keypair
    with open(keypair_path, 'r') as f:
        keypair_bytes = bytes(json.load(f))
    
    # Create a keypair object
    keypair = Keypair.from_bytes(keypair_bytes)
    
    # Get the public key
    pubkey = str(keypair.pubkey())
    
    print(f"\n=== CURRENT WALLET ===")
    print(f"Public Key: {pubkey}")
    
    # Method 1: Export as base58 private key (Phantom format)
    # Phantom expects just the private key (first 32 bytes)
    private_key_bytes = keypair_bytes[:32]
    private_key_base58 = base58.b58encode(private_key_bytes).decode('utf-8')
    
    print(f"\n=== PHANTOM IMPORT OPTIONS ===")
    print(f"Option 1 - Private Key (try this first):")
    print(private_key_base58)
    
    # Method 2: Export as JSON file
    phantom_json_path = os.path.join(os.getcwd(), "phantom_wallet.json")
    with open(phantom_json_path, 'w') as f:
        json.dump([b for b in keypair_bytes], f)
    
    print(f"\nOption 2 - JSON File:")
    print(f"File saved to: {phantom_json_path}")
    print("You can import this file directly into Phantom")
    
    # Method 3: Export as full base58 string
    full_keypair_base58 = base58.b58encode(keypair_bytes).decode('utf-8')
    
    print(f"\nOption 3 - Full Keypair as base58 (try this if Option 1 fails):")
    print(full_keypair_base58)
    
    print("\n=== INSTRUCTIONS ===")
    print("To import into Phantom:")
    print("1. Open Phantom wallet")
    print("2. Click on the hamburger menu (top left)")
    print("3. Select 'Add/Connect Wallet'")
    print("4. Choose 'Import Private Key'")
    print("5. Try pasting the key from Option 1")
    print("6. If that doesn't work, try Option 3")
    print("7. If neither works, use the JSON file from Option 2")
    
    print("\nIMPORTANT: Keep your private key secure! Never share it with anyone!")

if __name__ == "__main__":
    export_for_phantom()