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
import requests
import csv
from io import StringIO
import numpy as np

from src.core.models import StandardizedCandle, TimeRange
from src.exchanges.base import BaseExchangeHandler
from src.core.exceptions import ExchangeError, ValidationError
from src.core.config import ExchangeConfig, ExchangeCredentials
from src.exchanges.auth import DriftAuth
from driftpy.constants.config import configs
from driftpy.drift_client import DriftClient, AccountSubscriptionConfig
from anchorpy import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solana.rpc.api import Client
from src.core.time_utils import (
    convert_timestamp_to_datetime,
    get_timestamp_from_datetime,
    get_current_timestamp
)
from driftpy.drift_user import DriftUser
from driftpy.accounts.bulk_account_loader import BulkAccountLoader
from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Constants
DRIFTPY_COMPATIBLE = sys.version_info >= (3, 10)  # DriftPy requires Python 3.10+
DISABLE_TEST_MODE = os.environ.get('DISABLE_TEST_MODE', '0').lower() in ('1', 'true', 'yes')

# Try to import DriftPy and related packages
if DRIFTPY_COMPATIBLE:
    try:
        # Check if driftpy is installed
        if importlib.util.find_spec("driftpy") is not None:
            DRIFTPY_AVAILABLE = True
            logger.info("DriftPy SDK is available and imported successfully")
        else:
            if DISABLE_TEST_MODE:
                raise ImportError("DriftPy SDK is required when test mode is disabled")
            DRIFTPY_AVAILABLE = False
            logger.warning("DriftPy SDK is not installed")
    except ImportError as e:
        if DISABLE_TEST_MODE:
            raise
        DRIFTPY_AVAILABLE = False
        logger.warning(f"Failed to import DriftPy modules: {e}")
else:
    if DISABLE_TEST_MODE:
        raise RuntimeError(f"Python {sys.version_info.major}.{sys.version_info.minor} is not compatible with DriftPy (requires Python 3.10+)")
    DRIFTPY_AVAILABLE = False
    logger.warning(f"Python {sys.version_info.major}.{sys.version_info.minor} is not compatible with DriftPy (requires Python 3.10+)")

