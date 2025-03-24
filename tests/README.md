# D3X7-ALGO Test Suite

This directory contains all tests for the D3X7-ALGO trading platform.

## Test Organization

The tests are organized into the following categories:

- **Unit Tests** (`unit/`): Test individual components in isolation
  - Core components (`core/`)
  - Indicators (`indicators/`)
  - Storage mechanisms (`storage/`)
  - Exchange adaptors (`exchanges/`)
  - Wallet functions (`wallet/`)

- **Integration Tests** (`integration/`): Test how components work together
  - Devnet integration (`devnet/`)
  - Data fetching (`data/`)
  - Drift protocol (`drift/`)
  - Mainnet operations (`mainnet/`)

- **Backtesting** (`backtesting/`): Tests for backtesting functionality
  - Backtester core
  - Optimization
  - Performance metrics
  - Risk analysis

- **Functional Tests** (`functional/`): End-to-end tests of complete workflows
  - Critical functionality tests
  - Transfer tests

## Running Tests

### Running all tests

```bash
pytest
```

### Running a specific test category

```bash
# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/indicators/test_indicators.py
```

### Running tests with verbose output

```bash
pytest -v
```

### Running tests with asyncio support

```bash
pytest --asyncio-mode=auto
``` 