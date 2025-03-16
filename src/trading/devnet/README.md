# Trading Devnet Directory

This directory contains components for interacting with Solana's devnet, specifically focused on Drift Protocol integration for testing and development purposes.

## Directory Structure

```
devnet/
├── __init__.py          - Module exports and initialization
├── drift_auth.py        - Drift authentication and client setup
└── README.md           - This file
```

## Component Details

### 1. `drift_auth.py`

The core authentication and client initialization module for Drift Protocol on devnet.

**Key Features:**
- `DriftHelper` class for managing Drift client initialization
- Wallet loading and management
- RPC connection setup
- User account information retrieval
- Balance and PnL tracking

**Usage Example:**
```python
from src.trading.devnet.drift_auth import DriftHelper

async def example():
    helper = DriftHelper()
    
    # Initialize Drift client
    drift_client = await helper.initialize_drift()
    
    # Get user account information
    await helper.get_user_info()
```

**Requirements:**
- Solana keypair at `~/.config/solana/id.json`
- Active devnet connection
- Sufficient devnet SOL for transactions

### 2. `__init__.py`

Module initialization file that exports key components:
- `DriftHelper`: For client initialization and authentication
- `DriftAccountManager`: For managing Drift accounts and transactions

## Common Operations

1. **Client Initialization:**
   ```python
   helper = DriftHelper()
   drift_client = await helper.initialize_drift()
   ```

2. **Checking Account Information:**
   ```python
   await helper.get_user_info()
   ```

## Best Practices

1. **Error Handling:**
   - Always use try-catch blocks for async operations
   - Properly close connections using `drift_client.unsubscribe()`

2. **Resource Management:**
   ```python
   try:
       # Your code here
   finally:
       await drift_client.unsubscribe()
   ```

3. **Transaction Parameters:**
   - Default compute units: 1,400,000
   - Default compute units price: 85,000
   - Can be customized when initializing the client

## Integration Points

- Works with the main trading module for devnet testing
- Integrates with Drift Protocol's devnet deployment
- Compatible with Jupiter aggregator for testing strategies

## Notes

- All operations are performed on Solana's devnet
- Requires devnet SOL for testing (use devnet faucet)
- Keep private keys secure and never use mainnet keys for testing