class DriftHandler(BaseExchangeHandler):
    """Handler for Drift exchange data."""

    def __init__(self, config: ExchangeConfig):
        """Initialize Drift handler with configuration."""
        super().__init__(config)
        self.base_url = config.base_url or "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH/"
        self.client = None
        self._drift_user = None
        self._available_markets = []
        self._market_cache = {}
        self._last_market_update = None
        self._market_cache_ttl = timedelta(minutes=15)  # Cache markets for 15 minutes
        self._connection = None
        self._provider = None
        self._retry_config = {
            'max_retries': 3,
            'base_delay': 1,
            'max_delay': 10
        }
        
        # Initialize Drift authentication handler only if credentials provided
        self._auth_handler = DriftAuth(config.credentials) if config.credentials else None

    async def start(self) -> None:
        """Start the handler with improved connection management."""
        await super().start()
        try:
            # Initialize connection with retry logic
            await self._initialize_connection()
            logger.info("Started Drift exchange handler")
        except Exception as e:
            logger.error(f"Failed to start Drift handler: {e}")
            raise

    async def _initialize_connection(self) -> None:
        """Initialize connection with retry logic using simplified configuration."""
        for attempt in range(self._retry_config['max_retries']):
            try:
                # Get RPC endpoint
                rpc_endpoint = os.getenv("MAINNET_RPC_ENDPOINT")
                if not rpc_endpoint:
                    raise ExchangeError("MAINNET_RPC_ENDPOINT environment variable not set")
                
                # Initialize Solana connection
                connection = AsyncClient(rpc_endpoint)
                
                # Load user's keypair
                keypair_path = os.getenv("PRIVATE_KEY_PATH")
                if not keypair_path:
                    # Try alternative key paths
                    keypair_path = os.getenv("MAIN_KEY_PATH") or os.getenv("KP_KEY_PATH") or os.getenv("AG_KEY_PATH")
                    if not keypair_path:
                        raise ExchangeError("No key path environment variable found. Please set PRIVATE_KEY_PATH, MAIN_KEY_PATH, KP_KEY_PATH, or AG_KEY_PATH")
                
                try:
                    with open(keypair_path, 'r') as f:
                        keypair_bytes = bytes(json.load(f))
                    keypair = Keypair.from_bytes(keypair_bytes)
                except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                    raise ExchangeError(f"Failed to load keypair from {keypair_path}: {e}")
                
                # Initialize wallet and provider
                wallet = Wallet(keypair)
                self._provider = Provider(connection, wallet)
                
                # Initialize drift client with simplified configuration
                self.client = DriftClient(
                    self._provider.connection,
                    self._provider.wallet,
                    "mainnet",
                    account_subscription=AccountSubscriptionConfig("cached")
                )
                
                # Subscribe to updates
                await self.client.subscribe()
                
                # Initialize DriftUser with minimal configuration
                self._drift_user = DriftUser(
                    self.client,
                    self._provider.wallet.public_key
                )
                await self._drift_user.subscribe()
                
                logger.info("Successfully initialized Drift connection")
                return
                
            except Exception as e:
                delay = min(self._retry_config['base_delay'] * (2 ** attempt),
                          self._retry_config['max_delay'])
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        raise ExchangeError("Failed to initialize connection after multiple attempts")

    async def get_markets(self) -> List[str]:
        """Get list of available markets with caching and automatic refresh."""
        current_time = datetime.now(timezone.utc)
        
        # Check if cache is valid
        if (self._available_markets and self._last_market_update and 
            current_time - self._last_market_update < self._market_cache_ttl):
            return self._available_markets
            
        try:
            # Ensure connection is initialized
            if not self.client:
                await self._initialize_connection()
                
            # Fetch all perpetual markets
            all_perp_markets = await self.client.program.account["PerpMarket"].all()
            sorted_perp_markets = sorted(
                all_perp_markets,
                key=lambda x: x.account.market_index
            )
            
            # Extract market names and cache them
            self._available_markets = [
                bytes(x.account.name).decode("utf-8").strip()
                for x in sorted_perp_markets
            ]
            
            # Cache market metadata for later use
            for market in sorted_perp_markets:
                market_name = bytes(market.account.name).decode("utf-8").strip()
                self._market_cache[market_name] = {
                    'index': market.account.market_index,
                    'leverage': self._calculate_max_leverage(market.account)
                }
            
            self._last_market_update = current_time
            return self._available_markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            # If cache exists, return cached markets during error
            if self._available_markets:
                logger.warning("Returning cached markets due to fetch error")
                return self._available_markets
            raise ExchangeError(f"Failed to fetch markets: {e}")

    def _calculate_max_leverage(self, market_account) -> float:
        """Calculate maximum leverage for a market."""
        try:
            standard_max_leverage = QUOTE_PRECISION / market_account.margin_ratio_initial
            
            high_leverage = (
                QUOTE_PRECISION / market_account.high_leverage_margin_ratio_initial
                if market_account.high_leverage_margin_ratio_initial > 0
                else 0
            )
            
            return max(standard_max_leverage, high_leverage)
            
        except Exception as e:
            logger.warning(f"Error calculating max leverage: {e}")
            return 0.0

    async def stop(self) -> None:
        """Stop the handler with proper cleanup."""
        try:
            if self._drift_user:
                # Clear DriftUser cache
                self._drift_user = None
                
            if self.client:
                await self.client.unsubscribe()
            
            if self._connection:
                await self._connection.close()
                
            if self._auth_handler:
                await self._auth_handler.close()
                
            self.client = None
            self._connection = None
            self._provider = None
            logger.info("Stopped Drift exchange handler")
            
        except Exception as e:
            logger.error(f"Error during handler cleanup: {e}")
            raise

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
        resolution: str
    ) -> List[StandardizedCandle]:
        """Fetch historical candle data with optimized batch processing."""
        try:
            # Map market to marketKey format
            market_mapping = {
                "SOL-PERP": "perp_0",
                "BTC-PERP": "perp_1", 
                "ETH-PERP": "perp_2"
            }
            market_key = market_mapping.get(market)
            if not market_key:
                raise ExchangeError(f"Unsupported market: {market}")

            # Map resolution to Drift's format
            resolution_mapping = {
                "1": "1",
                "15": "15",
                "60": "60",
                "240": "240",
                "1D": "D",
                "1W": "W"
            }
            candle_resolution = resolution_mapping.get(resolution)
            if not candle_resolution:
                raise ExchangeError(f"Unsupported resolution: {resolution}")

            # Generate all required URLs for the date range
            urls = []
            current_date = time_range.start
            while current_date <= time_range.end:
                base_url = self.base_url.rstrip('/')
                url = f"{base_url}/candle-history/{current_date.year}/{market_key}/{candle_resolution}.csv"
                urls.append((url, current_date))
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            # Batch size for parallel processing
            BATCH_SIZE = 3  # Adjust based on your system's capabilities
            
            async def fetch_batch(batch_urls):
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for url, _ in batch_urls:
                        tasks.append(self._fetch_single_url(session, url, market, resolution, time_range))
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return [r for r in results if isinstance(r, list)]

            # Process URLs in batches
            all_candles = []
            for i in range(0, len(urls), BATCH_SIZE):
                batch = urls[i:i + BATCH_SIZE]
                batch_results = await fetch_batch(batch)
                for candles in batch_results:
                    all_candles.extend(candles)

            if not all_candles:
                raise ExchangeError("No valid candles found in response")
                
            # Sort candles by timestamp
            all_candles.sort(key=lambda x: x.timestamp)
            return all_candles
                    
        except Exception as e:
            raise ExchangeError(f"Failed to fetch historical candles: {e}")

    async def _fetch_single_url(self, session, url, market, resolution, time_range):
        """Helper method to fetch and process data from a single URL."""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    text_data = await response.text()
                    # Use StringIO for efficient memory usage
                    df = pd.read_csv(StringIO(text_data))
                    
                    candles = []
                    # Process in chunks for better memory management
                    for chunk in np.array_split(df, max(1, len(df) // 1000)):
                        for _, row in chunk.iterrows():
                            try:
                                timestamp = datetime.fromtimestamp(int(row["start"]) / 1000, tz=timezone.utc)
                                if time_range.start <= timestamp <= time_range.end:
                                    candle = StandardizedCandle(
                                        timestamp=timestamp,
                                        open=float(row["fillOpen"]),
                                        high=float(row["fillHigh"]),
                                        low=float(row["fillLow"]),
                                        close=float(row["fillClose"]),
                                        volume=float(row["quoteVolume"]),
                                        source="drift",
                                        resolution=resolution,
                                        market=market,
                                        raw_data=row.to_dict()
                                    )
                                    candles.append(candle)
                            except (KeyError, ValueError) as e:
                                logger.warning(f"Error parsing candle data: {e}")
                                continue
                    return candles
                else:
                    logger.warning(f"Failed to fetch data from S3: {response.status} for {url}")
                    return []
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP request failed for {url}: {e}")
            return []

    def _get_resolution_seconds(self, resolution: str) -> int:
        """Convert resolution to seconds for calculating time windows."""
        resolution_map = {
            "1": 60,
            "15": 900,
            "60": 3600,
            "240": 14400,
            "1D": 86400,
            "1W": 604800
        }
        return resolution_map.get(resolution, 60)

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
            historical_trades = await self._drift_user.get_historical_trades(market_symbol, start_date, end_date)
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
            latest_trade = await self._drift_user.get_latest_trade(market_symbol)
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

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str
    ) -> StandardizedCandle:
        """Fetch live candle data."""
        try:
            # For now, we'll return the most recent candle from historical data
            # This is a temporary solution until we implement WebSocket support
            now = datetime.now(timezone.utc)
            time_range = TimeRange(
                start=now - timedelta(minutes=int(resolution)*2),
                end=now
            )
            
            historical_candles = await self.fetch_historical_candles(
                market=market,
                time_range=time_range,
                resolution=resolution
            )
            
            if not historical_candles:
                raise ExchangeError(f"No live candle data available for {market}")
                
            # Return the most recent candle
            return historical_candles[-1]
            
        except Exception as e:
            raise ExchangeError(f"Failed to fetch live candle: {e}")

    async def get_market_leverage(self, market_name: str) -> float:
        """Get current leverage for a market using cached DriftUser."""
        try:
            if not self._drift_user:
                await self._initialize_connection()
            
            market_info = self._market_cache.get(market_name)
            if not market_info:
                raise ExchangeError(f"Market {market_name} not found in cache")
                
            # Use cached DriftUser for efficient leverage calculation
            leverage = await self._drift_user.get_leverage(market_index=market_info['index'])
            return leverage / 10_000  # Convert to human readable format
            
        except Exception as e:
            logger.error(f"Error fetching market leverage: {e}")
            return 0.0

    async def get_market_price(self, market_name: str) -> float:
        """Get current price for a market using public authority."""
        try:
            if not self.client:
                await self._initialize_connection()
                
            market_info = self._market_cache.get(market_name)
            if not market_info:
                raise ExchangeError(f"Market {market_name} not found in cache")
                
            # Get market account using public authority
            market = await get_perp_market_account(
                self.client.program,
                market_info['index']
            )
            
            # Get oracle price
            return market.amm.oracle_price_data.price / QUOTE_PRECISION
            
        except Exception as e:
            logger.error(f"Error fetching market price: {e}")
            raise ExchangeError(f"Failed to fetch market price: {e}")

    async def get_market_info(self, market_name: str) -> Dict[str, Any]:
        """Get comprehensive market information using public authority."""
        try:
            if not self.client:
                await self._initialize_connection()
                
            market_info = self._market_cache.get(market_name)
            if not market_info:
                raise ExchangeError(f"Market {market_name} not found in cache")
                
            # Get market account
            market = await get_perp_market_account(
                self.client.program,
                market_info['index']
            )
            
            # Return comprehensive market data
            return {
                'name': market_name,
                'index': market_info['index'],
                'max_leverage': market_info['leverage'],
                'current_price': market.amm.oracle_price_data.price / QUOTE_PRECISION,
                'base_asset_amount_long': market.amm.base_asset_amount_long,
                'base_asset_amount_short': market.amm.base_asset_amount_short,
                'open_interest': market.amm.base_asset_amount_with_amm,
                'last_update': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error fetching market info: {e}")
            raise ExchangeError(f"Failed to fetch market info: {e}")

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
