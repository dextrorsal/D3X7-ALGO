# Drift Protocol Integration

This directory contains the core components for interacting with the Drift Protocol, implementing both spot and perpetual futures trading functionality.

## Directory Structure

```
/src/trading/
├── drift/                  # Core Drift protocol components
│   ├── __init__.py        # Module exports
│   ├── account_manager.py # Account management and balance tracking
│   ├── drift_adapter.py   # Core Drift protocol interaction adapter
│   ├── management/        # CLI and management tools
│   │   ├── drift_cli.py           # CLI interface
│   │   ├── drift_wallet_manager.py # Wallet management
│   │   └── README.md              # Management tools documentation
│   └── README.md         # This file
├── devnet/                # Devnet testing components
│   ├── drift_auth.py     # Authentication for Drift (used by account_manager)
│   └── ...
└── tests/                # Test suites
    ├── drift/           # Main drift tests
    │   └── test_drift_account_manager.py
    └── devnet/          # Devnet-specific tests
        └── test_drift_account_manager.py
```

## Quick Start

### Using the CLI Tools

For detailed CLI usage and management tools, see the [Management Tools Documentation](management/README.md).

Basic commands:
```bash
# Show account balances
./drift_cli.py account balance MAIN 0

# List subaccounts
./drift_cli.py subaccount list MAIN

# Deposit SOL
./drift_cli.py account deposit MAIN --token SOL --amount 0.1
```

### Using the Python API

```python
from src.trading.drift.account_manager import DriftAccountManager

async def example():
    manager = DriftAccountManager()
    await manager.setup()
    
    try:
        # Check balances
        await manager.show_balances()
        
        # Deposit SOL
        await manager.deposit_sol(amount=1.0)
    finally:
        # Always clean up
        await manager.drift_client.unsubscribe()
```

## Component Details

### 1. Account Manager (`account_manager.py`)

Handles Drift account management, deposits, withdrawals, and balance tracking.

**Key Features:**
- SOL and USDC deposit/withdrawal handling
- Real-time balance checking and display
- PnL tracking and risk metrics
- Collateral management
- Safe transaction handling with confirmations

### 2. Drift Adapter (`drift_adapter.py`)

Core adapter for interacting with Drift Protocol's smart contracts.

**Key Features:**
- Market price fetching (spot and perpetual)
- Position tracking and management
- Order placement and execution
- Market configuration handling

### 3. Management Tools (`management/`)

CLI and management tools for Drift operations. Features include:
- Secure wallet management with encryption
- Subaccount creation and management
- Balance checking and transfers
- Interactive CLI interface

For detailed documentation of management features, see the [Management README](management/README.md).

## Environment Setup

### Dependencies
```bash
pip install driftpy anchorpy solana-py solders
```

### Configuration
The system uses environment variables and configuration files:

1. **Required Environment Variables:**
   ```bash
   ENABLE_ENCRYPTION=true    # Enable wallet encryption
   WALLET_PASSWORD=<secure>  # Wallet encryption password
   ```

2. **Optional Environment Variables:**
   ```bash
   DRIFT_LOG_LEVEL=DEBUG    # Enable detailed logging
   DRIFT_NETWORK=devnet     # Network selection
   ```

## Security Best Practices

1. **Wallet Security:**
   - Always use encrypted wallet files
   - Store passwords securely
   - Use the CLI's confirmation prompts

2. **Transaction Safety:**
   - Verify balances before transactions
   - Use the `--force` flag carefully
   - Monitor position risks

3. **Error Handling:**
   ```python
   try:
       await manager.deposit_sol(amount)
   except Exception as e:
       logger.error(f"Deposit failed: {e}")
   finally:
       await manager.drift_client.unsubscribe()
   ```

## Integration with Other Components

### Devnet Integration
- Uses `DriftHelper` from `src.trading.devnet.drift_auth`
- Supports both mainnet and devnet environments
- Handles authentication and connection setup

### Jupiter Integration
- Compatible with Jupiter Aggregator
- Supports price comparison
- Enables optimal routing strategies

## Troubleshooting

Common issues and solutions:

1. **Import Errors:**
   - Always run with `-m` flag from project root
   - Use correct relative imports
   - Check PYTHONPATH if needed

2. **Connection Issues:**
   - Verify RPC endpoint
   - Check wallet configuration
   - Ensure proper network selection

3. **Transaction Failures:**
   - Check account balances
   - Verify market indices
   - Monitor compute unit limits

For CLI-specific troubleshooting, see the [Management Tools Documentation](management/README.md).