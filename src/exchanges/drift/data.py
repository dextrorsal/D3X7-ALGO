"""
Drift data provider implementation.
Handles market data operations, historical data fetching, and live data streaming.
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

import aiohttp
from driftpy.types import PerpMarketAccount, SpotMarketAccount

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
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self._last_request_time = 0
        self._request_interval = 0.1  # 10 requests per second
        
        # Base URLs for API endpoints
        self.base_url = (
            "https://mainnet-beta.drift-history.com/v2" 
            if self.client.network == "mainnet" 
            else "https://devnet.drift-history.com/v2"
        )
        
    async def get_markets(self) -> List[str]:
        """Get list of available markets.
        
        Returns:
            List of market names
        """
        return list(self.client._market_name_lookup.values())
    
    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """Fetch historical candle data.
        
        Args:
            market: Market name (e.g. "SOL-PERP")
            time_range: Time range to fetch
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            List of standardized candles
        """
        # Ensure market exists
        if market not in self.client._market_index_lookup:
            raise ValidationError(f"Market {market} not found")
            
        market_index = self.client._market_index_lookup[market]
        api_resolution = self._convert_resolution(resolution)
        
        # Convert time range to timestamps
        start_time = int(time_range.start.timestamp())
        end_time = int(time_range.end.timestamp())
        
        # Calculate time chunks to avoid hitting rate limits
        chunks = self._calculate_time_chunks(start_time, end_time, api_resolution)
        all_candles = []
        
        # Initialize session if needed
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        for chunk_start, chunk_end in chunks:
            try:
                # Format API endpoint
                endpoint = f"/candles/{market_index}/{api_resolution}"
                params = {
                    'startTime': chunk_start,
                    'endTime': chunk_end
                }
                
                # Make request
                candles = await self._api_request("GET", endpoint, params)
                
                if not candles or 'data' not in candles:
                    logger.warning(f"No data returned for {market} from {chunk_start} to {chunk_end}")
                    continue
                
                # Process candles
                for candle_data in candles['data']:
                    try:
                        timestamp = datetime.fromtimestamp(
                            int(candle_data['time']) / 1000,
                            tz=timezone.utc
                        )
                        
                        candle = StandardizedCandle(
                            timestamp=timestamp,
                            open=float(candle_data['open']),
                            high=float(candle_data['high']),
                            low=float(candle_data['low']),
                            close=float(candle_data['close']),
                            volume=float(candle_data.get('volume', 0)),
                            market=market,
                            resolution=resolution,
                            source="drift"
                        )
                        
                        all_candles.append(candle)
                        
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Error processing candle: {e}")
                        continue
                
                # Respect rate limits
                await asyncio.sleep(self._request_interval)
                
            except Exception as e:
                logger.error(f"Error fetching candles for {market}: {e}")
                raise ExchangeError(f"Failed to fetch historical candles: {e}")
        
        # Sort candles by timestamp
        all_candles.sort(key=lambda x: x.timestamp)
        return all_candles
    
    async def fetch_live_candle(
        self,
        market: str,
        resolution: str
    ) -> Optional[StandardizedCandle]:
        """Fetch current live candle.
        
        Args:
            market: Market name (e.g. "SOL-PERP")
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            Current candle or None if not available
        """
        if market not in self.client._market_index_lookup:
            raise ValidationError(f"Market {market} not found")
            
        market_index = self.client._market_index_lookup[market]
        
        try:
            # Initialize session if needed
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Format API endpoint for live data
            endpoint = f"/candles/{market_index}/latest"
            params = {
                'resolution': self._convert_resolution(resolution)
            }
            
            # Make request
            response = await self._api_request("GET", endpoint, params)
            
            if not response or 'data' not in response:
                return None
            
            data = response['data']
            
            # Convert timestamp
            timestamp = datetime.fromtimestamp(
                int(data['time']) / 1000,
                tz=timezone.utc
            )
            
            # Create standardized candle
            return StandardizedCandle(
                timestamp=timestamp,
                open=float(data['open']),
                high=float(data['high']),
                low=float(data['low']),
                close=float(data['close']),
                volume=float(data.get('volume', 0)),
                market=market,
                resolution=resolution,
                source="drift"
            )
            
        except Exception as e:
            logger.error(f"Error fetching live candle for {market}: {e}")
            return None
    
    def _convert_resolution(self, resolution: str) -> str:
        """Convert standard resolution to API format."""
        resolution = resolution.lower()
        resolution_map = {
            "1m": "1MIN",
            "5m": "5MIN",
            "15m": "15MIN",
            "30m": "30MIN",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W"
        }
        return resolution_map.get(resolution, "1H")
    
    def _calculate_time_chunks(
        self,
        start_time: int,
        end_time: int,
        resolution: str
    ) -> List[tuple]:
        """Calculate time chunks for batched requests."""
        max_candles = 1000
        seconds_per_candle = {
            "1MIN": 60,
            "5MIN": 300,
            "15MIN": 900,
            "30MIN": 1800,
            "1H": 3600,
            "4H": 14400,
            "1D": 86400,
            "1W": 604800
        }.get(resolution, 3600)
        
        max_time_range = seconds_per_candle * max_candles
        chunks = []
        current_start = start_time
        
        while current_start < end_time:
            current_end = min(current_start + max_time_range, end_time)
            chunks.append((current_start, current_end))
            current_start = current_end
            
        return chunks
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Any:
        """Make API request with rate limiting."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        # Apply rate limiting
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._request_interval:
            await asyncio.sleep(self._request_interval - time_since_last)
        self._last_request_time = time.time()
        
        # Make request
        url = f"{self.base_url}{endpoint}"
        async with self._session.request(
            method,
            url,
            params=params,
            headers=headers
        ) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise ExchangeError(f"API error ({response.status}): {error_text}")
            return await response.json()
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
