# Trading Tests Directory

This directory contains test suites for all trading components, organized by protocol and environment.

## Directory Structure

```
tests/
├── devnet/                 # Devnet-specific tests
│   ├── test_balance.py    # Balance checking
│   ├── test_drift_*.py    # Drift protocol tests
│   └── test_wallet.py     # Wallet functionality
├── drift/                  # Drift protocol tests
│   ├── test_drift_*.py    # Core functionality
│   └── drift_tools.py     # Testing utilities
└── jup/                    # Jupiter tests
    ├── test_strategy.py   # Trading strategies
    └── test_trades.py     # Trade execution
```

## Test Categories

### 1. Drift Protocol Tests
- **Account Management:** Deposits, withdrawals, balances
- **Market Operations:** Order placement, execution
- **Authentication:** Client setup, permissions
- **Collateral:** Position management, risk checks

### 2. Jupiter Tests
- **Strategy Testing:** Trading logic validation
- **Trade Execution:** Swap functionality, routing
- **Price Impact:** Slippage calculations

### 3. Devnet Tests
- **Basic Operations:** Connection, authentication
- **Spot Trading:** Market orders, limits
- **Perpetual Markets:** Futures trading
- **Wallet Integration:** Transaction signing

## Running Tests

```bash
# Run all tests
pytest src/trading/tests

# Run specific category
pytest src/trading/tests/drift
pytest src/trading/tests/jup
pytest src/trading/tests/devnet

# Run single test file
pytest src/trading/tests/devnet/test_balance.py
```

## Test Requirements

1. **Environment Setup:**
   ```bash
   # Required environment variables
   export SOLANA_RPC_URL="https://api.devnet.solana.com"
   export PRIVATE_KEY_PATH="~/.config/solana/id.json"
   ```

2. **Dependencies:**
   ```bash
   pip install pytest pytest-asyncio
   ```

## Best Practices

1. **Test Organization:**
   - Group related tests in same file
   - Use descriptive test names
   - Include setup/teardown

2. **Devnet Testing:**
   - Always test on devnet first
   - Use test accounts
   - Clean up after tests

3. **Async Testing:**
   ```python
   @pytest.mark.asyncio
   async def test_function():
       # Your test here
       pass
   ```

## Common Test Patterns

```python
# Setup pattern
@pytest.fixture
async def drift_client():
    client = DriftClient()
    await client.connect()
    yield client
    await client.disconnect()

# Test pattern
@pytest.mark.asyncio
async def test_operation(drift_client):
    result = await drift_client.some_operation()
    assert result.status == "success"
```

## Notes

- All tests use devnet by default
- Clean up resources after tests
- Use fixtures for common setup
- Handle async operations properly
- Mock external services when appropriate