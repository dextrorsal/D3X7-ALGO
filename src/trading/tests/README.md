# Tests Directory

This directory contains test suites for different components of the trading system.

## Directory Structure

```
tests/
├── run_tests.py            - Test runner script
├── conftest.py            - Shared test fixtures
├── wallet/               - Wallet and RPC testing
├── unit/                  - Component-level tests
├── integration/          - End-to-end tests
└── utils/               - Test helpers
```

## Quick Start

Run all tests from project root:
```bash
./src/trading/run_tests.py
```

Common test commands:
```bash
# Run specific test suites
./src/trading/run_tests.py --unit
./src/trading/run_tests.py --integration
./src/trading/run_tests.py --devnet
./src/trading/run_tests.py --mainnet

# With coverage
./src/trading/run_tests.py --coverage

# Manual testing options
python src/trading/tests/wallet/manual_wallet_test.py  # Test wallet functionality
```

## Test Categories

### Wallet Tests
- RPC connection and network switching
- Wallet management and encryption
- Configuration handling
- Environment validation

### Unit Tests
- `security/`: Trading limits and risk management
- `drift/`: Drift protocol operations
- `jup/`: Jupiter protocol operations

### Integration Tests
- `devnet/`: Development environment testing
- `mainnet/`: Production environment validation

## Common Fixtures

Key fixtures in `conftest.py`:
- `wallet_manager`: Wallet operations
- `security_limits`: Trading controls
- `drift_adapter`: Drift protocol interface
- `jup_adapter`: Jupiter protocol interface

## Test Utils

The `utils/` directory contains:
- Mock data generators
- Test helpers
- Common test utilities

## Manual Testing

Some components provide manual test scripts for direct testing without pytest dependencies:

### Wallet Testing
The `wallet/manual_wallet_test.py` script tests:
- RPC Connection
- Network Switching (devnet/testnet)
- Wallet Operations
  - Wallet listing
  - Current wallet selection
  - Encryption/Decryption
  - Environment validation

Required environment variables:
- `WALLET_PASSWORD`: For encryption/decryption tests

For detailed documentation on writing tests, best practices, and troubleshooting, see the main [Trading Documentation](../README.md#testing).

## Jupiter Integration Tests

Jupiter integration tests validate the swap functionality and security features for the Jupiter DEX integration. These tests ensure that:

1. The Jupiter adapter connects properly to the Solana network
2. Market price retrieval works correctly
3. Account balance retrieval functions properly
4. Security validations work for swap sizes and slippage
5. Quote retrieval for swaps works as expected
6. Route options can be retrieved for optimal swaps

### Running Jupiter Integration Tests

To run all Jupiter integration tests:

```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_jupiter_integration.py -v
```

To run a specific Jupiter test:

```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_jupiter_integration.py::TestJupiterIntegration::test_market_price -v
```

To run the Jupiter security integration test:

```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration::test_jupiter_swap_security -v
```

### Test Coverage

The Jupiter integration tests cover:

- Basic connectivity to Jupiter API
- Market price retrieval
- Account balance retrieval
- Swap quote retrieval
- Security validation for swap sizes
- Security validation for slippage
- Route option retrieval

Note: The actual swap execution test is skipped by default to avoid spending SOL. You can enable it by removing the `skipif` decorator if you want to test actual swaps on devnet.