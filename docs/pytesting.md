# Testing Guide for Ultimate Data Fetcher

## Quick Start 🚀

To run all tests in src/tests:
```bash
cd /home/dex/ultimate_data_fetcher
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/ -v -p no:anchorpy
```

To run critical tests only (from src/critical_tests):
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/critical_tests/ -v -p no:anchorpy
```

## Test Overview 📊

Our test suite is divided into two main categories, aligned with our modular monolith architecture:

### 1. Critical Tests (src/critical_tests/)
These tests focus on core functionality that must never break:
- Exchange connectivity and market data
- Order execution and management
- Risk management systems
- Critical data pipelines

### 2. Regular Tests (src/tests/)
Our regular test suite contains 60 tests covering various components:

#### Exchange Tests (TestBinanceHandler, TestDriftHandler, TestCoinbaseHandler)
- `test_market_symbol_conversion`: Validates correct symbol format conversion (BTC-USDT ↔ BTCUSDT)
- `test_market_validation`: Ensures markets are properly validated in both formats
- `test_get_markets`: Verifies market list retrieval and format consistency
- `test_get_exchange_info`: Checks exchange information accuracy and USDT pairs
- `test_fetch_historical_candles`: Tests historical data retrieval with time ranges
- `test_live_candles`: Validates real-time candle data fetching
- `test_error_handling`: Ensures proper error handling for invalid inputs

#### Core Tests
- `test_symbol_mapper`: Tests symbol format conversion and registration
- `test_rate_limiting`: Validates API rate limit handling
- `test_retry_mechanism`: Checks automatic retry on temporary failures
- `test_mock_data`: Ensures test mode provides realistic mock data

#### Integration Tests
- `test_data_pipeline`: Tests end-to-end data flow
- `test_exchange_integration`: Validates multi-exchange compatibility
- `test_strategy_execution`: Tests strategy implementation with live data

#### Backtesting Tests
- `test_backtest_with_mock_indicator`: Tests backtesting with mock indicators
- `test_position_initialization`: Tests position initialization
- `test_portfolio_initialization`: Tests portfolio initialization
- `test_performance_metrics`: Tests performance metrics calculation

## Prerequisites 📋

Make sure you have all required packages installed:
```bash
pip install -r requirements.txt
pip install python-binance  # For Binance tests
```

## Test Structure 📁

All tests are located in `src/tests/` and `src/critical_tests/`. Here's what each test file covers:

- `test_exchanges.py` - Tests for exchange handlers (Binance, Coinbase, Drift, etc.)
- `test_indicators.py` - Tests for technical indicators (KNN, RSI, MACD, etc.)
- `test_core.py` - Core functionality tests
- `test_storage.py` - Data storage and retrieval tests
- `test_backtester.py` - Backtesting engine tests
- `test_performance_metrics.py` - Trading performance metrics tests
- `test_risk_analysis.py` - Risk analysis tools tests
- `test_optimizer.py` - Strategy optimization tests
- `test_backtesting_integration.py` - End-to-end backtesting tests
- `test_symbol_mapper.py` - Symbol mapping tests

## Running Specific Tests 🎯

1. Run all tests in a file:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/test_exchanges.py -v
```

2. Run a specific test class:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/test_exchanges.py::TestBinanceHandler -v
```

3. Run a specific test method:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/test_exchanges.py::TestBinanceHandler::test_market_symbol_conversion -v
```

## Test Categories 🏷️

Tests are organized into categories using pytest markers:
- `exchange` - Exchange-related tests
- `backtest` - Backtesting-related tests
- `integration` - Integration tests
- `unit` - Unit tests
- `performance` - Performance tests

To run tests by category:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/ -m exchange -v
```

## Test Mode vs Live Mode 🔄

Our tests support two modes:

### Test Mode
- Uses mock data for markets and candles
- Supports both standard (BTC-USDT) and exchange (BTCUSDT) formats
- Provides consistent test environment
- No API keys required

### Live Mode
- Connects to real exchange APIs
- Requires valid API credentials
- Subject to rate limits
- Tests real market conditions

### Important: Enabling Test Mode Correctly

To properly enable test mode in exchange handlers, follow this pattern:

```python
# Create handler but don't connect yet
handler = BinanceHandler(config)

# Enable test mode BEFORE connecting
handler._is_test_mode = True
handler._setup_test_mode()

