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

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

from core.config import ExchangeConfig, ExchangeCredentials
from core.models import TimeRange, StandardizedCandle
from exchanges.base import BaseExchangeHandler
from core.exceptions import ExchangeError, ValidationError
from driftpy.constants.config import configs
from driftpy.drift_client import DriftClient
from anchorpy import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solana.rpc.api import Client

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
    """Handler for the Drift exchange with conditional SDK usage."""

    def __init__(self, config: ExchangeConfig):
        """Initialize the DriftHandler."""
        super().__init__(config)
        self.base_url = config.base_url or "https://data.api.drift.trade"  # Default to mainnet Data API
        self.program_id = config.credentials.additional_params.get("program_id", "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")
        
        # Use Helius RPC endpoint if available, otherwise fallback to default
        self.rpc_url = os.getenv("HELIUS_RPC_ENDPOINT") or config.credentials.additional_params.get("rpc_url", "https://api.mainnet-beta.solana.com")
        
        logger.info(f"Initializing DriftHandler with base_url={self.base_url}, rpc_url={self.rpc_url}, program_id={self.program_id}")
        
        # Initialize connection-related attributes
        self._client = None
        self._connection = None
        self._wallet = None
        
        if DRIFTPY_AVAILABLE:
            logger.info("DriftHandler will use DriftPy SDK")
        else:
            logger.info("DriftHandler will use HTTP API (DriftPy SDK not available)")

    async def start(self):
        """Initialize connections and client."""
        if not self._client:
            self._wallet = Wallet(Keypair())
            self._connection = AsyncClient(self.rpc_url)
            self._client = DriftClient(
                self._connection,
                self._wallet,
                "mainnet"
            )
            try:
                await self._client.add_user(0)
                await self._client.subscribe()
                logger.info("Successfully initialized DriftClient with user subscription")
            except Exception as e:
                logger.warning(f"Failed to add user or subscribe: {e}. Client will be used in read-only mode.")

    async def stop(self):
        """Cleanup connections and client."""
        try:
            if self._client:
                try:
                    await self._client.unsubscribe()
                except Exception as e:
                    logger.warning(f"Error unsubscribing client: {e}")
            
            if self._connection:
                try:
                    await self._connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self._client = None
            self._connection = None
            self._wallet = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def _get_drift_client(self) -> DriftClient:
        """Get the DriftClient instance, initializing if necessary."""
        if not self._client:
            await self.start()
        return self._client

    async def fetch_historical_candles(self, market_symbol: str, time_range: TimeRange, resolution: str) -> List[StandardizedCandle]:
        """
        Fetch historical candlestick data for a market from Drift.
        Uses the SDK to retrieve trade data and formats it into candles.

        Parameters:
        - market_symbol: The market symbol (e.g., "SOL-PERP").
        - time_range: A TimeRange object containing start and end timestamps.
        - resolution: The resolution for the candlestick data (e.g., "1m", "5m", "1h", "1d").

        Returns:
        - A list of StandardizedCandle objects.
        """
        logger.info(f"Fetching historical candles for {market_symbol} from {time_range.start} to {time_range.end} with resolution {resolution}")
        
        try:
            # Fetch historical trades using the SDK
            historical_trades = await self._drift_client.get_historical_trades(market_symbol, time_range.start, time_range.end)
            
            # Convert historical trades to candles
            candles = self.create_candles_from_trades(historical_trades, resolution)
            
            return candles

        except Exception as e:
            logger.error(f"Error fetching historical candles: {e}")
            raise ExchangeError(f"Failed to fetch historical candles: {e}")

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
    
    async def fetch_live_candles(self, market: str, resolution: str) -> StandardizedCandle:
        """
        Fetch live candlestick data for a market from Drift.
        Uses the SDK to retrieve the latest trade data and formats it into a candle.

        Parameters:
        - market: The market symbol (e.g., "SOL-PERP").
        - resolution: The resolution for the candlestick data (e.g., "1m", "5m", "1h", "1d").

        Returns:
        - A StandardizedCandle object representing the latest candle.
        """
        logger.info(f"Fetching live candle for {market} with resolution {resolution}")
        
        try:
            # Validate market
            self.validate_market(market)
            
            # Get Drift client
            client = await self._get_drift_client()
            
            # Get current time
            now = datetime.now(timezone.utc)
            
            # Calculate start time based on resolution
            resolution_map = {
                "1": 60,      # 1 minute
                "5": 300,     # 5 minutes
                "15": 900,    # 15 minutes
                "30": 1800,   # 30 minutes
                "60": 3600,   # 1 hour
                "240": 14400, # 4 hours
                "D": 86400,   # 1 day
            }
            
            if resolution not in resolution_map:
                raise ValidationError(f"Unsupported resolution: {resolution}")
                
            seconds = resolution_map[resolution]
            start_time = now - timedelta(seconds=seconds)
            
            # Fetch trades for the last period
            trades = await client.get_historical_trades(market, start_time, now)
            
            if not trades:
                # If no trades in the period, return empty candle
                return StandardizedCandle.create_empty(market=market, source="drift", resolution=resolution)
            
            # Create candle from trades
            open_price = trades[0]['price']
            high_price = max(trade['price'] for trade in trades)
            low_price = min(trade['price'] for trade in trades)
            close_price = trades[-1]['price']
            volume = sum(trade['size'] for trade in trades)
            
            return StandardizedCandle(
                timestamp=start_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                source="drift",
                resolution=resolution,
                market=market,
                raw_data=trades
            )

        except Exception as e:
            logger.error(f"Error fetching live candle: {e}")
            raise ExchangeError(f"Failed to fetch live candle: {e}")
    
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
            market_info = await self._get_market_index(market)
            
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
    
    async def _get_market_index(self, market: str) -> Dict[str, Any]:
        """Get market index for a given market symbol."""
        if market in self._market_cache:
            return self._market_cache[market]
            
        client = await self._get_drift_client()
        
        # Parse market symbol (e.g., "BTC-PERP" or "SOL-USDC")
        parts = market.split('-')
        base = parts[0]
        is_perp = len(parts) > 1 and parts[1] == "PERP"
        
        if is_perp:
            # Get all perp markets
            perp_markets = await client.get_perp_market_accounts()
            for idx, perp_market in enumerate(perp_markets):
                market_name = perp_market.name.decode('utf-8').strip('\x00')
                if base in market_name:
                    self._market_cache[market] = {"type": "perp", "index": idx}
                    return self._market_cache[market]
        else:
            # Get all spot markets
            spot_markets = await client.get_spot_market_accounts()
            for idx, spot_market in enumerate(spot_markets):
                market_name = spot_market.name.decode('utf-8').strip('\x00')
                if base in market_name:
                    self._market_cache[market] = {"type": "spot", "index": idx}
                    return self._market_cache[market]
                    
        raise ExchangeError(f"Market {market} not found on Drift")
    
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
    
    async def get_markets(self) -> List[str]:
        """
        Get a list of available markets.
        Attempts to use the SDK first, falls back to HTTP API if needed.

        Returns:
        - A list of market symbols.
        """
        try:
            if DRIFTPY_AVAILABLE:
                markets = await self._get_markets_sdk()
            else:
                markets = await self._get_markets_http()

            # Store available markets for validation
            self._available_markets = [market.upper() for market in markets]
            logger.info(f"Successfully fetched and stored {len(self._available_markets)} markets")
            
            return self._available_markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            raise ExchangeError(f"Failed to fetch markets: {e}")

    async def _get_markets_sdk(self) -> List[str]:
        """Fetch available markets using DriftPy SDK."""
        try:
            client = await self._get_drift_client()
            markets = []

            try:
                # Try multiple approaches to fetch market data
                # Approach 1: Use program.account method
                try:
                    # Get perp markets using program accounts
                    perp_markets = await client.program.account["PerpMarket"].all()
                    for market in perp_markets:
                        if hasattr(market.account, 'name'):
                            name = bytes(market.account.name).decode('utf-8').strip('\x00')
                            if name:
                                markets.append(f"{name}-PERP")
                                
                    # Get spot markets using program accounts
                    spot_markets = await client.program.account["SpotMarket"].all()
                    for market in spot_markets:
                        if hasattr(market.account, 'name'):
                            name = bytes(market.account.name).decode('utf-8').strip('\x00')
                            if name and name != "USDC":  # Skip USDC market
                                markets.append(f"{name}-SPOT")
                except Exception as e:
                    logger.warning(f"Market fetching with program.account failed: {e}")
                
                # Ensure we have some standard markets even if fetching fails
                if not markets:
                    logger.warning("Using hardcoded market list as fallback")
                    markets = ["SOL-PERP", "BTC-PERP", "ETH-PERP", "SOL-SPOT", "BTC-SPOT", "ETH-SPOT"]
                
                return markets

            except Exception as e:
                logging.warning(f"Error fetching market states: {str(e)}")
                raise

        except Exception as e:
            logging.warning(f"SDK market fetch failed: {str(e)}, falling back to HTTP API")
            return await self._get_markets_http()

    async def _get_markets_http(self) -> List[str]:
        """Fetch available markets using HTTP API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Try v2 endpoint first
                url = f"{self.base_url}/v2/markets"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [market["symbol"] for market in data["data"]]
                    
                    # If v2 fails, try v1
                    url = f"{self.base_url}/markets"
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise ExchangeError(f"drift API error: {response.status}")
                        data = await response.json()
                        return [market["symbol"] for market in data["data"]]
                        
        except Exception as e:
            raise ExchangeError(f"Unexpected error in drift: {str(e)}")

    async def get_exchange_info(self) -> Dict:
        """Get exchange information."""
        try:
            return {
                "name": self.name,
                "markets": await self.get_markets(),
                "timeframes": ["1", "5", "15", "60", "240", "1D"],
                "has_live_data": True,
                "rate_limit": self.rate_limit,
                "sdk_version": "driftpy" if DRIFTPY_COMPATIBLE else "http_fallback"
            }
        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            raise ExchangeError(f"Failed to fetch exchange info: {e}")

    async def connect(self):
        await self._get_drift_client()

    async def open_position(self, market_symbol, amount):
        # Open a position using the SDK
        market_index = await self._drift_client.get_market_index(market_symbol)
        sig = await self._drift_client.open_position(
            PositionDirection.LONG(),  # or PositionDirection.SHORT()
            int(amount * BASE_PRECISION),  # amount in base precision
            market_index
        )
        return sig

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

    def validate_market(self, market_symbol: str) -> bool:
        """
        Validate if a market symbol is supported.

        Parameters:
        - market_symbol: The market symbol to validate (e.g., "SOL-PERP").

        Returns:
        - True if the market is supported, False otherwise.
        """
        try:
            # Normalize market symbol
            market_symbol = market_symbol.upper()
            
            # Check if market is in the configured markets list
            if market_symbol in self.config.markets:
                logger.debug(f"Market {market_symbol} found in configured markets")
                return True
                
            # Check if market is in the available markets list
            if hasattr(self, '_available_markets'):
                if market_symbol in self._available_markets:
                    logger.debug(f"Market {market_symbol} found in available markets")
                    return True
                    
            logger.warning(f"Market {market_symbol} not found in configured or available markets")
            return False
            
        except Exception as e:
            logger.error(f"Error validating market {market_symbol}: {e}")
            return False

    @staticmethod
    async def self_test():
        """A standalone method to test DriftHandler functionality."""
        from core.config import ExchangeConfig, ExchangeCredentials
        
        # Create a basic configuration for Drift
        config = ExchangeConfig(
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
        
        # Create handler and test
        handler = None
        try:
            handler = DriftHandler(config)
            # Manually set available markets for testing
            handler._available_markets = ["SOL-PERP", "BTC-PERP", "ETH-PERP"]
            
            # Test market validation
            assert handler.validate_market("SOL-PERP"), "SOL-PERP market not found"
            print("✅ Market validation passed")
            
            # Try to start the handler
            await handler.start()
            print("✅ Handler started successfully")
            
            try:
                # Try to get markets
                markets = await handler.get_markets()
                if markets and len(markets) > 0:
                    print(f"✅ Got {len(markets)} markets: {markets[:5]}...")
                else:
                    print("⚠️ No markets returned")
            except Exception as e:
                print(f"⚠️ Error getting markets: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Self-test failed: {e}")
            return False
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
