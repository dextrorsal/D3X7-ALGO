"""
Simplified mock DriftHandler for testing purposes.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from core.config import ExchangeConfig
from core.models import TimeRange, StandardizedCandle
from exchanges.base import BaseExchangeHandler
from core.exceptions import ExchangeError, ValidationError

logger = logging.getLogger(__name__)

class MockDriftHandler(BaseExchangeHandler):
    """A simplified mock version of DriftHandler for testing."""

    def __init__(self, config: ExchangeConfig):
        """Initialize the MockDriftHandler."""
        super().__init__(config)
        self.base_url = config.base_url or "https://data.api.drift.trade"
        self._available_markets = ["SOL-PERP", "BTC-PERP", "ETH-PERP", "SOL-SPOT", "BTC-SPOT", "ETH-SPOT"]
        logger.info("Initialized MockDriftHandler")

    async def start(self):
        """Initialize connections and client."""
        logger.info("MockDriftHandler started")

    async def stop(self):
        """Cleanup connections and client."""
        logger.info("MockDriftHandler stopped")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def get_markets(self) -> List[str]:
        """Get a list of available markets."""
        return self._available_markets

    def validate_market(self, market_symbol: str) -> bool:
        """
        Validate if a market symbol is supported.

        Parameters:
        - market_symbol: The market symbol to validate (e.g., "SOL-PERP").

        Returns:
        - True if the market is supported, False otherwise.
        """
        market_symbol = market_symbol.upper()
        return market_symbol in self._available_markets

    async def fetch_historical_candles(self, market_symbol: str, time_range: TimeRange, resolution: str) -> List[StandardizedCandle]:
        """Mock fetch historical candles."""
        # Return a simple mock candle
        candle = StandardizedCandle(
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
            source="drift",
            resolution=resolution,
            market=market_symbol,
            raw_data={}
        )
        return [candle]

    async def fetch_live_candles(self, market: str, resolution: str) -> StandardizedCandle:
        """Mock fetch live candles."""
        # Return a simple mock candle
        return StandardizedCandle(
            timestamp=datetime.now(timezone.utc),
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
            source="drift",
            resolution=resolution,
            market=market,
            raw_data={}
        ) 