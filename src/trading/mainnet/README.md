# Trading Mainnet Directory

This directory contains components for interacting with Solana's mainnet, focusing on secure wallet management and transaction handling for live trading.

## Directory Structure

```
mainnet/
├── __init__.py       - Module exports
├── sol_wallet.py     - Solana wallet interface (5.7KB)
└── README.md        - This file
```

## Component Details

### `sol_wallet.py`

Core wallet management system for Solana mainnet operations.

**Key Features:**
1. **Wallet Management:**
   - Keypair loading and creation
   - Transaction signing
   - Message signing
   - Public key management

2. **Security:**
   - Environment variable support
   - Multiple key loading methods
   - Secure keypair handling
   - Error handling and logging

**Usage Example:**
```python
from src.trading.mainnet import SolanaWallet

# Initialize wallet
wallet = SolanaWallet(keypair_path="~/.config/solana/id.json")

# Get public key
pubkey = wallet.get_public_key()

# Sign a transaction
signed_tx = wallet.sign_transaction(transaction_data)

# Sign a message
signature = wallet.sign_message("Hello Solana")

# Create new keypair
pubkey, privkey = SolanaWallet.create_new_keypair("new_wallet.json")
```

## Configuration

### 1. Environment Variables
```bash
# Required
PRIVATE_KEY_PATH="/path/to/keypair.json"  # Path to keypair file
# OR
PRIVATE_KEY="[...]"  # Direct private key (JSON array or base58)

# Optional
SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"  # Custom RPC endpoint
```

### 2. Keypair Formats
1. **JSON File:**
   ```json
   [1,2,3,...,64]  // 64-byte array
   ```

2. **Environment Variable:**
   - JSON array
   - Base58-encoded string

## Security Best Practices

1. **Private Key Management:**
   ```python
   # GOOD: Load from environment or secure file
   wallet = SolanaWallet(keypair_path=os.getenv("PRIVATE_KEY_PATH"))
   
   # BAD: Hardcode private key
   wallet = SolanaWallet(keypair_path="my_private_key.json")
   ```

2. **File Permissions:**
   - Set restrictive permissions on keypair files
   - Use secure directories
   - Never commit private keys

3. **Environment Variables:**
   - Use `.env` files
   - Keep sensitive data out of code
   - Rotate keys regularly

## Integration Points

### With Jupiter Aggregator
- Transaction signing for swaps
- Balance verification
- Order execution

### With Drift Protocol
- Account management
- Position handling
- Collateral verification

## Error Handling

```python
try:
    wallet = SolanaWallet()
    signed_tx = wallet.sign_transaction(tx_data)
except ValueError as e:
    logger.error(f"Wallet error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Dependencies

1. **Required:**
   - `solana`: Solana web3 library
   - `base64`: Encoding utilities
   - `python-dotenv`: Environment management

2. **Optional:**
   - `logging`: Error tracking
   - `typing`: Type hints

## Development Guidelines

1. **Testing:**
   - Use devnet for testing
   - Never test with real funds
   - Verify signatures offline

2. **Deployment:**
   - Double-check RPC endpoints
   - Verify network connections
   - Monitor transaction status

3. **Maintenance:**
   - Keep dependencies updated
   - Monitor for vulnerabilities
   - Back up keypairs securely

## Common Operations

1. **Creating New Wallets:**
   ```python
   # Generate new keypair
   pubkey, privkey = SolanaWallet.create_new_keypair("new_wallet.json")
   ```

2. **Loading Existing Wallets:**
   ```python
   # From file
   wallet = SolanaWallet(keypair_path="existing_wallet.json")
   
   # From environment
   wallet = SolanaWallet()  # Uses PRIVATE_KEY or PRIVATE_KEY_PATH
   ```

3. **Transaction Signing:**
   ```python
   # Sign transaction
   signed = wallet.sign_transaction({
       "recent_blockhash": "...",
       "instructions": [...]
   })
   ```

## Notes

- All operations target Solana mainnet
- Uses real funds - handle with care
- Requires proper key management
- Supports versioned transactions
- Implements best security practices

## Troubleshooting

1. **Keypair Loading Issues:**
   - Check file permissions
   - Verify file format
   - Confirm environment variables

2. **Transaction Errors:**
   - Verify RPC connection
   - Check account balances
   - Monitor network status

3. **Security Alerts:**
   - Review access logs
   - Check for unauthorized access
   - Monitor transaction history