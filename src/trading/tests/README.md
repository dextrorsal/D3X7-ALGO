# Testing Structure

This directory contains the test suites for the D3X7 trading platform, organized to support both mainnet and devnet testing environments.

## Directory Structure

```
/src/trading/tests/
├── drift/                 # Mainnet Drift Protocol tests
│   ├── test_drift_account_manager.py
│   ├── test_drift_adapter.py
│   └── check_drift_collateral.py
├── devnet/               # Devnet environment tests
│   ├── test_drift_auth.py
│   ├── test_drift_account_manager.py
│   └── test_drift_setup.py
└── README.md            # This file
```

## Test Suite Organization

### Why Multiple Test Directories?

Our test structure is organized around two key principles:
1. **Environment Separation**: Tests that run on mainnet vs devnet
2. **Component Isolation**: Tests specific to each major component (Drift, Jupiter, etc.)

#### 1. `/tests/drift/` Directory
- **Purpose**: Tests for mainnet Drift Protocol integration
- **When to Use**: 
  - Testing production-ready features
  - Verifying mainnet market interactions
  - Checking real collateral and positions
- **Key Test Files**:
  ```
  test_drift_account_manager.py  # Tests account operations
  test_drift_adapter.py         # Tests market interactions
  check_drift_collateral.py     # Verifies collateral calculations
  ```

#### 2. `/tests/devnet/` Directory
- **Purpose**: Safe testing environment for new features
- **When to Use**:
  - Developing new features
  - Testing risky operations
  - Verifying authentication flows
- **Key Test Files**:
  ```
  test_drift_auth.py            # Tests authentication flow
  test_drift_account_manager.py # Tests account operations
  test_drift_setup.py          # Tests initial setup
  ```

## Test Categories

### 1. Integration Tests
- Test interaction between components
- Verify end-to-end workflows
- Check system boundaries

### 2. Component Tests
- Focus on individual components
- Verify specific functionality
- Test error handling

### 3. Safety Tests
- Verify transaction safety
- Check balance management
- Test position limits

## Running Tests

### Mainnet Tests
```bash
# Run all mainnet tests
python -m pytest src/trading/tests/drift/

# Run specific mainnet test
python -m pytest src/trading/tests/drift/test_drift_account_manager.py

# Run collateral test
python src/trading/tests/drift/check_drift_collateral.py
```

### Devnet Tests
```bash
# Run all devnet tests
python -m pytest src/trading/tests/devnet/

# Run specific devnet test
python -m pytest src/trading/tests/devnet/test_drift_auth.py
```

### Test Parameters
```bash
# Run with verbose output
python -m pytest -v

# Run with debug logging
python -m pytest --log-cli-level=DEBUG

# Run specific test function
python -m pytest test_file.py::test_function_name
```

## Test Development Guidelines

### 1. Test Organization
- Place tests in appropriate environment directory
- Use clear, descriptive test names
- Group related tests in same file

### 2. Test Safety
- Never use mainnet credentials in devnet tests
- Always clean up after tests
- Use appropriate timeouts

### 3. Test Documentation
- Document test purpose
- Explain test prerequisites
- Include example usage

## Writing New Tests

### 1. Choose Location
```python
# For mainnet features:
/tests/drift/test_new_feature.py

# For experimental features:
/tests/devnet/test_new_feature.py
```

### 2. Test Structure
```python
import pytest
from src.trading.drift.account_manager import DriftAccountManager

@pytest.fixture
async def manager():
    manager = DriftAccountManager()
    await manager.setup()
    yield manager
    await manager.drift_client.unsubscribe()

async def test_feature(manager):
    # Test implementation
    pass
```

### 3. Test Documentation
```python
async def test_deposit_sol():
    """
    Test SOL deposit functionality.
    
    Prerequisites:
    - Devnet wallet with SOL
    - Active RPC connection
    
    Verifies:
    - Deposit confirmation
    - Balance update
    - Transaction safety
    """
    pass
```

## Common Test Patterns

### 1. Setup/Teardown
```python
@pytest.fixture(autouse=True)
async def setup_teardown():
    # Setup
    yield
    # Teardown
```

### 2. Error Testing
```python
async def test_error_handling():
    with pytest.raises(InsufficientFundsError):
        await manager.deposit_sol(999999)
```

### 3. Market Testing
```python
@pytest.mark.parametrize("market", ["SOL-PERP", "BTC-PERP"])
async def test_market_interaction(market):
    # Test implementation
```

## Test Dependencies

### Required Packages
```bash
pip install pytest pytest-asyncio pytest-timeout
```

### Environment Setup
```bash
# For devnet tests
export DEVNET_RPC_URL="https://api.devnet.solana.com"
export DEVNET_WALLET_PATH="~/.config/solana/devnet.json"

# For mainnet tests
export HELIUS_RPC_URL="your_helius_url"
export WALLET_PATH="~/.config/solana/id.json"
```

## Troubleshooting Tests

### Common Issues

1. **Import Errors**
   - Run from project root
   - Use correct import paths
   - Check PYTHONPATH

2. **Connection Issues**
   - Verify RPC endpoints
   - Check network status
   - Confirm wallet setup

3. **Test Failures**
   - Check test prerequisites
   - Verify environment setup
   - Review test logs

## Contributing

When adding new tests:
1. Choose appropriate directory
2. Follow naming conventions
3. Add documentation
4. Include example usage
5. Update this README if needed