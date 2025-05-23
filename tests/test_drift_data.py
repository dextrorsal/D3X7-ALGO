"""Test Drift data provider functionality."""

import asyncio
import logging
from datetime import datetime, timezone
from solders.keypair import Keypair
from unittest.mock import AsyncMock, patch

from src.exchanges.drift.client import DriftClient
from src.exchanges.drift.data import DriftDataProvider
from src.core.models import TimeRange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_historical_data():
    """Test fetching historical data."""
    with (
        patch("src.exchanges.drift.client.DriftClient") as MockDriftClient,
        patch("src.exchanges.drift.data.DriftDataProvider") as MockDriftDataProvider,
    ):
        # Set up mock client and provider
        mock_client = MockDriftClient.return_value
        mock_client.initialize = AsyncMock()
        mock_client.get_markets = AsyncMock(return_value=["BTC-PERP"])
        mock_provider = MockDriftDataProvider.return_value
        mock_provider.get_markets = AsyncMock(return_value=["BTC-PERP"])
        mock_provider.fetch_historical_candles = AsyncMock(return_value=["mock_candle"])
        mock_provider.fetch_live_candle = AsyncMock(return_value="mock_live_candle")
        mock_provider.cleanup = AsyncMock()

        # Set up time range
        now = datetime.now(timezone.utc)
        end_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if end_time.month == 1:
            start_time = end_time.replace(year=end_time.year - 1, month=12)
        else:
            start_time = end_time.replace(month=end_time.month - 1)
        test_time = datetime(2024, 3, 1, tzinfo=timezone.utc)
        start_time = test_time.replace(month=2)
        end_time = test_time
        time_range = TimeRange(start=start_time, end=end_time)

        # Use mocks
        await mock_client.initialize()
        data_provider = MockDriftDataProvider(mock_client)
        markets = await data_provider.get_markets()
        assert markets == ["BTC-PERP"]
        candles = await data_provider.fetch_historical_candles(
            market="BTC-PERP", time_range=time_range, resolution="1h"
        )
        assert candles == ["mock_candle"]
        live_candle = await data_provider.fetch_live_candle(
            market="BTC-PERP", resolution="1m"
        )
        assert live_candle == "mock_live_candle"
        await data_provider.cleanup()


if __name__ == "__main__":
    asyncio.run(test_historical_data())
