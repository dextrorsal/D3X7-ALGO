# Trading Mainnet Directory

This directory contains components for interacting with Solana's mainnet, focusing on secure wallet management and transaction handling for live trading.

## Directory Structure

```
mainnet/
├── __init__.py       - Module exports
├── sol_wallet.py     - Solana wallet interface (5.7KB)
├── security_limits.py       - Trading security controls
├── test_security_limits.py  - Security test suite
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

### `security_limits.py` & Testing Framework 🛡️

Our enhanced security framework for mainnet trading with comprehensive testing.

**Key Security Features:**
1. **Position Management:**
   - Market-specific position size limits
   - Default limits for new markets
   - Real-time position validation

2. **Risk Controls:**
   - Leverage limits per market
   - Daily volume tracking
   - Emergency shutdown triggers
   - Loss threshold monitoring

3. **Emergency Controls:**
   - Automatic trading suspension
   - Volume spike detection
   - Maximum drawdown protection
   - Manual override capabilities

### Visual Test Suite 🎨

The `test_security_limits.py` provides a beautiful, color-coded testing interface for security validations.

**Running Tests:**
```bash
# Install required package
pip install colorama

# Run the test suite
python3 test_security_limits.py
```

**Test Output Features:**
```
🚀 Running Security Limits Test Suite
=====================================
✅ Position Size Limits
  ├── Market-specific limits
  ├── Default market handling
  └── Size validation

✅ Leverage Controls
  ├── Per-market limits
  └── Default leverage rules

✅ Volume Tracking
  ├── Daily limits
  ├── Volume spikes
  └── Reset functionality

✅ Emergency Systems
  ├── Loss thresholds
  ├── Trading suspension
  └── Manual overrides
```

**Test Categories:**
1. **Position Size Testing:**
   - Validates market-specific limits
   - Tests default market behavior
   - Ensures proper size restrictions

2. **Leverage Validation:**
   - Verifies per-market leverage limits
   - Tests leverage calculation accuracy
   - Confirms default rules application

3. **Volume Control Testing:**
   - Daily volume limit enforcement
   - Volume spike detection
   - Automatic reset verification

4. **Emergency Systems:**
   - Loss threshold triggers
   - Trading suspension mechanics
   - Override functionality

**Visual Indicators:**
- ✅ Passed Tests (Green)
- ❌ Failed Tests (Red)
- ⚠️ Warnings (Yellow)
- 🔧 Setup Operations (Blue)
- 🧹 Cleanup Operations (Blue)

**Test Configuration:**
```python
# Example test configuration
{
    "max_position_size": {
        "SOL-PERP": 2.0,
        "BTC-PERP": 0.05
    },
    "max_leverage": {
        "SOL-PERP": 3,
        "BTC-PERP": 2
    },
    "daily_volume_limit": 5.0,
    "emergency_shutdown_triggers": {
        "loss_threshold_pct": 3.0,
        "volume_spike_multiplier": 2.0
    }
}
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

4. **Testing Practices:**
   ```python
   # GOOD: Regular test execution
   python3 test_security_limits.py
   
   # BETTER: Include in CI/CD pipeline
   pytest test_security_limits.py --html=report.html
   ```

## Integration Points

### With Jupiter Aggregator
- Transaction signing for swaps
- Balance verification
- Order execution

### With Drift Protocol
- Account management
- Position handling
- Collateral verification

### With Security Testing
- Automated validation
- Risk control verification
- Emergency system testing

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

4. **Testing Guidelines:**
   - Run security tests before deployment
   - Verify all limits are properly set
   - Test emergency procedures regularly
   - Document test results

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

4. **Running Security Tests:**
   ```bash
   # Full test suite
   python3 test_security_limits.py
   
   # Individual test categories
   python3 -m unittest test_security_limits.TestSecurityLimits.test_position_size_limits
   ```

## Notes

- All operations target Solana mainnet
- Uses real funds - handle with care
- Requires proper key management
- Supports versioned transactions
- Implements best security practices
- Regular security testing required
- Test results should be logged
- Keep test configuration updated

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

4. **Test Failures:**
   - Check test configuration
   - Verify security parameters
   - Review recent changes
   - Check log outputs