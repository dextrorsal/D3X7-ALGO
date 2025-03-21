# D3X7-ALGO Testing Cheatsheet 🚀

This cheat sheet contains commands to run various tests in the project, focusing on security integration tests, wallet tests, and devnet adapter tests.

## Setup

Make sure your development environment is set up with the required dependencies and Python path:

```bash
# Set PYTHONPATH to include the project root
export PYTHONPATH=$PYTHONPATH:/home/dex/D3X7-ALGO
```

## Running Basic Tests

### Run all tests in the project
```bash
cd /home/dex/D3X7-ALGO && python -m pytest
```

### Run tests with verbose output
```bash
cd /home/dex/D3X7-ALGO && python -m pytest -v
```

## Security Integration Tests

### Run a specific security test
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::test_security_features -v -p no:anchorpy
```

### Run a specific test method from the TestSecurityIntegration class
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration::test_position_size_limits -v -p no:anchorpy
```

### Run all tests in the TestSecurityIntegration class
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration -v -p no:anchorpy
```

### Run multiple specific tests
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration::test_position_size_limits src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration::test_leverage_limits -v -p no:anchorpy
```

## Market Integration Tests

### Run a specific market test
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_market_integration.py::test_get_markets -v -p no:anchorpy
```

## Wallet Tests

### Run manual wallet tests
```bash
cd /home/dex/D3X7-ALGO && python src/trading/tests/wallet/manual_wallet_test.py
```

### Run wallet encryption tests
```bash
cd /home/dex/D3X7-ALGO && python src/trading/tests/wallet/test_wallet_encryption.py
```

### Run wallet integration tests
```bash
cd /home/dex/D3X7-ALGO && python src/trading/tests/integration/devnet/test_wallet_integration.py
```

## Devnet Adapter Tests

### Run all devnet adapter tests
```bash
cd /home/dex/D3X7-ALGO && python src/trading/tests/integration/devnet/test_devnet_adapter.py
```

### Run specific devnet adapter tests
```bash
# Run only the initialize adapter test
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_devnet_adapter.py::test_initialize_adapter -v

# Run only the wallet balance test
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_devnet_adapter.py::test_get_wallet_balance -v

# Run only the airdrop test
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_devnet_adapter.py::test_airdrop -v
```

## Drift Integration Tests

### Run drift integration tests
```bash
cd /home/dex/D3X7-ALGO && python src/trading/tests/integration/devnet/test_drift_integration.py
```

## Jupiter Integration Tests

### Run all Jupiter integration tests
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_jupiter_integration.py -v -p no:anchorpy
```

### Run a specific Jupiter test
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_jupiter_integration.py::TestJupiterIntegration::test_market_price -v -p no:anchorpy
```

### Run Jupiter security integration test
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_security_integration.py::TestSecurityIntegration::test_jupiter_swap_security -v -p no:anchorpy
```

### Run Jupiter basic functionality test
```bash
cd /home/dex/D3X7-ALGO && python -m pytest src/trading/tests/integration/devnet/test_jupiter_integration.py::test_jupiter_functionality -v -p no:anchorpy
```

## Debugging and Cleanup

### Clean up after tests (kill any hanging processes)
```bash
cd /home/dex/D3X7-ALGO && python -m pytest --xkill
```

### Run tests with more detailed logs
```bash
cd /home/dex/D3X7-ALGO && python -m pytest --log-cli-level=DEBUG <test_path>
```

## Working Tests

The following security tests are currently working:

1. `test_security_features` - Tests security initialization, audit, session timeout, and transaction confirmation
2. `test_position_size_limits` - Tests validation of position sizes
3. `test_leverage_limits` - Tests validation of leverage limits
4. `test_daily_volume_tracking` - Tests tracking and limiting daily trading volume
5. `test_emergency_shutdown` - Tests emergency shutdown functionality
6. `test_loss_threshold` - Tests loss threshold monitoring
7. `test_jupiter_swap_security` - Tests Jupiter swap security validations ✅

### Working Jupiter Tests:
All Jupiter integration tests are now working:
1. `test_jupiter_connection` - Tests establishing connection to Jupiter
2. `test_market_price` - Tests retrieving market price for SOL-TEST
3. `test_account_balances` - Tests retrieving account balances
4. `test_small_swap_quote` - Tests retrieving and validating small swap quotes
5. `test_large_swap_rejection` - Tests security rejection of large swaps
6. `test_high_slippage_rejection` - Tests security rejection of high slippage
7. `test_route_options` - Tests retrieving route options for swaps
8. `test_jupiter_functionality` - Tests basic Jupiter functionality

### Working Devnet Adapter Tests:
1. `test_initialize_adapter` - Successfully initializes the DevnetAdapter
2. `test_get_wallet_balance` - Successfully retrieves wallet balance
3. `test_airdrop` - Successfully requests and receives airdrop

## Skipped/Pending Tests

### Security Tests:
These tests are skipped or pending because they depend on methods that aren't fully implemented yet:

1. `test_drift_trade_security` - Needs implementation of deposit_usdc and place_perp_order methods
2. `test_risk_metrics` - Needs implementation of risk calculation methods
3. `test_market_stress` - Needs implementation of market stress detection
4. `test_config_validation` - Needs implementation of configuration validation

### Devnet Adapter Tests (require sufficient SOL):
1. `test_create_test_token` - Skipped due to insufficient SOL
2. `test_mint_test_tokens` - Skipped due to insufficient SOL
3. `test_create_test_market` - Skipped due to insufficient SOL
4. `test_execute_test_trade` - Skipped due to insufficient SOL

## Jupiter Testing Notes

- For devnet testing, use "SOL-TEST" instead of "SOL-USDC" market
- A mock wallet implementation with Keypair is included for Jupiter tests to avoid wallet connection issues
- Mock quote implementation allows testing swap functionality without making actual API calls
- The `test_execute_small_swap` test is skipped by default to avoid spending SOL

## Notes

- The `-p no:anchorpy` flag is added to prevent anchorpy plugin issues
- For verbose output, use the `-v` flag
- Warning errors about closed files and pending tasks are related to WebSocket connections and don't affect test results - they're typical when working with asyncio and WebSockets
- To run devnet adapter tests that require SOL, make sure to have sufficient SOL in your test wallet (can use the airdrop test first)
- The Jupiter swap execution test is skipped by default to avoid spending SOL. You can enable it by removing the `skipif` decorator if you want to test actual swaps on devnet.