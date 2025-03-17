# Drift Protocol Integration

This directory contains the core components for interacting with the Drift Protocol, implementing both spot and perpetual futures trading functionality.

## Directory Structure

```
/src/trading/
├── drift/                  # Core Drift protocol components
│   ├── __init__.py        # Module exports
│   ├── account_manager.py # Account management and balance tracking
│   ├── drift_adapter.py   # Core Drift protocol interaction adapter
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

The account manager can be run from the project root using the `manage_drift.py` wrapper:

```bash
# Show account balances
python -m manage_drift balance

# Deposit SOL (with confirmation)
python -m manage_drift deposit --token SOL --amount 0.1

# Deposit SOL (without confirmation)
python -m manage_drift deposit --token SOL --amount 0.1 --force

# Withdraw SOL
python -m manage_drift withdraw --token SOL --amount 0.1
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

**Usage Example:**
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

### 2. Drift Adapter (`drift_adapter.py`)

Core adapter for interacting with Drift Protocol's smart contracts.

**Key Features:**
- Market price fetching (spot and perpetual)
- Position tracking and management
- Order placement and execution
- Market configuration handling

**Supported Markets:**
```python
# Perpetual Markets
- SOL-PERP (index: 0)
- BTC-PERP (index: 1)
- ETH-PERP (index: 2)

# Spot Markets
- SOL-USDC (index: 0)
- BTC-USDC (index: 1)
- ETH-USDC (index: 2)
```

**Usage Example:**
```python
from src.trading.drift.drift_adapter import DriftAdapter

async def example():
    adapter = DriftAdapter()
    await adapter.connect()
    
    try:
        # Get market price
        sol_price = await adapter.get_market_price("SOL-PERP")
        
        # Check balances
        balances = await adapter.get_account_balances()
    finally:
        await adapter.disconnect()
```

## Environment Setup

### Dependencies
```bash
pip install driftpy anchorpy solana-py solders
```

### Configuration
The system uses environment variables and configuration files:

1. **Required Environment Variables:**
   - `HELIUS_RPC_URL`: Your Helius RPC endpoint
   - `WALLET_PATH`: Path to your Solana wallet keypair

2. **Transaction Parameters:**
   ```python
   tx_params = TxParams(
       compute_units_price=85_000,  # Default
       compute_units=1_400_000      # Default
   )
   ```

## Testing

Tests are organized in two directories:

1. `/src/trading/tests/drift/`: Main test suite
   - Tests core functionality
   - Uses mainnet configuration
   - Full integration tests

2. `/src/trading/tests/devnet/`: Devnet test suite
   - Tests with devnet configuration
   - Safer for experimental features
   - Uses test tokens

To run tests:
```bash

# Run devnet tests
python -m pytest src/trading/tests/devnet/test_drift_account_manager.py
```

## Security Best Practices

1. **Transaction Safety:**
   - Always use confirmation prompts for deposits/withdrawals
   - Verify balances before transactions
   - Use the `--force` flag carefully

2. **Error Handling:**
   ```python
   try:
       await manager.deposit_sol(amount)
   except Exception as e:
       logger.error(f"Deposit failed: {e}")
   finally:
       await manager.drift_client.unsubscribe()
   ```

3. **Resource Management:**
   - Always clean up connections
   - Handle subscription lifecycle
   - Monitor position risks

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