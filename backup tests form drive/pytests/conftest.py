# src/tests/conftest.py
import pytest
import pytest_asyncio
import os
import sys
import asyncio
from typing import List
from pathlib import Path

# Configure pytest-asyncio
pytest_asyncio_config = {
    "asyncio_mode": "strict",
    "asyncio_default_fixture_loop_scope": "function",
}

def pytest_configure(config):
    """Configure test environment and register custom marks."""
    import matplotlib.pyplot as plt
    
    # Register test categories
    config.addinivalue_line("markers", "exchange: mark test as an exchange test")
    config.addinivalue_line("markers", "backtest: mark test as a backtest")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    
    # Register specific test types
    config.addinivalue_line("markers", "timeout: mark test with a timeout value in seconds")
    config.addinivalue_line("markers", "real_data: mark test that uses real exchange data")
    config.addinivalue_line("markers", "simple: mark test as 'simple'")

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection:
    1. Add markers based on test file location 
    2. Skip real_data tests by default
    3. Order tests by category
    """
    # Auto-mark tests based on their location/name
    for item in items:
        # Get the test file path relative to the tests directory
        test_file = Path(item.fspath).relative_to(Path(item.fspath).parent.parent / "tests")
        
        # Auto-mark based on filename
        if "test_exchanges" in str(test_file):
            item.add_marker(pytest.mark.exchange)
        elif "test_backtester" in str(test_file) or "test_real_data_backtest" in str(test_file):
            item.add_marker(pytest.mark.backtest)
        elif "test_integration" in str(test_file):
            item.add_marker(pytest.mark.integration)
        elif "test_performance" in str(test_file):
            item.add_marker(pytest.mark.performance)
        
        # Mark all tests in test_core.py as unit tests
        if "test_core" in str(test_file):
            item.add_marker(pytest.mark.unit)

    # Skip real_data tests by default unless --real-data flag is provided
    if not config.getoption("--real-data"):
        skip_real_data = pytest.mark.skip(reason="use --real-data to run")
        for item in items:
            if "real_data" in item.keywords:
                item.add_marker(skip_real_data)

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--real-data",
        action="store_true",
        default=False,
        help="run tests that use real exchange data"
    )
    parser.addoption(
        "--category",
        action="store",
        default=None,
        help="run tests of a specific category (exchange, backtest, integration, unit, performance)"
    )

@pytest.fixture(autouse=True)
def close_figures():
    """Close all matplotlib figures after each test."""
    yield
    import matplotlib.pyplot as plt
    plt.close('all')

@pytest_asyncio.fixture
async def mock_processed_storage(tmp_path_factory):
    """
    Mock ProcessedDataStorage for normal tests (not real data).
    """
    from src.storage.processed import ProcessedDataStorage
    from src.core.config import StorageConfig
    import pandas as pd
    from unittest.mock import patch

    temp_dir = tmp_path_factory.mktemp("processed_data")

    config = StorageConfig(
        data_path=temp_dir,
        historical_raw_path=temp_dir / "historical" / "raw",
        historical_processed_path=temp_dir / "historical" / "processed",
        live_raw_path=temp_dir / "live" / "raw",
        live_processed_path=temp_dir / "live" / "processed",
        use_compression=False
    )

    storage = ProcessedDataStorage(config)

    # Always return an empty DataFrame for load_candles in normal tests
    with patch.object(storage, 'load_candles', return_value=pd.DataFrame()):
        yield storage

@pytest.fixture(autouse=True)
def patch_real_data_backtest(monkeypatch, tmp_path_factory, request):
    """
    Patch ProcessedDataStorage for tests EXCEPT those marked with @pytest.mark.real_data.
    So real_data tests will use the actual data/historical/... directories.
    """
    # If the test has the "real_data" mark, do NOT patch it (i.e., use real folders).
    if "real_data" in request.keywords:
        return

    from pathlib import Path
    from src.core.config import StorageConfig
    from src.storage.processed import ProcessedDataStorage

    temp_dir = tmp_path_factory.mktemp("real_data_test")

    def mock_init(*args, **kwargs):
        storage_config = StorageConfig(
            data_path=temp_dir,
            historical_raw_path=temp_dir / "historical" / "raw",
            historical_processed_path=temp_dir / "historical" / "processed",
            live_raw_path=temp_dir / "live" / "raw",
            live_processed_path=temp_dir / "live" / "processed",
            use_compression=False
        )
        return ProcessedDataStorage(storage_config)

    try:
        import src.pytests.test_real_data_backtest
        # Replace references to ProcessedDataStorage with mock_init
        monkeypatch.setattr(
            'src.tests.test_real_data_backtest.ProcessedDataStorage',
            mock_init
        )
    except ImportError:
        pass

# -------------------------------------------------------------------------
# Optional: Example fixtures for testing new exchange handlers
# -------------------------------------------------------------------------
@pytest_asyncio.fixture
async def mock_coinbase_handler():
    """
    Example fixture for testing the updated CoinbaseHandler.
    This fixture starts the handler and stops it after tests finish.
    """
    from src.exchanges.coinbase import CoinbaseHandler
    from src.core.config import Config
    
    # Create a minimal config or a mock config
    config = Config()
    
    handler = CoinbaseHandler(config)
    await handler.start()
    yield handler
    await handler.stop()

@pytest_asyncio.fixture
async def mock_drift_handler():
    """
    Example fixture for testing the updated DriftHandler.
    """
    from src.exchanges.drift import DriftHandler
    from src.core.config import Config
    
    config = Config()
    
    handler = DriftHandler(config)
    await handler.start()
    yield handler
    await handler.stop()

# Add new fixtures for test categories
@pytest.fixture
def exchange_test_config():
    """Configuration for exchange tests."""
    from src.core.config import ExchangeConfig, ExchangeCredentials
    
    return ExchangeConfig(
        name="test_exchange",
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params={"passphrase": "test_passphrase"}
        ),
        rate_limit=10,
        markets=["BTC-PERP", "ETH-PERP", "SOL-PERP", "BTC-USD", "ETH-USD", "SOL-USD"],
        base_url="https://test.exchange.com",
        enabled=True
    )

@pytest.fixture
def backtest_config():
    """Configuration for backtest."""
    from src.core.config import Config
    return Config()
