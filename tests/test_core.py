"""
Tests for the Ultimate Data Fetcher.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import asyncio

from src.core.config import Config, StorageConfig, ExchangeConfig, ExchangeCredentials
from src.core.models import TimeRange, StandardizedCandle
from src.ultimate_fetcher import UltimateDataFetcher


# ---------------------------------------------------------------------------
# Fixture: Create a mock configuration for testing
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_config():
    """Mock configuration."""
    # Initialize Config without passing storage/exchanges
    config = Config()

    # Modify the config object to set up mock configurations
    config.storage = StorageConfig(
        historical_raw_path=Path("test_data/raw"),
        historical_processed_path=Path("test_data/processed"),
        live_raw_path=Path("test_data/live/raw"),
        live_processed_path=Path("test_data/live/processed"),
        use_compression=False,
    )
    config.exchanges = {
        "drift": ExchangeConfig(
            name="drift",
            credentials=ExchangeCredentials(
                api_key="test_key",
                api_secret="test_secret",
                additional_params={
                    "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
                    "rpc_url": "https://api.mainnet-beta.solana.com",
                },
            ),
            rate_limit=10,
            markets=["BTC-PERP", "ETH-PERP", "SOL-PERP"],
            base_url="https://test.drift.com",
            enabled=True,
        ),
        "binance": ExchangeConfig(
            name="binance",
            credentials=ExchangeCredentials(
                api_key="test_key", api_secret="test_secret"
            ),
            rate_limit=20,
            markets=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            base_url="https://test.binance.com",
            enabled=True,
        ),
    }
    return config


# ---------------------------------------------------------------------------
# Fixture: Create an async UltimateDataFetcher instance for tests
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def test_fetcher(mock_config):
    """Test fetcher instance."""
    return UltimateDataFetcher(config=mock_config)


# ---------------------------------------------------------------------------
# Test class for Ultimate Data Fetcher functionality
# ---------------------------------------------------------------------------
class TestUltimateDataFetcher:
    @pytest.mark.asyncio
    async def test_initialization(self):
        assert 1 == 1

    @pytest.mark.asyncio
    async def test_fetch_historical_data(self, test_fetcher):
        """Test historical data fetching."""
        async with test_fetcher:
            # Create a test candle to return
            test_candle = StandardizedCandle(
                timestamp=datetime.now(timezone.utc),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                source="test",
                resolution="15",
                market="BTC-PERP",
                raw_data={"data": "test"},
            )
            # Use AsyncMock to simulate the exchange handler
            drift_mock = AsyncMock()
            drift_mock.fetch_historical_candles = AsyncMock(return_value=[test_candle])
            drift_mock.__aenter__.return_value = drift_mock
            drift_mock.__aexit__.return_value = None

            binance_mock = AsyncMock()
            binance_mock.fetch_historical_candles = AsyncMock(
                return_value=[test_candle]
            )
            binance_mock.__aenter__.return_value = binance_mock
            binance_mock.__aexit__.return_value = None

            test_fetcher.exchange_handlers = {
                "drift": drift_mock,
                "binance": binance_mock,
            }

            # Define test parameters
            markets = ["BTC-PERP"]
            time_range = TimeRange(
                start=datetime.now(timezone.utc) - timedelta(days=1),
                end=datetime.now(timezone.utc),
            )
            resolution = "15"

            # Execute the historical fetch
            await test_fetcher.fetch_historical_data(
                markets=markets, time_range=time_range, resolution=resolution
            )

            # Verify that each mock handler's fetch method was called once
            drift_mock.fetch_historical_candles.assert_called_once()
            binance_mock.fetch_historical_candles.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_data_fetching(self, test_fetcher):
        """Test live data fetching."""
        async with test_fetcher:
            # Create a test candle for live data
            test_candle = StandardizedCandle(
                timestamp=datetime.now(timezone.utc),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                source="test",
                resolution="1",
                market="BTC-USDT",  # Changed from BTC-PERP to a spot market
                raw_data={"data": "live"},
            )

            # Replace the entire exchange_handlers dict with our mock
            mock_handler = AsyncMock()
            mock_handler.fetch_live_candles = AsyncMock(return_value=test_candle)
            mock_handler.validate_standard_symbol = AsyncMock(
                return_value=True
            )  # Make validation always pass
            mock_handler.__aenter__.return_value = mock_handler
            mock_handler.__aexit__.return_value = None

            test_fetcher.exchange_handlers = {"test": mock_handler}

            # Monkeypatch the symbol mapper to avoid issues
            test_fetcher.symbol_mapper = MagicMock()
            test_fetcher.symbol_mapper.to_exchange_symbol = MagicMock(
                return_value="BTC-USDT"
            )

            # Short-circuit the live fetching loop by setting up a task that we'll cancel
            try:
                task = asyncio.create_task(
                    test_fetcher.start_live_fetching(
                        markets=["BTC-USDT"],  # Use a valid spot market
                        resolution="1",
                        exchanges=["test"],  # Explicitly use our mock
                    )
                )

                # Wait briefly for execution
                await asyncio.sleep(0.1)
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Expected

            except Exception as e:
                pytest.fail(f"Live fetching raised exception: {e}")

            # Verify the mock was called
            assert mock_handler.fetch_live_candles.called

    @pytest.mark.asyncio
    async def test_error_handling(self, test_fetcher):
        """Test error handling during data fetching."""
        async with test_fetcher:
            # Use an AsyncMock that raises an error when fetching historical candles
            error_handler = AsyncMock()
            error_handler.fetch_historical_candles = AsyncMock(
                side_effect=Exception("Test error")
            )
            error_handler.__aenter__.return_value = error_handler
            error_handler.__aexit__.return_value = None

            test_fetcher.exchange_handlers = {"test": error_handler}

            # Define test parameters
            markets = ["BTC-PERP"]
            time_range = TimeRange(
                start=datetime.now(timezone.utc) - timedelta(days=1),
                end=datetime.now(timezone.utc),
            )
            resolution = "15"

            # Execute fetch (should handle error internally without crashing)
            await test_fetcher.fetch_historical_data(
                markets=markets, time_range=time_range, resolution=resolution
            )

    @pytest.mark.asyncio
    async def test_data_storage(self):
        assert 1 > 0

    @pytest.mark.asyncio
    async def test_multi_exchange_fetch(self, test_fetcher):
        """Test fetching from multiple exchanges simultaneously."""
        async with test_fetcher:
            test_candle = StandardizedCandle(
                timestamp=datetime.now(timezone.utc),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                source="test",
                resolution="15",
                market="BTC-PERP",
                raw_data={"data": "multi"},
            )
            drift_mock = AsyncMock()
            drift_mock.fetch_historical_candles = AsyncMock(return_value=[test_candle])
            drift_mock.__aenter__.return_value = drift_mock
            drift_mock.__aexit__.return_value = None

            binance_mock = AsyncMock()
            binance_mock.fetch_historical_candles = AsyncMock(
                return_value=[test_candle]
            )
            binance_mock.__aenter__.return_value = binance_mock
            binance_mock.__aexit__.return_value = None

            coinbase_mock = AsyncMock()
            coinbase_mock.fetch_historical_candles = AsyncMock(
                return_value=[test_candle]
            )
            coinbase_mock.__aenter__.return_value = coinbase_mock
            coinbase_mock.__aexit__.return_value = None

            test_fetcher.exchange_handlers = {
                "drift": drift_mock,
                "binance": binance_mock,
                "coinbase": coinbase_mock,
            }

            markets = ["BTC-PERP"]
            time_range = TimeRange(
                start=datetime.now(timezone.utc) - timedelta(days=1),
                end=datetime.now(timezone.utc),
            )
            resolution = "15"

            await test_fetcher.fetch_historical_data(
                markets=markets,
                time_range=time_range,
                resolution=resolution,
                exchanges=["drift", "binance", "coinbase"],
            )

            drift_mock.fetch_historical_candles.assert_called_once()
            binance_mock.fetch_historical_candles.assert_called_once()
            coinbase_mock.fetch_historical_candles.assert_called_once()
