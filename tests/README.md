# 🧪 Testing Framework

This directory contains the testing framework and test suites for the D3X7-ALGO platform.

## 🔍 Overview

The testing framework provides:
- Unit tests for individual components
- Integration tests for system interactions
- End-to-end tests for complete workflows
- Performance tests for optimization
- Mock data and fixtures

## 📁 Structure

```
tests/
├── unit/             # Unit tests for individual components
│   ├── core/         # Core functionality tests
│   ├── data/         # Data handling tests
│   ├── trading/      # Trading logic tests
│   └── utils/        # Utility function tests
├── integration/      # Integration tests
│   ├── exchanges/    # Exchange integration tests
│   ├── storage/      # Storage system tests
│   └── trading/      # Trading system tests
├── e2e/             # End-to-end tests
├── performance/     # Performance benchmarks
├── fixtures/        # Test fixtures and mock data
├── conftest.py     # Pytest configuration
└── README.md       # This file
```

## 🚀 Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage report
pytest --cov=src tests/
```

## 📋 Test Categories

### 1. Unit Tests
Tests for individual components in isolation.

```python
# Example unit test
def test_standardized_candle():
    candle = StandardizedCandle(
        timestamp=1234567890,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000.0
    )
    assert candle.is_valid()
```

### 2. Integration Tests
Tests for component interactions.

```python
# Example integration test
@pytest.mark.asyncio
async def test_data_fetching_and_storage():
    fetcher = DriftDataFetcher()
    storage = DataStorage()
    
    data = await fetcher.fetch_historical_data("SOL")
    await storage.save_candles("SOL", data)
    
    retrieved = await storage.get_candles("SOL")
    assert len(retrieved) == len(data)
```

### 3. End-to-End Tests
Tests for complete workflows.

```python
# Example E2E test
@pytest.mark.asyncio
async def test_trading_workflow():
    # Setup components
    strategy = SimpleStrategy()
    executor = OrderExecutor()
    
    # Run complete workflow
    signals = await strategy.generate_signals()
    for signal in signals:
        result = await executor.execute_order(signal)
        assert result.status == "success"
```

### 4. Performance Tests
Tests for system performance.

```python
# Example performance test
def test_data_processing_performance():
    data = generate_large_dataset()
    
    start_time = time.time()
    processed = process_data(data)
    end_time = time.time()
    
    assert (end_time - start_time) < 1.0  # Should process in under 1 second
```

## 🎯 Test Fixtures

### Common Fixtures
```python
# conftest.py
import pytest

@pytest.fixture
def mock_market_data():
    return generate_mock_data()

@pytest.fixture
async def drift_client():
    client = DriftClient()
    await client.connect()
    yield client
    await client.disconnect()
```

### Using Fixtures
```python
def test_with_fixtures(mock_market_data, drift_client):
    result = process_market_data(mock_market_data)
    assert result.is_valid
```

## 🔧 Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests independent

```python
class TestDataProcessing:
    def test_data_cleaning(self):
        # Arrange
        data = load_test_data()
        
        # Act
        cleaned = clean_data(data)
        
        # Assert
        assert cleaned.is_valid()
```

### 2. Mock Data
- Use realistic test data
- Create reusable fixtures
- Document data assumptions
- Handle edge cases

```python
@pytest.fixture
def mock_trade_data():
    return {
        "market": "SOL",
        "price": 100.0,
        "size": 1.0,
        "side": "buy"
    }
```

### 3. Async Testing
- Use pytest-asyncio
- Handle cleanup properly
- Test timeouts
- Mock async calls

```python
@pytest.mark.asyncio
async def test_async_function():
    async with AsyncClient() as client:
        result = await client.fetch_data()
        assert result is not None
```

## 🐛 Debugging Tests

### Using PDB
```python
def test_with_debugger():
    data = process_data()
    breakpoint()  # Start debugger
    assert data.is_valid()
```

### Running with Debug Output
```bash
pytest -vv --pdb tests/unit/test_file.py
```

## 📊 Coverage Reports

### Running Coverage
```bash
# Generate coverage report
pytest --cov=src --cov-report=html tests/

# View report
open htmlcov/index.html
```

### Coverage Configuration
```ini
# .coveragerc
[run]
source = src
omit = tests/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
```

## 🔄 Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/
```

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Guide](docs/testing/guide.md)
- [Mock Data Guide](docs/testing/mock_data.md)
- [CI/CD Guide](docs/testing/ci_cd.md) 