#!/usr/bin/env python3
"""
Export a Solana keypair for Phantom wallet using multiple formats.
"""

import json
import base58
import os
import subprocess
from pathlib import Path

def get_keypair_formats():
    """Get the keypair in multiple formats to try with Phantom"""
    
    keypair_path = os.path.expanduser("~/.config/solana/id.json")
    if not os.path.exists(keypair_path):
        print(f"Error: Keypair not found at {keypair_path}")
        return
    
    print(f"Using keypair from: {keypair_path}")
    
    # Method 1: Extract first 32 bytes (private key) and encode to base58
    try:
        with open(keypair_path, 'r') as f:
            keypair_json = json.load(f)
        
        keypair_bytes = bytes(keypair_json)
        private_key_bytes = keypair_bytes[:32]
        base58_private_key = base58.b58encode(private_key_bytes).decode('utf-8')
        
        print("\n=== METHOD 1: First 32 bytes as base58 ===")
        print(f"Private key: {base58_private_key}")
    except Exception as e:
        print(f"Error with Method 1: {e}")
    
    # Method 2: Use solana-keygen to recover the BIP39 passphrase
    try:
        result = subprocess.run(
            ["solana-keygen", "recover", "--force", "--outfile", "/tmp/phantom_temp.json"],
            capture_output=True,
            text=True,
            input="\n"  # Press enter for default options
        )
        
        # Read the seed phrase from the output
        output_lines = result.stderr.split('\n')
        seed_phrase = None
        for line in output_lines:
            if "recover: " in line:
                seed_phrase = line.replace("recover: ", "").strip()
                break
        
        if seed_phrase:
            print("\n=== METHOD 2: BIP39 Seed Phrase ===")
            print(f"Seed phrase: {seed_phrase}")
            print("This is the most reliable way to import into Phantom.")
            print("Use 'Import Seed Phrase' option in Phantom instead of 'Import Private Key'")
        else:
            print("Could not extract seed phrase from solana-keygen output")
    except Exception as e:
        print(f"Error with Method 2: {e}")
    
    # Method 3: Try using the entire keypair as base58
    try:
        with open(keypair_path, 'r') as f:
            keypair_json = json.load(f)
        
        keypair_bytes = bytes(keypair_json)
        full_base58 = base58.b58encode(keypair_bytes).decode('utf-8')
        
        print("\n=== METHOD 3: Full keypair as base58 ===")
        print(f"Full keypair: {full_base58}")
    except Exception as e:
        print(f"Error with Method 3: {e}")
    
    print("\n=== INSTRUCTIONS ===")
    print("Try these methods in order:")
    print("1. In Phantom, use 'Import Seed Phrase' with the seed phrase from Method 2")
    print("2. If that doesn't work, try 'Import Private Key' with the key from Method 1")
    print("3. As a last resort, try 'Import Private Key' with the full keypair from Method 3")
    print("\nIMPORTANT: Keep your private key and seed phrase secure! Never share them with anyone!")

if __name__ == "__main__":
    get_keypair_formats()