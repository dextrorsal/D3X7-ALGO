"""
Critical functionality tests for exchange connectivity and data fetching.
Run these tests first when returning to development to ensure core functionality.

To run all tests:
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py -v -p no:anchorpy

To run with specific market format:
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py -v -p no:anchorpy --market-format=binance
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py -v -p no:anchorpy --market-format=coinbase
    PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/test_critical_functionality.py -v -p no:anchorpy --market-format=drift

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
from exchanges.binance_mock import MockBinanceHandler  # Add mock Binance handler
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
# Market Format Configuration
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    """Add market format option to pytest."""
    parser.addoption(
        "--exchange",
        action="store",
        default="binance",
        help="Exchange to test: binance, coinbase, or drift"
    )

@pytest.fixture
def exchange_name(request):
    """Get exchange name from CLI option."""
    try:
        return request.config.getoption("--exchange")
    except (ValueError, AttributeError):
        # Default to binance if the option is not provided
        return "binance"

@pytest.fixture
def test_markets(exchange_name):
    """
    Return test markets in the exchange-specific format.
    Each exchange has its own format for spot and perpetual markets:
    
    Binance:
        - Spot: BTCUSDT, ETHUSDT, SOLUSDT
        - Perp: BTCUSDT, ETHUSDT, SOLUSDT
        
    Coinbase:
        - Spot: BTC-USD, ETH-USD, SOL-USD
        - Perp: Not supported
        
    Drift:
        - Spot: BTC/USD, ETH/USD, SOL/USD
        - Perp: BTC-PERP, ETH-PERP, SOL-PERP
    """
    exchange_formats = {
        "binance": {
            "spot": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "perp": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        },
        "coinbase": {
            "spot": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "perp": []  # Coinbase doesn't support perpetual markets
        },
        "drift": {
            "spot": ["BTC/USD", "ETH/USD", "SOL/USD"],
            "perp": ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        }
    }
    return exchange_formats.get(exchange_name, exchange_formats["binance"])

@pytest.fixture
def mock_config(exchange_name, test_markets):
    """Create a mock exchange configuration specific to the selected exchange."""
    base_urls = {
        "binance": "https://api.binance.com",
        "coinbase": "https://api.coinbase.com",
        "drift": "https://api.drift.trade"
    }
    
    additional_params = {}
    if exchange_name == "coinbase":
        additional_params["passphrase"] = "test_passphrase"
    elif exchange_name == "drift":
        additional_params.update({
            "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
            "rpc_url": "https://api.mainnet-beta.solana.com"
        })

    return ExchangeConfig(
        name=exchange_name,
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params=additional_params
        ),
        rate_limit=10,
        markets=test_markets["spot"] + test_markets["perp"],
        base_url=base_urls[exchange_name],
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

@pytest.fixture
def binance_config():
    """Return a test configuration for Binance."""
    return ExchangeConfig(
        name="binance",
        credentials=ExchangeCredentials(
            api_key="test_key",
            api_secret="test_secret",
            additional_params={}
        ),
        rate_limit=10,
        markets=["BTC-USDT", "ETH-USDT", "SOL-USDT"],  # Standard Binance market format
        base_url="https://api.binance.com",
        enabled=True
    )

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
    async def test_binance_connectivity(self, mock_config, test_markets):
        """Test basic Binance connection and market data fetching."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Test market data fetching
                markets = await handler.get_markets()
                print(f"✅ Found {len(markets)} markets")
                assert len(markets) > 0, "No markets returned"
                
                # Verify test markets are available
                for market in test_markets["spot"]:
                    assert market in markets, f"Test market {market} not found"
                print("✅ All test markets verified")
                
        except Exception as e:
            print(f"❌ Binance connectivity test failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_historical_data_fetching(self, mock_config, time_range, test_markets):
        """Test historical data fetching functionality."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Force test mode
                handler._is_test_mode = True
                handler._setup_test_mode()
                
                # Test historical candle fetching for each spot market
                for market in test_markets["spot"]:
                    candles = await handler.fetch_historical_candles(
                        market=market,
                        resolution="60",
                        time_range=time_range
                    )
                    assert len(candles) > 0, f"No historical candles returned for {market}"
                    print(f"✅ Historical data fetched for {market}")
                    
        except Exception as e:
            print(f"❌ Historical data fetching test failed: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_live_data_fetching(self, mock_config, test_markets):
        """Test live data fetching functionality."""
        try:
            async with BinanceHandler(mock_config) as handler:
                # Force test mode
                handler._is_test_mode = True
                handler._setup_test_mode()
                
                # Test live candle fetching for each spot market
                for market in test_markets["spot"]:
                    candle = await handler.fetch_live_candles(
                        market=market,
                        resolution="1"
                    )
                    assert candle is not None, f"No live candle returned for {market}"
                    print(f"✅ Live data fetched for {market}")
                    
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

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_binance_basic_functionality(self, binance_config):
        """Test basic Binance functionality using mock handler."""
        handler = None
        try:
            # Create and initialize Mock Binance handler
            handler = MockBinanceHandler(binance_config)
            await handler.start()
            
            # Test market data fetching
            markets = await handler.get_markets()
            assert len(markets) > 0, "No markets returned"
            print(f"✅ Binance markets fetched successfully: {len(markets)} markets found")

            # Test market symbol conversion
            test_markets = [
                ("BTC-PERP", "BTCUSDT"),   # Drift format to Binance
                ("BTC-USD", "BTCUSDT"),    # Coinbase format to Binance
                ("BTC-USDT", "BTCUSDT"),   # Already in Binance format
                ("ETH-USDT", "ETHUSDT")    # Standard format
            ]
            
            for input_market, expected_output in test_markets:
                converted = handler._convert_market_symbol(input_market)
                assert converted == expected_output, f"Market conversion failed: {input_market} -> {converted} (expected {expected_output})"
            print("✅ Market symbol conversion tests passed")

            # Test market validation
            assert handler.validate_market("BTC-USDT"), "BTC-USDT market not found"
            print("✅ Market validation passed")

            # Test historical data fetching
            time_range = TimeRange(
                start=datetime.now(timezone.utc) - timedelta(hours=1),
                end=datetime.now(timezone.utc)
            )
            candles = await handler.fetch_historical_candles(
                market="BTC-USDT",
                time_range=time_range,
                resolution="1"
            )
            assert len(candles) > 0, "No historical candles returned"
            print("✅ Historical data fetching passed")

            # Test live data fetching
            live_candle = await handler.fetch_live_candles(
                market="BTC-USDT",
                resolution="1"
            )
            assert live_candle is not None, "No live candle returned"
            print("✅ Live data fetching passed")

        except Exception as e:
            print(f"❌ Binance basic functionality test failed: {e}")
            raise
        finally:
            if handler:
                await handler.stop()

if __name__ == "__main__":
    print("Running critical functionality tests...")
    pytest.main([__file__, "-v"])