# Solana Utilities

This directory contains utilities for working with the Solana blockchain.

## Components

- **sol_rpc.py**: Solana RPC client utility for connecting to the Solana network
- **convert_keypair_to_base58.py**: Convert Solana keypair to base58 format
- **export_for_phantom.py**: Export Solana keypair for Phantom wallet
- **phantom_export.py**: Export Solana keypair for Phantom wallet
- **extract_private_key.py**: Extract private key from Solana id.json

## Usage

Import the utilities in your code:

```python
from src.utils.solana import get_solana_client

# Get a Solana client
client = get_solana_client()
```

Or run the scripts directly:

```bash
python src/utils/solana/convert_keypair_to_base58.py
```