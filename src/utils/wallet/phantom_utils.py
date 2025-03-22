#!/usr/bin/env python3
"""
Unified Phantom wallet utilities for converting, exporting, and managing Solana keypairs.
Provides multiple formats and methods for importing wallets into Phantom.
"""

import json
import base58
import os
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict
from solders.keypair import Keypair
import click

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhantomWalletUtils:
    """Utility class for Phantom wallet operations"""
    
    @staticmethod
    def load_keypair(keypair_path: str) -> bytes:
        """Load keypair bytes from a JSON file"""
        with open(os.path.expanduser(keypair_path), 'r') as f:
            return bytes(json.load(f))
    
    @staticmethod
    def get_private_key(keypair_bytes: bytes) -> str:
        """Extract and encode private key (first 32 bytes) as base58"""
        private_key_bytes = keypair_bytes[:32]
        return base58.b58encode(private_key_bytes).decode('utf-8')
    
    @staticmethod
    def get_full_keypair_base58(keypair_bytes: bytes) -> str:
        """Encode full keypair as base58"""
        return base58.b58encode(keypair_bytes).decode('utf-8')
    
    @staticmethod
    def get_bip39_seed_phrase(keypair_path: str) -> Optional[str]:
        """Get BIP39 seed phrase using solana-keygen"""
        try:
            # Create a temporary file
            temp_file = "/tmp/phantom_temp.json"
            
            # Copy the wallet file to temp location
            with open(os.path.expanduser(keypair_path), 'r') as src, open(temp_file, 'w') as dst:
                dst.write(src.read())
            
            # Recover seed phrase
            result = subprocess.run(
                ["solana-keygen", "recover", "--force", f"--outfile={temp_file}"],
                capture_output=True,
                text=True,
                input="\n"
            )
            
            # Extract seed phrase from output
            for line in result.stderr.split('\n'):
                if "recover: " in line:
                    return line.replace("recover: ", "").strip()
            
            return None
        except Exception as e:
            logger.error(f"Error getting seed phrase: {e}")
            return None
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    @staticmethod
    def export_json_format(keypair_bytes: bytes, output_path: str = "phantom_wallet.json"):
        """Export keypair as JSON file"""
        with open(output_path, 'w') as f:
            json.dump([b for b in keypair_bytes], f)
        return output_path
    
    @staticmethod
    def get_wallet_info(keypair_path: str) -> Dict[str, str]:
        """Get comprehensive wallet information"""
        try:
            # Load keypair
            keypair_bytes = PhantomWalletUtils.load_keypair(keypair_path)
            keypair = Keypair.from_bytes(keypair_bytes)
            
            # Get various formats
            return {
                "public_key": str(keypair.pubkey()),
                "private_key_base58": PhantomWalletUtils.get_private_key(keypair_bytes),
                "full_keypair_base58": PhantomWalletUtils.get_full_keypair_base58(keypair_bytes),
                "seed_phrase": PhantomWalletUtils.get_bip39_seed_phrase(keypair_path)
            }
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            return {}

# CLI Commands
@click.group()
def cli():
    """Phantom wallet utilities for Solana keypair management"""
    pass

@cli.command()
@click.option('--keypair-path', '-k', 
              default="~/.config/solana/id.json",
              help='Path to keypair JSON file')
def export(keypair_path):
    """Export wallet in multiple formats for Phantom import"""
    keypair_path = os.path.expanduser(keypair_path)
    
    if not os.path.exists(keypair_path):
        click.echo(f"Error: Keypair not found at {keypair_path}")
        return
    
    click.echo(f"\nUsing keypair from: {keypair_path}")
    
    wallet_info = PhantomWalletUtils.get_wallet_info(keypair_path)
    
    if not wallet_info:
        click.echo("Error getting wallet information")
        return
    
    click.echo("\n=== WALLET INFORMATION ===")
    click.echo(f"Public Key: {wallet_info['public_key']}")
    
    click.echo("\n=== METHOD 1: Private Key (Recommended) ===")
    click.echo(f"Private key: {wallet_info['private_key_base58']}")
    
    if wallet_info.get('seed_phrase'):
        click.echo("\n=== METHOD 2: BIP39 Seed Phrase ===")
        click.echo(f"Seed phrase: {wallet_info['seed_phrase']}")
        click.echo("This is the most reliable way to import into Phantom.")
    
    click.echo("\n=== METHOD 3: Full Keypair ===")
    click.echo(f"Full keypair: {wallet_info['full_keypair_base58']}")
    
    # Export JSON format
    json_path = PhantomWalletUtils.export_json_format(
        PhantomWalletUtils.load_keypair(keypair_path)
    )
    click.echo(f"\n=== METHOD 4: JSON File ===")
    click.echo(f"Exported to: {json_path}")
    
    click.echo("\n=== IMPORT INSTRUCTIONS ===")
    click.echo("Try these methods in order:")
    click.echo("1. In Phantom, use 'Import Seed Phrase' with Method 2")
    click.echo("2. If that fails, use 'Import Private Key' with Method 1")
    click.echo("3. As a last resort, try Method 3 or the JSON file")
    click.echo("\nIMPORTANT: Keep your private keys and seed phrases secure!")

@cli.command()
@click.option('--keypair-path', '-k', 
              default="~/.config/solana/id.json",
              help='Path to keypair JSON file')
def convert(keypair_path):
    """Convert keypair to base58 format only"""
    keypair_path = os.path.expanduser(keypair_path)
    
    if not os.path.exists(keypair_path):
        click.echo(f"Error: Keypair not found at {keypair_path}")
        return
    
    try:
        keypair_bytes = PhantomWalletUtils.load_keypair(keypair_path)
        private_key = PhantomWalletUtils.get_private_key(keypair_bytes)
        
        click.echo("\n=== CONVERSION RESULT ===")
        click.echo(f"Private key (base58): {private_key}")
        click.echo("\nYou can use this key in your .env file as:")
        click.echo(f"DRIFT_PRIVATE_KEY={private_key}")
        
    except Exception as e:
        click.echo(f"Error converting keypair: {e}")

if __name__ == "__main__":
    cli() 