# Now connect with test mode already enabled
await handler.start()
```

This ensures that no real API calls are made during testing.

## Common Issues & Solutions 🔧

1. **Import Errors**
   - Make sure `PYTHONPATH` is set correctly
   - Check if all required packages are installed
   - Verify package versions in `requirements.txt`

2. **Rate Limit Errors**
   - Tests automatically handle rate limits
   - If persistent, increase delay between requests in `conftest.py`

3. **Missing Dependencies**
   - Install missing packages:
     ```bash
     pip install python-binance pytest-asyncio
     ```

4. **Plugin Errors**
   - If you see anchorpy plugin errors, use `-p no:anchorpy` flag
   - For xprocess errors, run `pytest --xkill` after tests

5. **Timeout Errors**
   - If tests timeout when connecting to real APIs, ensure test mode is enabled
   - Check that test mode is enabled BEFORE connecting to the API

## Writing New Tests 📝

1. Create test file in `src/tests/`
2. Import required modules
3. Create test class inheriting from appropriate base class
4. Add test methods prefixed with `test_`
5. Use appropriate markers for categorization

Example:
```python
import pytest
from src.exchanges import BinanceHandler

@pytest.mark.exchange
class TestNewExchange:
    async def test_new_feature(self):
        # Your test code here
        assert result == expected
```

## Test Configuration ⚙️

Test settings are managed in:
- `pytest.ini` - General pytest configuration
- `conftest.py` - Shared fixtures and settings
- `config/test_settings.json` - Test-specific settings

## Debugging Tests 🐛

1. Add print statements:
```python
print(f"Debug: {variable}")  # Will show in test output
```

2. Use pytest's -vv flag for more detail:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/ -vv
```

3. Run tests with pdb on failure:
```bash
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/ --pdb
```

## Best Practices ✨

1. Always run tests before pushing changes
2. Keep tests focused and independent
3. Use meaningful test names
4. Add docstrings to test classes and methods
5. Handle cleanup in fixture teardown
6. Use appropriate assertions
7. Mock external services when possible
8. Maintain alignment with the modular monolith architecture
9. Always enable test mode BEFORE connecting to APIs

## Running Tests with Specific Market Formats

You can run tests with a specific market format using the `--market-format` option:

```bash
# Run tests with Binance market format
PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/ -p no:anchorpy --market-format=binance

# Run tests with Coinbase market format
PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/ -p no:anchorpy --market-format=coinbase

# Run tests with Drift market format
PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/ -p no:anchorpy --market-format=drift
```

## Recent Updates (March 2025) 🆕

### Test Mode Improvements

We've made several important improvements to the testing framework:

1. **Enhanced Test Mode Implementation**
   - Fixed the `_setup_test_mode` method in exchange handlers to properly initialize mock data
   - Ensured test mode is enabled BEFORE connecting to APIs to avoid real API calls
   - Improved mock market structure to match real API responses

2. **Test Fixtures Enhancements**
   - Updated fixtures to properly enable test mode
   - Fixed the `binance_handler` fixture to initialize test mode correctly
   - Added proper cleanup in fixture teardown

3. **Critical Test Fixes**
   - Fixed `test_binance_connectivity` and `test_live_data_fetching` to use test mode
   - Ensured all critical tests can run without real API connections
   - Improved error handling in test mode

These changes ensure that our tests are more reliable, easier to run, and better at catching potential issues before they affect production code.

## Architectural Alignment

Our test suite is designed to maintain the integrity of our modular monolith architecture:

1. **Data Acquisition Layer Tests**
   - Exchange handler tests ensure proper market data fetching
   - Symbol mapping tests validate correct format conversion
   - Mock handlers provide reliable testing environments

2. **Transformation Pipeline Tests**
   - Data standardization tests ensure consistent formats
   - Storage tests validate data persistence and retrieval
   - Processing tests check data transformation accuracy

3. **Strategy Composition Layer Tests**
   - Indicator tests validate technical analysis calculations
   - Strategy tests ensure proper signal generation
   - Backtesting tests verify strategy performance

4. **Execution Layer Tests**
   - Order execution tests validate trade placement
   - Risk management tests ensure proper position sizing
   - Performance tests measure trading outcomes

By maintaining this test structure, we ensure that each architectural layer maintains its integrity while properly integrating with adjacent layers.

## Need Help? 🆘

1. Check test output for error messages
2. Review relevant test file
3. Check `conftest.py` for test configuration
4. Verify environment setup
5. Look for similar tests as examples 