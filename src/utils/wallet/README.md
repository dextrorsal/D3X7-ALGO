# Wallet Utilities

This directory contains utilities for working with Solana wallets, particularly for integration with Phantom wallet.

## Utilities

- `convert_keypair_to_base58.py`: Convert a Solana keypair JSON file to base58 format for Phantom wallet
- `export_for_phantom.py`: Export a Solana keypair for Phantom wallet using multiple formats
- `phantom_export.py`: Export a Solana keypair specifically for Phantom wallet
- `extract_private_key.py`: Extract private key from Solana id.json file for importing into Phantom wallet
- `phantom_wallet.json`: Example Phantom wallet JSON file
- `phantom_import.json`: Example Phantom import JSON file

## Usage

These utilities can be run directly from the command line. For example:

```bash
# Convert a keypair to base58 format
python src/utils/wallet/convert_keypair_to_base58.py

# Export a keypair for Phantom wallet
python src/utils/wallet/export_for_phantom.py
```