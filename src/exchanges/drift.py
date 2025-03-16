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
from src.exchanges.auth import DriftAuth
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
    """Handler for Drift exchange data."""

    def __init__(self, config: ExchangeConfig):
        """Initialize Drift handler with configuration."""
        super().__init__(config)
        self.base_url = config.base_url or "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
        self.client = None
        self.drift_client = None
        self._is_test_mode = False
        self._mock_markets = ["SOL", "BTC", "ETH", "SOL-PERP", "BTC-PERP", "ETH-PERP"]
        self._available_markets = []
        
        # Initialize Drift authentication handler
        self._auth_handler = DriftAuth(config.credentials)
        
        # Initialize with test mode if SDK is not available
        if not self._check_sdk_available():
            self._is_test_mode = True
            self._setup_test_mode()

    def _check_sdk_available(self) -> bool:
        """Check if DriftPy SDK is available."""
        try:
            if importlib.util.find_spec("driftpy") is not None:
                logger.info("DriftPy SDK is available and imported successfully")
                return True
            else:
                logger.warning("DriftPy SDK is not available")
                return False
        except Exception as e:
            logger.warning(f"Error checking DriftPy SDK: {e}")
            return False

    def _setup_test_mode(self):
        """Set up test mode with mock data."""
        self._is_test_mode = True
        self._available_markets = self._mock_markets
        logger.info(f"Initialized test mode with {len(self._mock_markets)} mock markets")

    async def _initialize_drift_client(self) -> None:
        """Initialize the Drift client using the authentication handler."""
        if self._is_test_mode:
            logger.info("Running in test mode, skipping Drift client initialization")
            return
            
        try:
            # Check if we have valid authentication
            if self._auth_handler.is_authenticated():
                # Initialize the client using the auth handler
                self.client = await self._auth_handler.initialize_client()
                logger.info("Successfully initialized Drift client with authenticated wallet")
            else:
                # Create a mock wallet for public endpoints
                mock_wallet = Keypair()
                
                # Get program ID and RPC URL from auth handler
                program_id = self._auth_handler.get_program_id()
                rpc_url = self._auth_handler.get_rpc_url()
                
                # Initialize the Drift client with mock wallet for public endpoints
                self.client = DriftClient(
                    connection=AsyncClient(rpc_url),
                    wallet=mock_wallet,
                    program_id=program_id,
                    opts={"commitment": "processed"}
                )
                logger.info("Successfully initialized Drift client with mock wallet for public endpoints")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Drift client: {e}. Falling back to test mode.")
            self._is_test_mode = True
            self._setup_test_mode()

    async def start(self) -> None:
        """Start the handler."""
        await super().start()
        try:
            if not self._is_test_mode:
                await self._initialize_drift_client()
        except Exception as e:
            logger.error(f"Error starting Drift handler: {e}")
            self._is_test_mode = True
            self._setup_test_mode()

    async def stop(self) -> None:
        """Stop the handler."""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning(f"Error closing Drift client: {e}")
                
        # Close the auth handler connection
        if hasattr(self, '_auth_handler') and self._auth_handler:
            await self._auth_handler.close()

    async def get_markets(self) -> List[str]:
        """Get list of available markets."""
        if self._is_test_mode:
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
        """Fetch historical candle data."""
        # If in test mode, return mock data
        if self._is_test_mode:
            return self._generate_mock_candles(time_range, resolution, market)
            
        try:
            # Try to use the client if available
            if self.client:
                # Fetch candles using the SDK client
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
            else:
                # Use direct HTTP request to public S3 bucket for historical data
                # Format the URL based on the market and time range
                formatted_market = market.replace("-", "").lower()
                start_date = time_range.start.strftime("%Y-%m-%d")
                end_date = time_range.end.strftime("%Y-%m-%d")
                
                # Create a session for HTTP requests
                async with aiohttp.ClientSession() as session:
                    # Construct URL for the S3 bucket
                    url = f"{self.base_url}/{formatted_market}/{resolution}/{start_date}_to_{end_date}.json"
                    
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Parse the data into StandardizedCandle objects
                                candles = []
                                for item in data:
                                    try:
                                        timestamp = datetime.fromtimestamp(item["time"] / 1000, tz=timezone.utc)
                                        candle = StandardizedCandle(
                                            timestamp=timestamp,
                                            open=float(item["open"]),
                                            high=float(item["high"]),
                                            low=float(item["low"]),
                                            close=float(item["close"]),
                                            volume=float(item["volume"]),
                                            source="drift",
                                            resolution=resolution,
                                            market=market,
                                            raw_data=item
                                        )
                                        candles.append(candle)
                                    except (KeyError, ValueError) as e:
                                        logger.warning(f"Error parsing candle data: {e}")
                                        continue
                                
                                return candles
                            else:
                                # If we can't access the data, fall back to mock data
                                logger.warning(f"Failed to fetch data from S3: {response.status}. Falling back to mock data.")
                                return self._generate_mock_candles(time_range, resolution, market)
                    except Exception as e:
                        logger.warning(f"Error fetching data from S3: {e}. Falling back to mock data.")
                        return self._generate_mock_candles(time_range, resolution, market)
                
        except Exception as e:
            logger.error(f"Error fetching historical candles: {e}")
            raise ExchangeError(f"Failed to fetch historical candles: {e}")

    def _generate_mock_candles(
        self,
        time_range: TimeRange,
        resolution: str,
        market: str
    ) -> List[StandardizedCandle]:
        """Generate mock candles for testing."""
        candles = []
        current_time = time_range.start
        
        # Get interval in seconds
        interval_seconds = self._get_resolution_seconds(resolution)
        
        while current_time <= time_range.end:
            # Generate a mock candle with random price movements
            base_price = 100.0 if "BTC" in market else 50.0 if "ETH" in market else 20.0
            price_volatility = 0.05  # 5% volatility
            
            # Random price movement
            open_price = base_price * (1 + random.uniform(-price_volatility, price_volatility))
            close_price = open_price * (1 + random.uniform(-price_volatility, price_volatility))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, price_volatility))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, price_volatility))
            volume = random.uniform(500, 2000)
            
            candle = StandardizedCandle(
                timestamp=current_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                source='drift',
                resolution=resolution,
                market=market,
                raw_data={
                    'mock': True,
                    'interval': resolution
                }
            )
            candles.append(candle)
            
            # Increment time based on resolution
            current_time = datetime.fromtimestamp(current_time.timestamp() + interval_seconds, tz=timezone.utc)
        
        return candles

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str = "1"
    ) -> StandardizedCandle:
        """Fetch live candle data."""
        # If in test mode, return a mock candle
        if self._is_test_mode:
            return self._generate_mock_live_candle(market, resolution)
            
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

    def _generate_mock_live_candle(self, market: str, resolution: str) -> StandardizedCandle:
        """Generate a mock live candle for testing."""
        # Base price depends on the market
        base_price = 100.0 if "BTC" in market else 50.0 if "ETH" in market else 20.0
        price_volatility = 0.02  # 2% volatility
        
        # Random price movement
        open_price = base_price * (1 + random.uniform(-price_volatility, price_volatility))
        close_price = open_price * (1 + random.uniform(-price_volatility, price_volatility))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, price_volatility))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, price_volatility))
        volume = random.uniform(100, 500)
        
        return StandardizedCandle(
            timestamp=datetime.now(timezone.utc),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            source='drift',
            resolution=resolution,
            market=market,
            raw_data={
                'mock': True,
                'interval': resolution
            }
        )

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
        
    async def _get_authenticated_client(self) -> DriftClient:
        """Get an authenticated Drift client for operations requiring authentication."""
        if not self._auth_handler.is_authenticated():
            raise ExchangeError("Authentication required for this operation")
            
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

    async def is_ready(self) -> bool:
        """Check if the handler is ready to use."""
        if self._is_test_mode:
            return True
        
        # If not in test mode, check if client is initialized
        if self.client:
            return True
            
        # Try to initialize client if not already done
        try:
            await self._initialize_drift_client()
            return self.client is not None
        except Exception as e:
            logger.warning(f"Failed to initialize Drift client during ready check: {e}")
            return False

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
