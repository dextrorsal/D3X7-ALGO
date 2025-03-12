"""
Binance exchange handler implementation using the official binance-connector SDK.
"""

import logging
from typing import List, Dict, Optional, Tuple, Union, Any, Callable
from datetime import datetime, timezone, timedelta
import asyncio
from binance.spot import Spot
from binance.error import ClientError
import random
import json
import time

import aiohttp
import pandas as pd
from binance.client import Client

from src.core.models import StandardizedCandle, TimeRange
from src.exchanges.base import BaseExchangeHandler
from core.exceptions import ExchangeError, ValidationError, RateLimitError
from core.symbol_mapper import SymbolMapper
from src.utils.time_utils import (
    convert_timestamp_to_datetime,
    get_current_timestamp,
    get_timestamp_from_datetime,
)

logger = logging.getLogger(__name__)

# Binance error codes that should trigger a retry
RETRY_ERROR_CODES = {
    -1003,  # Too many requests; current limit is exceeded
    -1006,  # An unexpected response was received from the message bus
    -1007,  # Timeout waiting for response from backend server
    -1015,  # Too many new orders
    -1021,  # Timestamp for this request was 1000ms ahead of the server's time
    -1022   # Signature for this request is not valid
}

class BinanceHandler(BaseExchangeHandler):
    """Handler for Binance exchange data using official SDK."""

    def __init__(self, config):
        """Initialize Binance handler with configuration."""
        super().__init__(config)
        self.client = None
        self.symbol_mapper = SymbolMapper()
        # Define both formats for test mode
        self.mock_markets = {
            "spot": {
                "binance_format": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "standard_format": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
            },
            "perp": {
                "binance_format": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "standard_format": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
            }
        }
        self.timeframe_map = {
            "1": "1m",
            "3": "3m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "120": "2h",
            "240": "4h",
            "360": "6h",
            "480": "8h",
            "720": "12h",
            "1D": "1d",
            "3D": "3d",
            "1W": "1w",
            "1M": "1M"
        }
        # Base URLs for different purposes
        self._base_urls = [
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://api4.binance.com"
        ]
        self._data_base_url = "https://data-api.binance.vision"  # For market data only
        self._current_url_index = 0
        self._weight_used = 0
        self._weight_limit = 1200  # Default weight limit per minute
        self._last_weight_reset = datetime.now().timestamp()
        self._exchange_info = None  # Cache exchange info
        self._market_filters = {}  # Cache market-specific filters
        self._available_markets = []
        self._is_test_mode = False

    async def start(self):
        """Start the Binance handler and initialize the client."""
        try:
            if not self.client:
                await self._initialize_client()
                
            # Try to get exchange info
            try:
                exchange_info = await self.get_exchange_info()
                self._exchange_info = exchange_info
                
                # Process and cache market filters
                for symbol in exchange_info['symbols']:
                    if symbol['status'] == 'TRADING':
                        permissions = symbol.get('permissions', [])
                        if isinstance(permissions, str):
                            permissions = [permissions]
                        
                        self._market_filters[symbol['symbol']] = {
                            'filters': symbol['filters'],
                            'baseAsset': symbol['baseAsset'],
                            'quoteAsset': symbol['quoteAsset'],
                            'permissions': permissions,
                            'symbol': symbol['symbol']
                        }
                        
                        standard_symbol = f"{symbol['baseAsset']}-{symbol['quoteAsset']}"
                        self._market_filters[standard_symbol] = self._market_filters[symbol['symbol']]
                
                # Register all trading markets with symbol mapper
                symbols = []
                binance_symbols = []
                for symbol in exchange_info['symbols']:
                    if symbol['status'] == 'TRADING':
                        standard_symbol = f"{symbol['baseAsset']}-{symbol['quoteAsset']}"
                        symbols.append(standard_symbol)
                        binance_symbols.append(symbol['symbol'])
                        
                        # Register symbol with the mapper
                        self.symbol_mapper.register_symbol(
                            exchange="binance",
                            symbol=symbol['symbol'],
                            base_asset=symbol['baseAsset'],
                            quote_asset=symbol['quoteAsset'],
                            is_perpetual=False
                        )
                        
                        # Also register standard format
                        self.symbol_mapper.register_symbol(
                            exchange="binance",
                            symbol=standard_symbol,
                            base_asset=symbol['baseAsset'],
                            quote_asset=symbol['quoteAsset'],
                            is_perpetual=False
                        )
                
                logger.info(f"Initialized {len(symbols)} trading markets for Binance")
                
            except Exception as e:
                logger.warning(f"Failed to get exchange info: {e}. Falling back to test mode.")
                self._is_test_mode = True
                self._setup_test_mode()
                
        except Exception as e:
            logger.warning(f"Failed to initialize Binance client: {e}. Falling back to test mode.")
            self._is_test_mode = True
            self._setup_test_mode()
            
        logger.info("Started Binance exchange handler")

    def _setup_test_mode(self):
        """Setup test mode with mock data."""
        self._is_test_mode = True
        
        # Register all market formats
        for market_type in ["spot"]:  # Only spot markets for Binance
            for binance_format, standard_format in zip(
                self.mock_markets[market_type]["binance_format"],
                self.mock_markets[market_type]["standard_format"]
            ):
                base_asset = binance_format.replace("USDT", "")
                
                # Register both formats with the symbol mapper
                self.symbol_mapper.register_symbol(
                    exchange="binance",
                    symbol=binance_format,
                    base_asset=base_asset,
                    quote_asset="USDT",
                    is_perpetual=False
                )
                self.symbol_mapper.register_symbol(
                    exchange="binance",
                    symbol=standard_format,
                    base_asset=base_asset,
                    quote_asset="USDT",
                    is_perpetual=False
                )
                
                # Add Binance format to available markets
                if binance_format not in self._available_markets:
                    self._available_markets.append(binance_format)
        
        logger.info(f"Initialized test mode with {len(self._available_markets)} mock markets")

    async def _initialize_client(self, retry_count: int = 0) -> None:
        """Initialize the Binance client with retry logic."""
        if retry_count >= 5:  # Max 5 retries
            raise ExchangeError("Failed to initialize Binance client after 5 attempts")
            
        try:
            # Initialize the client with the current base URL
            self.client = Spot(
                api_key=self.config.credentials.api_key if self.config.credentials else None,
                api_secret=self.config.credentials.api_secret if self.config.credentials else None,
                base_url=self.base_url
            )
            
            # Test connection with a simple ping
            response = await self._make_request("GET", "/api/v3/ping")
            logger.info("Successfully connected to Binance API")
            
        except Exception as e:
            # If we fail to connect, try the next URL
            if retry_count < len(self._base_urls) - 1:
                next_url = self._base_urls[retry_count + 1]
                logger.warning(f"Failed to connect to {self.base_url}, trying {next_url}")
                self.base_url = next_url
                await self._initialize_client(retry_count + 1)
            else:
                raise ExchangeError(f"Failed to connect to any Binance API endpoints: {str(e)}")

    def _get_market_filters(self, market: str) -> Dict:
        """
        Get market-specific filters and trading rules.
        
        Args:
            market (str): Market symbol in Binance format
            
        Returns:
            Dict: Market filters and trading rules
        """
        try:
            # Check cache first
            if market in self._market_filters:
                return self._market_filters[market]
            
            # If in test mode, return mock filters
            if self._is_test_mode:
                mock_filters = {
                    'symbol': market,
                    'status': 'TRADING',
                    'baseAsset': market[:-4],  # Remove USDT
                    'quoteAsset': 'USDT',
                    'permissions': ['SPOT', 'MARGIN'],
                    'filters': [
                        {
                            'filterType': 'PRICE_FILTER',
                            'minPrice': '0.00000100',
                            'maxPrice': '100000.00000000',
                            'tickSize': '0.00000100'
                        },
                        {
                            'filterType': 'LOT_SIZE',
                            'minQty': '0.00100000',
                            'maxQty': '100000.00000000',
                            'stepSize': '0.00100000'
                        }
                    ]
                }
                self._market_filters[market] = mock_filters
                return mock_filters
            
            # Get exchange info if not cached
            if not self._exchange_info:
                raise ExchangeError("Exchange info not initialized")
            
            # Find market in exchange info
            for symbol in self._exchange_info['symbols']:
                if symbol['symbol'] == market:
                    self._market_filters[market] = symbol
                    return symbol
            
            raise ValidationError(f"No filters found for market {market}")
            
        except Exception as e:
            raise ValidationError(f"Error getting filters for market {market}: {str(e)}")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ultimate-data-fetcher/1.0'
        }
        
        if self.config.credentials:
            headers.update({
                'X-MBX-APIKEY': self.config.credentials.api_key
            })
            
        return headers

    async def _handle_weight_limit(self, response: Union[aiohttp.ClientResponse, Dict[str, Any]]) -> None:
        """
        Handle rate limiting based on Binance API response headers.
        
        Args:
            response: The response object containing rate limit headers
        """
        try:
            # If response is a dict (from error response), check for retry-after
            if isinstance(response, dict):
                retry_after = response.get('retry-after')
                if retry_after:
                    sleep_time = int(retry_after)
                    logger.warning(f"Rate limit hit. Sleeping for {sleep_time}s")
                    await asyncio.sleep(sleep_time)
                return
                
            # Get rate limit headers
            used_weight = int(response.headers.get('x-mbx-used-weight-1m', '0'))
            weight_limit = int(response.headers.get('x-mbx-weight-limit-1m', '1200'))
            
            # Calculate remaining weight
            remaining_weight = weight_limit - used_weight
            
            # If we're close to the limit (less than 10% remaining), sleep
            if remaining_weight < (weight_limit * 0.1):
                sleep_time = 60  # Sleep for 1 minute to allow weight to reset
                logger.warning(f"Rate limit approaching ({remaining_weight}/{weight_limit}). Sleeping for {sleep_time}s")
                await asyncio.sleep(sleep_time)
                
            # Always check for 429 status
            if response.status == 429:
                retry_after = int(response.headers.get('Retry-After', '60'))
                logger.warning(f"Rate limit exceeded. Sleeping for {retry_after}s")
                await asyncio.sleep(retry_after)
                
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning(f"Error handling rate limit: {e}")

    async def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Any:
        """
        Make a request to the Binance API with rate limiting.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            ExchangeError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        for attempt in range(3):  # Max 3 retries
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, params=params, headers=headers) as response:
                        # Handle rate limiting
                        await self._handle_weight_limit(response)
                        
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # Rate limit hit - already handled in _handle_weight_limit
                            continue
                        else:
                            error_data = await response.text()
                            raise ExchangeError(f"Request failed: {response.status} - {error_data}")
                            
            except aiohttp.ClientError as e:
                if attempt == 2:  # Last attempt
                    raise ExchangeError(f"Request failed after 3 attempts: {e}")
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)  # Wait before retry
                
        raise ExchangeError("Request failed after all retries")

    async def _make_request_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Make a request with retry logic.
        
        Args:
            func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Response from the function
            
        Raises:
            ExchangeError: If all retries fail
        """
        for attempt in range(3):  # Max 3 retries
            try:
                # Handle both async and regular functions
                if func is None:
                    raise ExchangeError("No function provided")
                    
                if isinstance(func, dict):
                    # If we're passed a mock response for testing
                    await self._handle_weight_limit({
                        'x-mbx-used-weight-1m': '1',
                        'x-mbx-weight-limit-1m': '1200'
                    })
                    return func
                    
                # Call the function and get the result
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # If it's a bound method that's not a coroutine
                    method = getattr(func, '__func__', None)
                    if method and asyncio.iscoroutinefunction(method):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                
                # Handle rate limiting with a mock response
                await self._handle_weight_limit({
                    'x-mbx-used-weight-1m': '1',
                    'x-mbx-weight-limit-1m': '1200'
                })
                
                return result
                
            except Exception as e:
                if attempt == 2:  # Last attempt
                    raise ExchangeError(f"Request failed after 3 attempts: {e}")
                    
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)  # Wait before retry
                
        raise ExchangeError("Request failed after all retries")

    def _parse_raw_candle(self, raw_data: List, market: str, resolution: str) -> StandardizedCandle:
        """Parse raw candle data into StandardizedCandle format."""
        try:
            # Binance kline format:
            # [
            #   0  Open time
            #   1  Open
            #   2  High
            #   3  Low
            #   4  Close
            #   5  Volume
            #   6  Close time
            #   7  Quote asset volume
            #   8  Number of trades
            #   9  Taker buy base asset volume
            #   10 Taker buy quote asset volume
            #   11 Ignore
            # ]
            candle = StandardizedCandle(
                timestamp=self.standardize_timestamp(raw_data[0]),
                open=float(raw_data[1]),
                high=float(raw_data[2]),
                low=float(raw_data[3]),
                close=float(raw_data[4]),
                volume=float(raw_data[5]),
                source='binance',
                resolution=resolution,
                market=market,
                raw_data=raw_data
            )
            self.validate_candle(candle)
            return candle
        except (IndexError, ValueError) as e:
            raise ValidationError(f"Error parsing Binance candle data: {str(e)}")

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange = None,
        resolution: str = "1",
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict]:
        """
        Fetch historical candles for a market.
        
        Args:
            market (str): Market symbol (e.g., 'BTC-USDT')
            time_range (TimeRange, optional): Time range to fetch data for
            resolution (str): Candle resolution (default: "1")
            start_time (datetime, optional): Start time (if time_range not provided)
            end_time (datetime, optional): End time (if time_range not provided)
            
        Returns:
            List[Dict]: List of candles with OHLCV data
        """
        try:
            if not self.validate_market(market):
                raise ValidationError(f"Invalid market {market}")
            
            # Convert market symbol
            binance_symbol = self._convert_market_symbol(market)
            
            # Handle time range
            if time_range:
                start_time = time_range.start
                end_time = time_range.end
            elif not (start_time and end_time):
                raise ValidationError("Must provide either time_range or both start_time and end_time")
            
            # Get candle data
            interval = self.timeframe_map.get(resolution, "1m")
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            if self._is_test_mode:
                return self._generate_mock_candles(start_ts, end_ts, interval)
            
            # Make API request
            response = await self._make_request_with_retry(
                self.client.get_klines,
                symbol=binance_symbol,
                interval=interval,
                startTime=start_ts,
                endTime=end_ts,
                limit=1000
            )
            
            # Parse response
            candles = []
            for candle in response:
                candles.append(self._parse_raw_candle(candle, market, resolution))
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching historical candles for {market}: {str(e)}")
            raise ExchangeError(f"Failed to fetch historical candles: {str(e)}")

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str = "1"
    ) -> StandardizedCandle:
        """
        Fetch latest candle for a market.
        
        Args:
            market (str): Market symbol (e.g., 'BTC-USDT')
            resolution (str): Candle resolution (default: "1")
            
        Returns:
            StandardizedCandle: Latest candle data
        """
        try:
            if not self.validate_market(market):  # Now sync call
                raise ValidationError(f"Invalid market {market}")
            
            # Convert market symbol
            binance_symbol = self._convert_market_symbol(market)
            
            if self._is_test_mode:
                return self._generate_mock_candle()
            
            # Get latest candle
            interval = self.timeframe_map.get(resolution, "1m")
            response = await self._make_request_with_retry(
                self.client.get_klines,
                symbol=binance_symbol,
                interval=interval,
                limit=1
            )
            
            if not response:
                raise ExchangeError(f"No data returned for {market}")
            
            # Parse response
            return self._parse_raw_candle(response[0], market, resolution)
            
        except Exception as e:
            logger.error(f"Error fetching live candle for {market}: {str(e)}")
            raise ExchangeError(f"Failed to fetch live candle: {str(e)}")

    def _generate_mock_candle(self) -> Dict:
        """Generate a mock candle for testing."""
        now = datetime.now(timezone.utc)
        return {
            'timestamp': int(now.timestamp() * 1000),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.0
        }

    def _generate_mock_candles(
        self,
        start_ts: int,
        end_ts: int,
        interval: str
    ) -> List[Dict]:
        """Generate mock candles for testing."""
        candles = []
        current_ts = start_ts
        
        # Get interval in minutes
        if interval.endswith('m'):
            minutes = int(interval[:-1])
        elif interval.endswith('h'):
            minutes = int(interval[:-1]) * 60
        elif interval.endswith('d'):
            minutes = int(interval[:-1]) * 1440
        else:
            minutes = 1
            
        interval_ms = minutes * 60 * 1000
        
        while current_ts <= end_ts:
            candles.append({
                'timestamp': current_ts,
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 100.0
            })
            current_ts += interval_ms
            
        return candles

    async def get_markets(self) -> List[str]:
        """
        Get list of available markets.
        
        Returns:
            List[str]: List of market symbols in Binance format
        """
        try:
            if self._is_test_mode:
                return self._available_markets
                
            if not self._available_markets:
                # Fetch exchange info
                exchange_info = await self._make_request_with_retry(
                    self.client.exchange_info
                )
                
                # Process symbols
                for symbol_info in exchange_info["symbols"]:
                    if (
                        symbol_info["status"] == "TRADING" and
                        symbol_info["quoteAsset"] == "USDT"
                    ):
                        symbol = symbol_info["symbol"]
                        base_asset = symbol_info["baseAsset"]
                        
                        # Register both formats
                        self.symbol_mapper.register_symbol(
                            exchange="binance",
                            symbol=symbol,
                            base_asset=base_asset,
                            quote_asset="USDT",
                            is_perpetual=False
                        )
                        
                        standard_format = f"{base_asset}-USDT"
                        self.symbol_mapper.register_symbol(
                            exchange="binance",
                            symbol=standard_format,
                            base_asset=base_asset,
                            quote_asset="USDT",
                            is_perpetual=False
                        )
                        
                        self._available_markets.append(symbol)
                        
            return self._available_markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {str(e)}")
            raise ExchangeError(f"Failed to fetch markets: {str(e)}")

    async def get_exchange_info(self) -> Dict:
        """
        Get detailed exchange information including trading rules and filters.
        
        Returns:
            Dict containing exchange information with the following key data:
            - timezone: Exchange timezone
            - serverTime: Current server time
            - symbols: List of trading symbols with their rules:
                - symbol: Trading pair name
                - status: Trading status (e.g., TRADING)
                - baseAsset: Base currency
                - quoteAsset: Quote currency
                - permissions: List of allowed operations (e.g., SPOT, MARGIN)
                - filters: List of filters with trading rules
        """
        try:
            if self._is_test_mode:
                # Return mock exchange info with USDT pairs
                mock_info = {
                    'timezone': 'UTC',
                    'serverTime': int(datetime.now(timezone.utc).timestamp() * 1000),
                    'symbols': []
                }
                
                for market in self.mock_markets['spot']['standard_format']:
                    mock_info['symbols'].append({
                        'symbol': market,
                        'status': 'TRADING',
                        'baseAsset': market[:-4],  # Remove USDT
                        'quoteAsset': 'USDT',
                        'permissions': ['SPOT', 'MARGIN'],
                        'filters': [
                            {
                                'filterType': 'PRICE_FILTER',
                                'minPrice': '0.00000100',
                                'maxPrice': '100000.00000000',
                                'tickSize': '0.00000100'
                            },
                            {
                                'filterType': 'LOT_SIZE',
                                'minQty': '0.00100000',
                                'maxQty': '100000.00000000',
                                'stepSize': '0.00100000'
                            }
                        ]
                    })
                return mock_info
            
            # Use the client for market data
            response = await self._make_request_with_retry(
                self.client.exchange_info if hasattr(self, 'client') else None
            )
            
            # Cache the response
            self._exchange_info = response
            
            # Register all symbols with the mapper
            for symbol in response['symbols']:
                if symbol['status'] == 'TRADING':
                    standard_symbol = f"{symbol['baseAsset']}-{symbol['quoteAsset']}"
                    
                    # Register both formats
                    self.symbol_mapper.register_symbol(
                        exchange="binance",
                        symbol=symbol['symbol'],
                        base_asset=symbol['baseAsset'],
                        quote_asset=symbol['quoteAsset'],
                        is_perpetual=False
                    )
                    
                    self.symbol_mapper.register_symbol(
                        exchange="binance",
                        symbol=standard_symbol,
                        base_asset=symbol['baseAsset'],
                        quote_asset=symbol['quoteAsset'],
                        is_perpetual=False
                    )
            
            return response
            
        except Exception as e:
            raise ExchangeError(f"Failed to get exchange info: {str(e)}")

    def validate_market(self, market: str) -> bool:
        """
        Validate if a market is supported.
        
        Args:
            market (str): Market symbol (e.g., 'BTC-USDT' or 'BTCUSDT')
            
        Returns:
            bool: True if market is valid
        """
        try:
            if not market or not isinstance(market, str):
                return False
                
            if self._is_test_mode:
                # In test mode, accept both formats directly
                for market_type in ["spot"]:
                    if market in self.mock_markets[market_type]["binance_format"] or \
                       market in self.mock_markets[market_type]["standard_format"]:
                        return True
                        
                # Also try converting the market symbol
                try:
                    binance_symbol = self._convert_market_symbol(market)
                    for market_type in ["spot"]:
                        if binance_symbol in self.mock_markets[market_type]["binance_format"]:
                            return True
                except Exception:
                    pass
                    
                return False
            else:
                # In live mode, check if the market is in available markets
                if market in self._available_markets:
                    return True
                    
                # Try converting the market symbol
                try:
                    binance_symbol = self._convert_market_symbol(market)
                    return binance_symbol in self._available_markets
                except Exception:
                    return False
                
        except Exception as e:
            logger.error(f"Error validating market {market}: {str(e)}")
            return False

    def _convert_market_symbol(self, market: str) -> str:
        """
        Convert market symbol to Binance format.
        
        Args:
            market (str): Market symbol (e.g., 'BTC-USDT' or 'BTCUSDT')
            
        Returns:
            str: Market symbol in Binance format (e.g., 'BTCUSDT')
        """
        try:
            # If already in Binance format, return as is
            if market.isupper() and "-" not in market and "USDT" in market:
                return market
            
            # Try to use the symbol mapper first
            try:
                return self.symbol_mapper.to_exchange_symbol("binance", market)
            except ValueError:
                pass
                
            # Handle standard format (e.g., BTC-USDT)
            if "-" in market:
                base, quote = market.split("-")
                # Convert USD or USDC to USDT for Binance
                if quote in ["USD", "USDC"]:
                    quote = "USDT"
                return f"{base.upper()}{quote.upper()}"
                
            # Handle other formats
            return market.replace("-", "").upper()
            
        except Exception as e:
            logger.error(f"Error converting market symbol {market}: {str(e)}")
            # Return original market as fallback
            return market