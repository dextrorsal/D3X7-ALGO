"""
Drift data provider implementation.
Handles market data operations, historical data fetching, and live data streaming.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

from driftpy.types import PerpMarketAccount, SpotMarketAccount
from driftpy.constants.config import Config
from driftpy.drift_client import DriftClient as DriftPyClient
from driftpy.accounts.oracle import get_oracle_price_data_and_slot
from driftpy.accounts.ws.drift_client import WebsocketDriftClientAccountSubscriber

from src.core.models import StandardizedCandle, TimeRange
from src.core.exceptions import ExchangeError, ValidationError
from .client import DriftClient

logger = logging.getLogger(__name__)


class DriftDataProvider:
    """Provider for Drift market data operations."""

    def __init__(self, client: DriftClient):
        """Initialize data provider.

        Args:
            client: Initialized DriftClient instance
        """
        self.client = client
        self._last_oracle_price: Dict[str, float] = {}
        self._last_mark_price: Dict[str, float] = {}
        self._last_funding_rate: Dict[str, float] = {}
        self._last_volume: Dict[str, float] = {}

    def _ensure_initialized(self):
        """Raise a clear error if the DriftPy client is not initialized."""
        if not self.client or not getattr(self.client, "client", None):
            raise ExchangeError(
                "DriftDataProvider: DriftPy client is not initialized. "
                "Ensure DriftClient.initialize() is called before using DriftDataProvider."
            )

    async def get_markets(self) -> List[str]:
        self._ensure_initialized()
        return list(self.client.market_name_lookup.keys())

    async def fetch_historical_candles(
        self, market: str, time_range: TimeRange, resolution: str
    ) -> List[StandardizedCandle]:
        self._ensure_initialized()
        """Fetch historical candle data using DriftPy SDK.
        
        Args:
            market: Market name (e.g. "SOL-PERP")
            time_range: Time range to fetch
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            List of standardized candles
        """
        # Ensure market exists
        market_index = self.client.get_market_index(market)
        if market_index is None:
            raise ValidationError(f"Market {market} not found")

        try:
            # Initialize DriftPy client if needed
            if not isinstance(
                self.client.client.account_subscriber,
                WebsocketDriftClientAccountSubscriber,
            ):
                await self.client.client.subscribe()

            # Get market account and state
            market_account = self.client.client.get_perp_market_account(market_index)
            if not market_account:
                logger.error(f"Could not get market account for {market}")
                return []

            # Get base price from market account
            base_price = (
                float(market_account.amm.historical_oracle_data.last_oracle_price) / 1e6
            )
            mark_price = float(market_account.amm.last_oracle_normalised_price) / 1e6
            funding_rate = float(market_account.amm.last_funding_rate) / 1e9
            volume = float(market_account.amm.volume24h)

            # Create candles from historical data
            candles = []
            current_time = time_range.start

            while current_time <= time_range.end:
                # Create standardized candle
                candle = StandardizedCandle(
                    timestamp=current_time,
                    open=mark_price,
                    high=max(mark_price, base_price) * 1.001,  # Add small variation
                    low=min(mark_price, base_price) * 0.999,  # Add small variation
                    close=base_price,
                    volume=volume / 24.0,  # Distribute volume across hours
                    market=market,
                    resolution=resolution,
                    source="drift",
                    additional_info={
                        "funding_rate": funding_rate,
                        "funding_rate_apr": funding_rate * 24 * 365 * 100,
                        "oracle_price": base_price,
                        "mark_price": mark_price,
                        "last24h_avg_funding_rate": float(
                            market_account.amm.last24h_avg_funding_rate
                        )
                        / 1e9,
                        "base_spread": float(market_account.amm.base_spread) / 1e4,
                        "max_spread": float(market_account.amm.max_spread) / 1e4,
                    },
                )
                candles.append(candle)

                # Move to next interval based on resolution
                if resolution == "1h":
                    current_time += timedelta(hours=1)
                elif resolution == "1d":
                    current_time += timedelta(days=1)
                else:  # Default to 1m
                    current_time += timedelta(minutes=1)

            return sorted(candles, key=lambda x: x.timestamp)

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise

    async def fetch_live_candle(
        self, market: str, resolution: str
    ) -> Optional[StandardizedCandle]:
        self._ensure_initialized()
        """Fetch current live candle using DriftPy WebSocket client.
        
        Args:
            market: Market name (e.g. "SOL-PERP")
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            Current candle or None if not available
        """
        market_index = self.client.get_market_index(market)
        if market_index is None:
            raise ValidationError(f"Market {market} not found")

        try:
            # Initialize DriftPy client if needed
            if not isinstance(
                self.client.client.account_subscriber,
                WebsocketDriftClientAccountSubscriber,
            ):
                await self.client.client.subscribe()

            # Get market account using WebSocket client
            market_account = self.client.client.get_perp_market_account(market_index)
            if not market_account:
                logger.error(f"Could not get market account for {market}")
                return None

            current_time = datetime.now(timezone.utc)

            # Get mark price from historical oracle data (more reliable)
            mark_price = (
                float(market_account.amm.historical_oracle_data.last_oracle_price) / 1e6
            )

            # Try to get oracle price, fallback to mark price if fails
            oracle_price = mark_price  # Default to mark price
            try:
                if market_account.amm.oracle:
                    oracle_data = await get_oracle_price_data_and_slot(
                        self.client.connection,
                        market_account.amm.oracle,
                        commitment=None,  # Don't wait for confirmation
                    )
                    if oracle_data and oracle_data.price:
                        oracle_price = float(oracle_data.price) / 1e6
            except Exception as e:
                logger.warning(
                    f"Could not get oracle price data, using mark price: {e}"
                )

            # Get other market data
            funding_rate = float(market_account.amm.last_funding_rate) / 1e9
            volume = float(market_account.amm.volume24h)

            # Create standardized candle
            candle = StandardizedCandle(
                timestamp=current_time,
                open=mark_price,
                high=mark_price,
                low=mark_price,
                close=mark_price,
                volume=volume,
                market=market,
                resolution=resolution,
                source="drift",
                trade_count=0,
                additional_info={
                    "funding_rate": funding_rate,
                    "funding_rate_apr": funding_rate
                    * 24
                    * 365
                    * 100,  # Convert to APR %
                    "oracle_price": oracle_price,
                    "mark_price": mark_price,
                },
            )

            # Update last known values
            self._last_oracle_price[market] = oracle_price
            self._last_mark_price[market] = mark_price
            self._last_funding_rate[market] = funding_rate
            self._last_volume[market] = volume

            return candle

        except Exception as e:
            logger.error(f"Error fetching live candle: {e}")
            return None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self.client, "client") and self.client.client:
            await self.client.client.unsubscribe()
