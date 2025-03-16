"""
Coinbase exchange handler implementation with public API endpoints.
"""

import logging
import time
from typing import List, Dict, Optional, Union
import asyncio
from datetime import datetime, timezone
import json
import pandas as pd
import numpy as np
import aiohttp

from src.core.models import StandardizedCandle, TimeRange
from src.exchanges.base import BaseExchangeHandler
from src.utils.time_utils import (
    convert_timestamp_to_datetime,
    get_current_timestamp,
    get_timestamp_from_datetime,
)
from src.core.exceptions import ExchangeError, ValidationError, RateLimitError

logger = logging.getLogger(__name__)

class CoinbaseHandler(BaseExchangeHandler):
    """Handler for Coinbase exchange data."""
    
    def __init__(self, config):
        """Initialize Coinbase handler with configuration."""
        super().__init__(config)
        self.base_url = "https://api.coinbase.com"
        self._available_markets = set()  # Cache for available markets
        self._is_test_mode = False
        self._mock_markets = ["BTC-USD", "ETH-USD", "SOL-USD"]
        # Updated to match Coinbase's exact granularity values
        self.timeframe_map = {
            "1": "ONE_MINUTE",
            "5": "FIVE_MINUTE",
            "15": "FIFTEEN_MINUTE",
            "30": "THIRTY_MINUTE",
            "60": "ONE_HOUR",
            "120": "TWO_HOUR",
            "360": "SIX_HOUR",
            "1D": "ONE_DAY"
        }
        logger.info("Initialized Coinbase handler with correct granularity mapping")

    async def start(self):
        """Start the handler and fetch initial market data."""
        await super().start()
        try:
            # Fetch and cache available markets on startup
            # This can be done without authentication
            markets = await self.get_markets()
            self._available_markets = set(markets)
            logger.info(f"Cached {len(self._available_markets)} available markets")
        except Exception as e:
            logger.error(f"Failed to cache markets during startup: {e}")
            # Fall back to test mode
            self._is_test_mode = True
            self._setup_test_mode()

    def _setup_test_mode(self):
        """Set up test mode with mock data."""
        self._is_test_mode = True
        self._available_markets = set(self._mock_markets)
        logger.info(f"Initialized test mode with {len(self._mock_markets)} mock markets")

    def validate_market(self, market: str) -> bool:
        """
        Validate if a market symbol is available on Coinbase.
        
        Args:
            market (str): Market symbol to validate (e.g., "BTC-USD", "SOL-PERP")
            
        Returns:
            bool: True if market is valid, False otherwise
        """
        if not isinstance(market, str):
            raise ValidationError("Market must be a string")
        
        # Convert market to Coinbase format
        coinbase_market = self._convert_market_symbol(market)
        
        # First check if it's in our cached markets
        if self._available_markets and coinbase_market in self._available_markets:
            logger.debug(f"Market {coinbase_market} found in cache")
            return True
            
        # If not in cache or cache is empty, check configured markets
        # Don't try to refresh markets here as it causes event loop issues
        return market in self.config.markets or coinbase_market in self.config.markets

    async def validate_standard_symbol(self, market: str) -> bool:
        """
        Asynchronously validate if a standard market symbol is available on Coinbase.
        
        Args:
            market (str): Market symbol to validate (e.g., "BTC-USD", "SOL-PERP")
            
        Returns:
            bool: True if market is valid, False otherwise
        """
        if not isinstance(market, str):
            raise ValidationError("Market must be a string")
        
        # Convert market to Coinbase format
        coinbase_market = self._convert_market_symbol(market)
        
        # First check if it's in our cached markets
        if self._available_markets and coinbase_market in self._available_markets:
            logger.debug(f"Market {coinbase_market} found in cache")
            return True
            
        # If not in cache or cache is empty, try to refresh markets
        try:
            markets = await self.get_markets()
            self._available_markets = set(markets)
            return coinbase_market in self._available_markets
        except Exception as e:
            logger.error(f"Error validating market {market}: {e}")
            # If we can't fetch markets, fall back to checking configured markets
            return market in self.config.markets or coinbase_market in self.config.markets

    def _convert_market_symbol(self, market: str) -> str:
        """
        Convert internal market symbol to Coinbase format.
        Example: 
            - SOL-PERP -> SOL-USD
            - SOLUSDT -> SOL-USD
        """
        if not isinstance(market, str):
            raise ValidationError("Market must be a string")
            
        market = market.upper()  # Ensure consistent casing
        logger.debug(f"Converting market symbol: {market}")
        # Remove -PERP suffix if present (from Drift format)
        market = market.replace('-PERP', '')
        
        # Convert from Binance format (SOLUSDT -> SOL-USD)
        if 'USDT' in market:
            base = market.replace('USDT', '')
            return f"{base}-USD"
            
        # If already in Coinbase format (SOL-USD), return as is
        if '-USD' in market:
            return market
            
        # Default case: add -USD if no other format detected
        return f"{market}-USD"

    def _get_headers(self, method: str = "GET", path: str = "") -> Dict:
        """
        Return headers for API requests.
        If credentials are provided, include authentication headers.
        """
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.config.credentials:
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
            signature = self._generate_signature(method, path, timestamp)
            headers.update({
                'CB-ACCESS-KEY': self.config.credentials.api_key,
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
                'CB-ACCESS-PASSPHRASE': self.config.credentials.additional_params.get("passphrase", "")
            })
        return headers

    def _generate_signature(self, method: str, path: str, timestamp: str) -> str:
        """
        Stub for generating a signature.
        (In tests, this method is patched.)
        """
        return "stub_signature"

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """
        Fetch historical candle data from Coinbase public API.
        
        Args:
            market (str): Market symbol (e.g., "BTC-USD")
            time_range (TimeRange): Time range to fetch data for
            resolution (str): Candle resolution (e.g., "1", "5", "15", "60")
            
        Returns:
            List[StandardizedCandle]: List of standardized candles
        """
        self.validate_market(market)
        coinbase_symbol = self._convert_market_symbol(market)
        granularity = self.timeframe_map.get(resolution)
        if not granularity:
            raise ValidationError(f"Invalid resolution: {resolution}")
        if time_range.end < time_range.start:
            raise ValidationError("End time must be after start time")
        
        # If in test mode, return mock data
        if self._is_test_mode:
            return self._generate_mock_candles(time_range, resolution, market)
            
        logger.debug(f"Fetching {market} data from {time_range.start} to {time_range.end}")
        candles = []
        start_time = int(time_range.start.timestamp())
        end_time = int(time_range.end.timestamp())
        empty_batch_counter = 0
        max_empty_batches = 3

        try:
            while start_time < end_time:
                batch_duration = self._get_granularity_seconds(resolution) * 300
                current_end = min(start_time + batch_duration, end_time)
                
                path = f'/api/v3/brokerage/market/products/{coinbase_symbol}/candles'
                params = {
                    'start': str(start_time),
                    'end': str(current_end),
                    'granularity': granularity
                }
                
                try:
                    # Use direct HTTP request for public endpoints if no session is available
                    if not self._session:
                        # Ensure we have a session
                        await self.start()
                    
                    # Use the existing session and _make_request method
                    response_data = await self._make_request(
                        method='GET',
                        endpoint=path,
                        params=params,
                        headers=self._get_headers("GET", path)
                    )
                except RateLimitError as e:
                    logger.warning(f"Rate limit hit: {e}. Waiting 5 seconds before retrying.")
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    logger.error(f"Error fetching data: {e}")
                    await asyncio.sleep(5)
                    continue

                # Handle response format
                candle_list = []
                if isinstance(response_data, dict):
                    if 'candles' in response_data:
                        candle_list = response_data['candles']
                    elif 'data' in response_data:
                        candle_list = response_data['data']
                    else:
                        logger.warning(f"Unexpected response format: {response_data}")
                elif isinstance(response_data, list):
                    candle_list = response_data
                else:
                    logger.warning(f"Unexpected response type: {type(response_data)}")
                
                if not candle_list:
                    empty_batch_counter += 1
                    if empty_batch_counter >= max_empty_batches:
                        logger.warning(f"Received {max_empty_batches} empty batches in a row, stopping.")
                        break
                    start_time = current_end
                    continue
                
                empty_batch_counter = 0
                for candle_data in candle_list:
                    try:
                        # Handle list format
                        if isinstance(candle_data, list):
                            candle = StandardizedCandle(
                                timestamp=datetime.fromtimestamp(float(candle_data[0]), tz=timezone.utc),
                                open=float(candle_data[1]),
                                high=float(candle_data[2]),
                                low=float(candle_data[3]),
                                close=float(candle_data[4]),
                                volume=float(candle_data[5]),
                                source='coinbase',
                                resolution=resolution,
                                market=market,
                                raw_data=candle_data
                            )
                        # Handle dictionary format
                        elif isinstance(candle_data, dict):
                            # Try different timestamp field names
                            timestamp = None
                            for field in ['time', 'timestamp', 'start']:
                                if field in candle_data:
                                    timestamp = candle_data[field]
                                    break
                            
                            if timestamp is None:
                                logger.warning(f"No timestamp found in candle data: {candle_data}")
                                continue
                            
                            # Convert timestamp to datetime
                            if isinstance(timestamp, str):
                                try:
                                    timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                                except ValueError:
                                    timestamp = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
                            else:
                                timestamp = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
                            
                            # Create standardized candle
                            candle = StandardizedCandle(
                                timestamp=timestamp,
                                open=float(candle_data.get('open', 0.0)),
                                high=float(candle_data.get('high', 0.0)),
                                low=float(candle_data.get('low', 0.0)),
                                close=float(candle_data.get('close', 0.0)),
                                volume=float(candle_data.get('volume', 0.0)),
                                source='coinbase',
                                resolution=resolution,
                                market=market,
                                raw_data=candle_data
                            )
                        else:
                            logger.warning(f"Unexpected candle data format: {type(candle_data)}")
                            continue
                        
                        candles.append(candle)
                        
                    except (ValueError, KeyError, TypeError) as e:
                        logger.warning(f"Error parsing candle data: {e}")
                        continue
                
                start_time = current_end
                await asyncio.sleep(0.1)  # Rate limiting
            
            # Sort candles by timestamp
            candles.sort(key=lambda x: x.timestamp)
            return candles

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
        interval_seconds = self._get_granularity_seconds(resolution)
        
        while current_time <= time_range.end:
            # Generate a mock candle
            candle = StandardizedCandle(
                timestamp=current_time,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                source='coinbase',
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
        resolution: str
    ) -> StandardizedCandle:
        """Fetch live ticker data from Coinbase public API."""
        self.validate_market(market)
        coinbase_symbol = self._convert_market_symbol(market)

        try:
            path = f'/api/v3/brokerage/market/products/{coinbase_symbol}/ticker'
            params = {'limit': 1}
            response = await self._make_request(
                method='GET',
                endpoint=path,
                params=params,
                headers=self._get_headers("GET", path)
            )
            if not response or 'trades' not in response:
                raise ExchangeError(f"No live data available for {market}")
            trade_data = response['trades'][0]
            current_time = self.standardize_timestamp(
                int(datetime.strptime(trade_data['time'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())
            )
            price = float(trade_data['price'])
            candle = StandardizedCandle(
                timestamp=current_time,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=float(trade_data['size']),
                source='coinbase',
                resolution=resolution,
                market=market,
                raw_data={
                    'trade': trade_data,
                    'best_bid': float(response['best_bid']),
                    'best_ask': float(response['best_ask'])
                }
            )
            self.validate_candle(candle)
            return candle

        except Exception as e:
            raise ExchangeError(f"Failed to fetch live data: {e}")

    def _get_granularity_seconds(self, resolution: str) -> int:
        """Convert resolution to seconds."""
        resolution_map = {
            "1": 60,
            "5": 300,
            "15": 900,
            "30": 1800,
            "60": 3600,
            "120": 7200,
            "360": 21600,
            "1D": 86400
        }
        return resolution_map.get(resolution, 60)

    async def get_markets(self) -> List[str]:
        """Get available markets from Coinbase public API."""
        if self._is_test_mode:
            return self._mock_markets
            
        try:
            # Ensure we have a session
            if not self._session:
                await self.start()
                
            # Use direct HTTP request instead of _make_request to avoid potential issues
            url = f"{self.base_url}/api/v3/brokerage/market/products"
            headers = self._get_headers("GET", "/api/v3/brokerage/market/products")
            
            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExchangeError(f"API error: {response.status} - {error_text}")
                
                response_data = await response.json()
                
                if not response_data:
                    logger.error("No response received from Coinbase when fetching markets")
                    return []
                
                # Safely access the 'products' key with a default empty list
                products = response_data.get('products', [])
                return [product['product_id'] for product in products
                       if product.get('status') == 'online']
                
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            raise ExchangeError(f"Failed to fetch markets: {e}")
