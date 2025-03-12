"""
DriftHandler implementation with conditional imports for DriftPy SDK.
"""
import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
import aiohttp
import json
import sys
import importlib.util
import os
from dotenv import load_dotenv
import asyncio
from collections import defaultdict
import random

from src.core.models import StandardizedCandle, TimeRange
from src.exchanges.base import BaseExchangeHandler
from src.core.exceptions import ExchangeError, ValidationError
from src.core.config import ExchangeConfig, ExchangeCredentials
from driftpy.constants.config import configs
from driftpy.drift_client import DriftClient
from anchorpy import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solana.rpc.api import Client
from src.utils.time_utils import (
    convert_timestamp_to_datetime,
    get_current_timestamp,
    get_timestamp_from_datetime,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try to import specific DriftPy functions for market access
try:
    if importlib.util.find_spec("driftpy") is not None:
        try:
            from driftpy.accounts import get_perp_market_account, get_spot_market_account
            logger.info("Successfully imported DriftPy market account functions")
        except ImportError as e:
            logger.warning(f"Failed to import DriftPy market account functions: {e}")
except Exception as e:
    logger.warning(f"Error importing DriftPy modules: {e}")

# Check Python version for DriftPy compatibility
PY_VERSION = sys.version_info
DRIFTPY_COMPATIBLE = PY_VERSION.major == 3 and PY_VERSION.minor >= 10

# Try to import DriftPy and related packages
if DRIFTPY_COMPATIBLE:
    try:
        # Check if driftpy is installed
        if importlib.util.find_spec("driftpy") is not None:
            from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
            DRIFTPY_AVAILABLE = True
            logger.info("DriftPy SDK is available and imported successfully")
        else:
            DRIFTPY_AVAILABLE = False
            logger.warning("DriftPy SDK is not installed")
    except ImportError as e:
        DRIFTPY_AVAILABLE = False
        logger.warning(f"Failed to import DriftPy modules: {e}")
else:
    DRIFTPY_AVAILABLE = False
    logger.warning(f"Python {PY_VERSION.major}.{PY_VERSION.minor} is not compatible with DriftPy (requires Python 3.10+)")

class DriftHandler(BaseExchangeHandler):
    """Handler for Drift exchange."""

    def __init__(self, config: ExchangeConfig):
        """Initialize DriftHandler with configuration."""
        super().__init__(config)
        self.base_url = config.base_url
        self.rpc_url = config.credentials.additional_params.get("rpc_url") if config.credentials else None
        self.program_id = config.credentials.additional_params.get("program_id") if config.credentials else None
        self._is_test_mode = False
        self._mock_markets = ["SOL-PERP", "BTC-PERP", "ETH-PERP", "SOL-USDC", "BTC-USDC", "ETH-USDC"]
        self.client = None

    async def _initialize_drift_client(self) -> None:
        """Initialize the Drift client."""
        try:
            # Create a mock wallet for testing
            mock_wallet = Keypair()
            
            # Initialize the Drift client with mock wallet
            self.client = DriftClient(
                connection=AsyncClient(self.rpc_url) if self.rpc_url else None,
                wallet=mock_wallet,
                program_id=self.program_id,
                opts={"commitment": "processed"}
            )
            logger.info("Successfully initialized Drift client with mock wallet")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Drift client: {e}. Falling back to test mode.")
            self._is_test_mode = True

    async def start(self) -> None:
        """Start the handler."""
        try:
            await self._initialize_drift_client()
        except Exception as e:
            logger.warning(f"Failed to start Drift handler: {e}. Operating in test mode.")
            self._is_test_mode = True

    async def stop(self) -> None:
        """Stop the handler."""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning(f"Error closing Drift client: {e}")

    async def get_markets(self) -> List[str]:
        """Get available markets."""
        if self._is_test_mode:
            logger.info("Using mock markets for testing")
            return self._mock_markets
            
        try:
            if not self.client:
                raise ExchangeError("Drift client not initialized")
                
            markets = await self.client.get_perp_markets()
            return [market.symbol for market in markets if market.status == "ACTIVE"]
            
        except Exception as e:
            logger.warning(f"Error fetching markets: {e}. Using mock markets.")
            return self._mock_markets

    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information."""
        info = {
            "name": self.config.name,
            "markets": await self.get_markets(),
            "timeframes": ["1", "5", "15", "30", "60", "240", "1D"],
            "description": "Drift Protocol - Solana's most advanced perpetual futures DEX"
        }
        return info

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str = "15"
    ) -> List[StandardizedCandle]:
        """
        Fetch historical candlestick data.
        
        Args:
            market: Market symbol (e.g., "SOL-PERP")
            time_range: Time range to fetch data for
            resolution: Candle resolution in minutes
            
        Returns:
            List of StandardizedCandle objects
        """
        if self._is_test_mode:
            # Generate mock candles for testing
            candles = []
            current_time = time_range.start
            while current_time <= time_range.end:
                candle = StandardizedCandle(
                    timestamp=current_time,
                    open=100.0 + random.uniform(-5, 5),
                    high=105.0 + random.uniform(-5, 5),
                    low=95.0 + random.uniform(-5, 5),
                    close=102.0 + random.uniform(-5, 5),
                    volume=1000.0 + random.uniform(-100, 100),
                    source="drift",
                    resolution=resolution,
                    market=market,
                    raw_data={"mock": True}
                )
                candles.append(candle)
                current_time += timedelta(minutes=int(resolution))
            return candles
            
        try:
            if not self.client:
                raise ExchangeError("Drift client not initialized")
                
            # Convert timestamps to milliseconds
            start_ts = int(time_range.start.timestamp() * 1000)
            end_ts = int(time_range.end.timestamp() * 1000)
            
            # Fetch candles from Drift
            raw_candles = await self.client.get_candles(
                market=market,
                resolution=resolution,
                start_time=start_ts,
                end_time=end_ts
            )
            
            # Convert to StandardizedCandle format
            candles = []
            for raw in raw_candles:
                candle = StandardizedCandle(
                    timestamp=datetime.fromtimestamp(raw["time"] / 1000, tz=timezone.utc),
                    open=float(raw["open"]),
                    high=float(raw["high"]),
                    low=float(raw["low"]),
                    close=float(raw["close"]),
                    volume=float(raw["volume"]),
                    source="drift",
                    resolution=resolution,
                    market=market,
                    raw_data=raw
                )
                candles.append(candle)
                
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching historical candles: {e}")
            raise ExchangeError(f"Failed to fetch historical candles: {e}")

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str = "1"
    ) -> StandardizedCandle:
        """
        Fetch live candlestick data.
        
        Args:
            market: Market symbol (e.g., "SOL-PERP")
            resolution: Candle resolution in minutes
            
        Returns:
            StandardizedCandle object
        """
        if self._is_test_mode:
            # Generate a mock live candle
            return StandardizedCandle(
                timestamp=datetime.now(timezone.utc),
                open=100.0 + random.uniform(-5, 5),
                high=105.0 + random.uniform(-5, 5),
                low=95.0 + random.uniform(-5, 5),
                close=102.0 + random.uniform(-5, 5),
                volume=1000.0 + random.uniform(-100, 100),
                source="drift",
                resolution=resolution,
                market=market,
                raw_data={"mock": True}
            )
            
        try:
            if not self.client:
                raise ExchangeError("Drift client not initialized")
                
            # Fetch the latest candle
            raw_candles = await self.client.get_candles(
                market=market,
                resolution=resolution,
                limit=1
            )
            
            if not raw_candles:
                raise ExchangeError("No live data available")
                
            raw = raw_candles[0]
            return StandardizedCandle(
                timestamp=datetime.fromtimestamp(raw["time"] / 1000, tz=timezone.utc),
                open=float(raw["open"]),
                high=float(raw["high"]),
                low=float(raw["low"]),
                close=float(raw["close"]),
                volume=float(raw["volume"]),
                source="drift",
                resolution=resolution,
                market=market,
                raw_data=raw
            )
            
        except Exception as e:
            logger.error(f"Error fetching live candles: {e}")
            raise ExchangeError(f"Failed to fetch live candles: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def _get_drift_client(self) -> DriftClient:
        """Get the DriftClient instance, initializing if necessary."""
        if not self.client:
            await self.start()
        return self.client

    def create_candles_from_trades(self, trades: List[Dict], resolution: str) -> List[StandardizedCandle]:
        """
        Create candlestick data from historical trades based on the specified resolution.

        Parameters:
        - trades: A list of historical trade data.
        - resolution: The resolution for the candlestick data (e.g., "1m", "15m", "1h", "1d", "1w").

        Returns:
        - A list of StandardizedCandle objects.
        """
        # Define resolution in seconds
        resolution_map = {
            "1m": 60,
            "15m": 900,
            "1h": 3600,
            "1d": 86400,
            "1w": 604800
        }
        
        if resolution not in resolution_map:
            raise ValueError(f"Unsupported resolution: {resolution}")

        resolution_seconds = resolution_map[resolution]
        candles = []
        grouped_trades = defaultdict(list)

        # Group trades by the resolution
        for trade in trades:
            trade_time = datetime.fromtimestamp(trade['timestamp'], tz=timezone.utc)
            # Calculate the start of the candle period
            candle_start = trade_time - timedelta(seconds=trade_time.second % resolution_seconds,
                                                  microseconds=trade_time.microsecond)
            grouped_trades[candle_start].append(trade)

        # Create candles from grouped trades
        for candle_start, trades in grouped_trades.items():
            open_price = trades[0]['price']
            high_price = max(trade['price'] for trade in trades)
            low_price = min(trade['price'] for trade in trades)
            close_price = trades[-1]['price']
            volume = sum(trade['size'] for trade in trades)

            candle = StandardizedCandle(
                timestamp=candle_start,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                source="drift",
                resolution=resolution,
                market=trades[0]['market'],
                raw_data=trades
            )
            candles.append(candle)

        return candles

    async def get_historical_data(self, market_symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Fetch raw historical trade data for a market.
        This method returns the raw trade data without aggregation.

        Parameters:
        - market_symbol: The market symbol (e.g., "SOL-PERP").
        - start_date: The start date for fetching historical data.
        - end_date: The end date for fetching historical data.

        Returns:
        - A list of raw trade data.
        """
        logger.info(f"Fetching historical trade data for {market_symbol} from {start_date} to {end_date}")
        
        try:
            # Fetch historical trades using the SDK
            historical_trades = await self._drift_client.get_historical_trades(market_symbol, start_date, end_date)
            return historical_trades

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            raise ExchangeError(f"Failed to fetch historical data: {e}")

    async def get_latest_candle(self, market_symbol: str) -> Optional[StandardizedCandle]:
        """
        Fetch the most recent candle data for a market.
        Uses the latest trade data to create a single candlestick.

        Parameters:
        - market_symbol: The market symbol (e.g., "SOL-PERP").
        """
        logger.info(f"Fetching latest candle for {market_symbol}")
        
        try:
            # Fetch the latest trade data using the SDK
            latest_trade = await self._drift_client.get_latest_trade(market_symbol)
            candle = self.create_candle_from_trade(latest_trade)  # Implement this function to create a candle
            return candle

        except Exception as e:
            logger.error(f"Error fetching latest candle: {e}")
            raise ExchangeError(f"Failed to fetch latest candle: {e}")
    
    async def fetch_live_candle(self, market: str, resolution: str) -> Optional[StandardizedCandle]:
        """
        Fetch the most recent candle from Drift.
        Uses SDK if available, otherwise falls back to HTTP API.
        """
        # Try SDK method first if available
        if DRIFTPY_COMPATIBLE:
            try:
                return await self._fetch_live_candle_sdk(market, resolution)
            except Exception as e:
                logger.warning(f"SDK live candle method failed, falling back to HTTP: {e}")
                # Fall back to HTTP method
        
        # HTTP fallback method
        try:
            # Get current time
            now = datetime.now(timezone.utc)
            
            # Calculate start time based on resolution
            resolution_seconds = self._get_resolution_seconds(resolution)
            start_time = now - timedelta(seconds=resolution_seconds)
            
            # Create time range
            time_range = TimeRange(start=start_time, end=now)
            
            # Fetch candles
            candles = await self.fetch_historical_candles(market, time_range, resolution)
            
            # Return the most recent candle
            if candles:
                return candles[-1]
                
            return None
            
        except Exception as e:
            logger.error(f"Error fetching live candle: {e}")
            raise ExchangeError(f"Failed to fetch live candle: {e}")
    
    async def _fetch_live_candle_sdk(self, market: str, resolution: str) -> StandardizedCandle:
        """Fetch live candle using the DriftPy SDK."""
        if not DRIFTPY_COMPATIBLE:
            raise ExchangeError("DriftPy SDK is not available")
            
        try:
            # Get Drift client
            client = await self._get_drift_client()
            
            # Get market info
            market_info = await self._get_market_info(market)
            
            if market_info["type"] == "perp":
                # Get perp market account
                market_account = await get_perp_market_account(
                    client.program, 
                    client.drift_program_id, 
                    market_info["index"]
                )
                
                # Get market price
                price = market_account.amm.oracle_price_data.price / QUOTE_PRECISION
                
                # Create a candle with current price
                candle = StandardizedCandle(
                    timestamp=datetime.now(timezone.utc),
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=0.0,  # Volume not available in this context
                    source="drift",
                    resolution=resolution,
                    market=market,
                    raw_data={"price": price}
                )
                
            else:  # spot market
                market_account = await get_spot_market_account(
                    client.program, 
                    client.drift_program_id, 
                    market_info["index"]
                )
                
                # Get market price
                price = market_account.oracle_price_data.price / QUOTE_PRECISION
                
                # Create a candle with current price
                candle = StandardizedCandle(
                    timestamp=datetime.now(timezone.utc),
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=0.0,  # Volume not available in this context
                    source="drift",
                    resolution=resolution,
                    market=market,
                    raw_data={"price": price}
                )
            
            return candle
            
        except Exception as e:
            logger.error(f"Error fetching live data with SDK: {e}")
            raise ExchangeError(f"Failed to fetch live candle with SDK: {e}")
    
    def _parse_raw_candle(self, raw_data: Dict, market: str, resolution: str) -> StandardizedCandle:
        """Parse raw candle data into StandardizedCandle object."""
        try:
            # Convert timestamp to datetime
            if isinstance(raw_data.get('timestamp'), (int, float)):
                timestamp = datetime.fromtimestamp(raw_data['timestamp'] / 1000, tz=timezone.utc)
            elif 'start' in raw_data:
                timestamp = self.standardize_timestamp(raw_data['start'])
            elif 'ts' in raw_data:
                timestamp = datetime.fromtimestamp(raw_data['ts'], tz=timezone.utc)
            else:
                timestamp = self.standardize_timestamp(raw_data['timestamp'])
                
            # Create StandardizedCandle
            candle = StandardizedCandle(
                timestamp=timestamp,
                open=float(raw_data.get('open', 0)),
                high=float(raw_data.get('high', 0)),
                low=float(raw_data.get('low', 0)),
                close=float(raw_data.get('close', 0)),
                volume=float(raw_data.get('volume', 0)),
                source="drift",
                resolution=resolution,
                market=market,
                raw_data=raw_data
            )
            
            return candle
            
        except Exception as e:
            logger.error(f"Error parsing candle: {e}")
            raise ValidationError(f"Failed to parse candle: {e}")
    
    def _get_resolution_seconds(self, resolution: str) -> int:
        """Convert resolution to seconds for calculating time windows."""
        resolution_map = {
            "1": 60,
            "5": 300,
            "15": 900,
            "30": 1800,
            "60": 3600,
            "240": 14400,
            "1D": 86400
        }
        return resolution_map.get(resolution, 60)
    
    def create_candle_from_trade(self, trade: Dict) -> StandardizedCandle:
        """
        Create a StandardizedCandle object from a single trade.

        Parameters:
        - trade: A dictionary containing trade data.

        Returns:
        - A StandardizedCandle object.
        """
        # Implement the logic to create a candle from a trade
        # This will typically involve extracting the necessary fields from the trade data
        return StandardizedCandle(
            timestamp=datetime.fromtimestamp(trade['timestamp'], tz=timezone.utc),
            open=trade['price'],
            high=trade['price'],
            low=trade['price'],
            close=trade['price'],
            volume=trade['size'],
            source="drift",
            resolution="1m",  # Default resolution, adjust as needed
            market=trade['market'],
            raw_data=trade
        )

    @staticmethod
    async def self_test():
        """Run self-test to verify handler functionality."""
        from core.config import ExchangeConfig
        
        # Create test config
        config = ExchangeConfig(
            name="drift",
            enabled=True,
            base_url="https://api.drift.trade",
            markets=["SOL-PERP", "BTC-PERP", "ETH-PERP"],
            credentials=None
        )
        
        handler = None
        try:
            handler = DriftHandler(config)
            # Test market validation
            assert await handler.validate_market("SOL-PERP")
            
            # Test market info
            info = await handler.get_exchange_info()
            assert "markets" in info
            assert "timeframes" in info
            assert "exchange" in info
            
            logger.info("Self-test passed successfully")
            
        except Exception as e:
            logger.error(f"Self-test failed: {e}")
            raise
            
        finally:
            if handler:
                await handler.stop()

# Example usage
async def main():
    """Example usage of DriftHandler."""
    import os
    
    # Run the self-test
    print("Running DriftHandler self-test...")
    success = await DriftHandler.self_test()
    print(f"Self-test {'succeeded' if success else 'failed'}")
    
    # Other examples...
    # drift_handler = DriftHandler(None)
    # await drift_handler.connect()
    # etc...

if __name__ == "__main__":
    asyncio.run(main())
