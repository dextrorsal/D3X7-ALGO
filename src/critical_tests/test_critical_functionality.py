"""
Critical functionality tests for exchange connectivity and data fetching.
Run these tests first when returning to development to ensure core functionality.

To run all tests:
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py -v -p no:anchorpy

To run a specific test:
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py::TestCriticalExchangeFunctionality::test_name -v -p no:anchorpy

Example for Drift test:
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py::TestCriticalExchangeFunctionality::test_drift_basic_functionality -v -p no:anchorpy
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import asyncio
import contextlib

from core.config import ExchangeConfig, ExchangeCredentials
from core.models import TimeRange
from exchanges.drift_mock import MockDriftHandler  # Use the mock handler for testing
from exchanges.binance import BinanceHandler
from exchanges.coinbase import CoinbaseHandler
from storage.processed import ProcessedDataStorage

# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Configure pytest with proper asyncio settings."""
    config.addinivalue_line(
        "markers",
        "timeout: mark test to timeout after X seconds"
    )

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_config():
    """Create a mock exchange configuration."""
    return ExchangeConfig(
        name="test_exchange",
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params={}
        ),
        rate_limit=10,
        markets=["BTC-USDT", "ETH-USDT", "SOL-USDT", "BTC-PERP", "ETH-PERP", "SOL-PERP", "BTC-USD", "ETH-USD", "SOL-USD"],
        base_url="https://api.binance.com",  # Use actual Binance API URL
        enabled=True
    )

@pytest.fixture
def coinbase_config():
    """Return a test configuration for Coinbase."""
    return ExchangeConfig(
        name="coinbase",
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params={
                "passphrase": "test_passphrase"  # Required for Coinbase API
            }
        ),
        rate_limit=10,
        markets=["BTC-USD", "ETH-USD", "SOL-USD"],  # Standard Coinbase market format
        base_url="https://api.coinbase.com",
        enabled=True
    )

@pytest.fixture
def drift_config():
    """Return a test configuration for Drift."""
    return ExchangeConfig(
        name="drift",
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params={
                "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
                "rpc_url": "https://api.mainnet-beta.solana.com"
            }
        ),
        rate_limit=10,
        markets=["SOL-PERP", "BTC-PERP", "ETH-PERP"],
        base_url="https://data.api.drift.trade",
        enabled=True
    )

@pytest.fixture
def time_range():
    """Create a time range for testing."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    return TimeRange(start=start, end=end)

@pytest_asyncio.fixture(scope="function")
async def binance_handler(mock_config):
    """Create and initialize a Binance handler."""
    handler = BinanceHandler(mock_config)
    await handler.start()  # Initialize the session
    yield handler
    await handler.stop()  # Clean up

# ---------------------------------------------------------------------------
# Critical Exchange Tests
# ---------------------------------------------------------------------------
class TestCriticalExchangeFunctionality:
    """
    Critical tests that should be run first to verify exchange connectivity
    and data fetching capabilities.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_binance_connectivity(self, mock_config):
        """Test basic Binance connection and market data fetching."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Test market data fetching
                markets = await handler.get_markets()
                print("✅ Binance connectivity test passed")
                assert len(markets) > 0, "No markets returned"
        except Exception as e:
            print(f"❌ Binance connectivity test failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_historical_data_fetching(self, mock_config, time_range):
        """Test historical data fetching functionality."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Test historical candle fetching
                candles = await handler.fetch_historical_candles(
                    market="BTC-USDT",  # Changed from BTC-PERP to BTC-USDT for spot market
                    resolution="60",
                    time_range=time_range
                )
                print("✅ Historical data fetching test passed")
                assert len(candles) > 0, "No historical candles returned"
        except Exception as e:
            print(f"❌ Historical data fetching test failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_live_data_fetching(self, mock_config):
        """Test live data fetching functionality."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Test live candle fetching
                candle = await handler.fetch_live_candles(
                    market="BTC-USDT",  # Changed from BTC-PERP to BTC-USDT for spot market
                    resolution="1"
                )
                print("✅ Live data fetching test passed")
                assert candle is not None, "No live candle returned"
        except Exception as e:
            print(f"❌ Live data fetching test failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)  # Increased timeout for Drift
    async def test_drift_basic_functionality(self, drift_config):
        """Test basic Drift protocol functionality."""
        handler = None
        try:
            # Create and initialize Mock Drift handler
            handler = MockDriftHandler(drift_config)
            await handler.start()
            
            # Test market data fetching
            markets = await handler.get_markets()
            assert len(markets) > 0, "No markets returned"
            print("✅ Drift markets fetched successfully")

            # Test market validation
            assert handler.validate_market("SOL-PERP"), "SOL-PERP market not found"
            print("✅ Market validation passed")

        except Exception as e:
            print(f"❌ Drift basic functionality test failed: {e}")
            raise
        finally:
            if handler:
                await handler.stop()

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_coinbase_basic_functionality(self, coinbase_config):
        """Test basic Coinbase functionality including market data fetching and symbol conversion."""
        handler = None
        try:
            # Create and initialize Coinbase handler
            handler = CoinbaseHandler(coinbase_config)
            await handler.start()
            
            # Test market data fetching
            markets = await handler.get_markets()
            assert len(markets) > 0, "No markets returned"
            print(f"✅ Coinbase markets fetched successfully: {len(markets)} markets found")

            # Test market symbol conversion
            test_markets = [
                ("SOL-PERP", "SOL-USD"),  # Drift format to Coinbase
                ("SOLUSDT", "SOL-USD"),    # Binance format to Coinbase
                ("SOL-USD", "SOL-USD"),    # Already in Coinbase format
                ("BTC-USD", "BTC-USD")     # Standard format
            ]
            
            for input_market, expected_output in test_markets:
                converted = handler._convert_market_symbol(input_market)
                assert converted == expected_output, f"Market conversion failed: {input_market} -> {converted} (expected {expected_output})"
            print("✅ Market symbol conversion tests passed")

            # Test market validation
            assert handler.validate_market("BTC-USD"), "BTC-USD market not found"
            print("✅ Market validation passed")

        except Exception as e:
            print(f"❌ Coinbase basic functionality test failed: {e}")
            raise
        finally:
            if handler:
                await handler.stop()

if __name__ == "__main__":
    print("Running critical functionality tests...")
    pytest.main([__file__, "-v"])