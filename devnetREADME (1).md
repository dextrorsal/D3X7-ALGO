# Devnet Testing Environment

This directory contains components for testing and development on Solana's devnet, with a focus on Drift Protocol integration.

## Directory Structure

```
/src/trading/
├── devnet/                # Devnet components
│   ├── __init__.py       # Module exports
│   ├── drift_auth.py     # Drift authentication
│   ├── check_jupiter_devnet.py  # Jupiter testing
│   └── README.md         # This file
└── tests/
    └── devnet/           # Devnet test suite
        ├── test_drift_auth.py
        ├── test_drift_account_manager.py
        └── test_drift_setup.py
```

## Quick Start

Run tests from the project root:

```bash
# Test authentication
python -m pytest src/trading/tests/devnet/test_drift_auth.py

# Test account management
python -m pytest src/trading/tests/devnet/test_drift_account_manager.py

# Test setup
python -m pytest src/trading/tests/devnet/test_drift_setup.py
```

## Component Details

### 1. Drift Authentication (`drift_auth.py`)

Core authentication and client initialization for Drift Protocol on devnet.

**Key Features:**
- Secure wallet loading and management
- RPC connection setup with retry logic
- User account initialization and verification
- Balance tracking and PnL calculation
- Safe transaction handling

**Usage Example:**
```python
from src.trading.devnet.drift_auth import DriftHelper

async def example():
    helper = DriftHelper()
    
    # Initialize with devnet configuration
    drift_client = await helper.initialize_drift()
    
    try:
        # Get user account information
        user_info = await helper.get_user_info()
        print(f"Account Balance: {user_info['total_collateral']}")
    finally:
        await drift_client.unsubscribe()
```

### 2. Jupiter Testing (`check_jupiter_devnet.py`)

Tests Jupiter integration on devnet for swap functionality.

**Key Features:**
- Price quote fetching
- Swap route optimization
- Transaction simulation
- Slippage protection

## Environment Setup

### Prerequisites
1. **Solana CLI Tools:**
   ```bash
   sh -c "$(curl -sSfL https://release.solana.com/v1.17.9/install)"
   ```

2. **Devnet Account:**
   ```bash
   solana-keygen new --outfile ~/.config/solana/devnet.json
   solana config set --url devnet
   solana airdrop 2 # Get devnet SOL
   ```

### Configuration
Required environment variables:
```bash
export DEVNET_RPC_URL="https://api.devnet.solana.com"
export DEVNET_WALLET_PATH="~/.config/solana/devnet.json"
```

## Testing Framework

### Test Organization
1. **Authentication Tests:**
   - Wallet loading
   - Client initialization
   - Connection management

2. **Account Management Tests:**
   - Deposit functionality
   - Balance checking
   - Position management

3. **Setup Tests:**
   - Market initialization
   - Account creation
   - Permission verification

### Running Tests
```bash
# Run all devnet tests
python -m pytest src/trading/tests/devnet/

# Run specific test file
python -m pytest src/trading/tests/devnet/test_drift_auth.py -v

# Run with debug logging
python -m pytest src/trading/tests/devnet/test_drift_auth.py -v --log-cli-level=DEBUG
```

## Integration with Main Module

### Drift Integration
- `drift_auth.py` provides authentication for main Drift module
- Shares account management logic with production code
- Uses same transaction parameters for consistency

### Jupiter Integration
- Test swaps and routing on devnet
- Verify slippage calculations
- Test price impact estimation

## Security and Best Practices

1. **Wallet Safety:**
   - NEVER use mainnet wallets for testing
   - Keep devnet private keys separate
   - Use environment variables for sensitive data

2. **Error Handling:**
   ```python
   try:
       await helper.initialize_drift()
   except Exception as e:
       logger.error(f"Initialization failed: {e}")
   finally:
       await drift_client.unsubscribe()
   ```

3. **Resource Management:**
   - Clean up connections after tests
   - Monitor compute unit usage
   - Track transaction costs

## Troubleshooting

Common issues and solutions:

1. **RPC Connection Issues:**
   - Check devnet status: `solana ping`
   - Verify RPC URL is correct
   - Try alternative RPC endpoints

2. **Insufficient Balance:**
   - Request devnet airdrop: `solana airdrop 2`
   - Check balance: `solana balance`
   - Monitor transaction costs

3. **Test Failures:**
   - Check logs with `-v` flag
   - Verify wallet permissions
   - Ensure market is initialized

## Development Guidelines

1. **Code Organization:**
   - Keep tests in `/tests/devnet/`
   - Maintain separation from mainnet code
   - Use clear naming conventions

2. **Documentation:**
   - Comment complex test scenarios
   - Document setup requirements
   - Keep README updated

3. **Testing Strategy:**
   - Start with unit tests
   - Add integration tests
   - Include error cases