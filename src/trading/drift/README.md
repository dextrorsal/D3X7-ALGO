# Trading Drift Directory

This directory contains the core components for interacting with the Drift Protocol, implementing both spot and perpetual futures trading functionality.

## Directory Structure

```
drift/
├── __init__.py           - Module exports
├── account_manager.py    - Account management and balance tracking
├── drift_adapter.py      - Core Drift protocol interaction adapter
└── README.md            - This file
```

## Component Details

### 1. `drift_adapter.py` (18KB)

The main adapter for interacting with Drift Protocol's smart contracts.

**Key Features:**
- Market price fetching for both spot and perpetual markets
- Account balance management
- Position tracking
- Order placement (spot and perpetual)
- Market configuration for major pairs (SOL, BTC, ETH)

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
from src.trading.drift import DriftAdapter

async def example():
    adapter = DriftAdapter(config_path="config.json")
    await adapter.connect()
    
    # Get market price
    sol_price = await adapter.get_market_price("SOL-PERP")
    
    # Check balances
    balances = await adapter.get_account_balances()
```

### 2. `account_manager.py` (12KB)

Handles Drift account management, deposits, withdrawals, and balance tracking.

**Key Features:**
- SOL and USDC deposit handling
- Balance checking and display
- PnL tracking
- Risk metrics monitoring
- Collateral management

**Usage Example:**
```python
from src.trading.drift.account_manager import DriftAccountManager

async def example():
    manager = DriftAccountManager()
    await manager.setup()
    
    # Check balances
    await manager.show_balances()
    
    # Deposit SOL
    await manager.deposit_sol(amount=1.0)
```

## Integration Points

### With Devnet Testing
- Uses `DriftHelper` from devnet module for authentication
- Compatible with devnet testing environment
- Supports test account management

### With Jupiter Aggregator
- Can be used alongside Jupiter for optimal routing
- Supports price comparison and arbitrage opportunities

## Best Practices

1. **Error Handling:**
   ```python
   try:
       await manager.deposit_sol(amount)
   except Exception as e:
       logger.error(f"Deposit failed: {e}")
   finally:
       await manager.drift_client.unsubscribe()
   ```

2. **Resource Management:**
   - Always initialize with proper configuration
   - Clean up connections after use
   - Handle subscription lifecycle properly

3. **Market Interaction:**
   - Use market indices consistently
   - Handle decimal precision correctly
   - Verify balances before transactions

## Configuration

1. **Required Environment:**
   - Solana RPC endpoint
   - Wallet keypair
   - Market configuration

2. **Transaction Parameters:**
   - Compute units: 1,400,000 (default)
   - Compute units price: 85,000 (default)

## Notes

- Core functionality for Drift Protocol interaction
- Supports both spot and perpetual markets
- Handles complex account management
- Integrates with both mainnet and devnet
- Provides detailed logging and error tracking

## Dependencies

- `driftpy`: Drift Protocol Python SDK
- `anchorpy`: Solana Anchor framework
- `solana`: Solana web3 library
- `solders`: Solana transaction library

## Security Considerations

1. Always verify transaction parameters before execution
2. Keep private keys secure
3. Monitor position risks
4. Handle errors gracefully
5. Validate inputs before transactions