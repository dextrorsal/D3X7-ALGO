"""
Drift data provider implementation.
Handles market data operations, historical data fetching, and live data streaming.
"""

import asyncio
import logging
import time
import csv
import io
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
            "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
            if self.client.network == "mainnet" 
            else "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
        )
        
    async def get_markets(self) -> List[str]:
        """Get list of available markets.
        
        Returns:
            List of market names
        """
        return list(self.client.market_name_lookup.keys())
    
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
        market_index = self.client.get_market_index(market)
        if market_index is None:
            raise ValidationError(f"Market {market} not found")
            
        api_resolution = self._convert_resolution(resolution)
        all_candles = []
        
        # Initialize session if needed
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        # Process each day in the time range
        current_date = time_range.start.date()
        end_date = time_range.end.date()
        
        while current_date <= end_date:
            try:
                # Format API endpoint for historical data using current date
                endpoint = f"/market/{market}/tradeRecords/{current_date.year}/{current_date.strftime('%Y%m%d')}"
                
                # Make request
                csv_data = await self._api_request("GET", endpoint)
                
                if not csv_data:
                    logger.warning(f"No data returned for {market} on {current_date}")
                    current_date += timedelta(days=1)
                    continue
                
                # Process CSV data
                reader = csv.DictReader(io.StringIO(csv_data))
                logger.info(f"CSV headers: {reader.fieldnames}")
                
                for row in reader:
                    try:
                        # Try different timestamp fields
                        timestamp = None
                        for ts_field in ['timestamp', 'time', 'ts', 'txTime']:
                            if ts_field in row and row[ts_field]:
                                try:
                                    ts_value = float(row[ts_field])
                                    # Handle both seconds and milliseconds timestamps
                                    if len(str(int(ts_value))) > 10:
                                        ts_value /= 1000
                                    timestamp = datetime.fromtimestamp(ts_value, tz=timezone.utc)
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        if timestamp is None:
                            logger.warning(f"No valid timestamp found in row: {row}")
                            continue
                        
                        # Skip if outside time range
                        if timestamp < time_range.start or timestamp > time_range.end:
                            continue
                        
                        # Try to get price from different possible fields
                        price = None
                        for price_field in ['price', 'markPrice', 'oraclePrice', 'fillPrice']:
                            if price_field in row and row[price_field]:
                                try:
                                    price = float(row[price_field])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        if price is None:
                            logger.warning(f"No valid price found in row: {row}")
                            continue
                        
                        # Try to get size/volume from different possible fields
                        volume = 0.0
                        for size_field in ['size', 'baseAssetAmountFilled', 'quantity', 'amount']:
                            if size_field in row and row[size_field]:
                                try:
                                    volume = float(row[size_field])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        candle = StandardizedCandle(
                            timestamp=timestamp,
                            open=price,
                            high=price,
                            low=price,
                            close=price,
                            volume=volume,
                            market=market,
                            resolution=resolution,
                            source="drift"
                        )
                        
                        all_candles.append(candle)
                        
                    except Exception as e:
                        logger.warning(f"Error processing trade data: {e}")
                        continue
                
                # Move to next day
                current_date += timedelta(days=1)
                
                # Respect rate limits
                await asyncio.sleep(self._request_interval)
                
            except Exception as e:
                logger.error(f"Error fetching trades for {market} on {current_date}: {e}")
                raise ExchangeError(f"Failed to fetch historical data: {e}")
        
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
        market_index = self.client.get_market_index(market)
        if market_index is None:
            raise ValidationError(f"Market {market} not found")
        
        try:
            # Initialize session if needed
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Get latest trades for the market
            today = datetime.now(timezone.utc)
            endpoint = f"/market/{market}/tradeRecords/{today.year}/{today.strftime('%Y%m%d')}"
            
            # Make request
            csv_data = await self._api_request("GET", endpoint)
            
            if not csv_data:
                return None
            
            # Process CSV data
            reader = csv.DictReader(io.StringIO(csv_data))
            trades = list(reader)
            
            if not trades:
                return None
            
            # Use the most recent trade as the current candle
            latest_trade = trades[-1]
            
            # Convert timestamp
            timestamp = datetime.fromtimestamp(
                int(float(latest_trade['timestamp'])) / 1000,
                tz=timezone.utc
            )
            
            # Create standardized candle from latest trade
            return StandardizedCandle(
                timestamp=timestamp,
                open=float(latest_trade['price']),
                high=float(latest_trade['price']),
                low=float(latest_trade['price']),
                close=float(latest_trade['price']),
                volume=float(latest_trade.get('size', 0)),
                market=market,
                resolution=resolution,
                source="drift"
            )
            
        except Exception as e:
            logger.error(f"Error fetching live data for {market}: {e}")
            return None
    
    def _convert_resolution(self, resolution: str) -> str:
        """Convert resolution to API format.
        
        Args:
            resolution: Resolution string (e.g. "1m", "1h", "1d")
            
        Returns:
            API resolution format
        """
        resolution = resolution.lower()
        if resolution.endswith('m'):
            return resolution.replace('m', '')
        elif resolution.endswith('h'):
            minutes = int(resolution[:-1]) * 60
            return str(minutes)
        elif resolution.endswith('d'):
            minutes = int(resolution[:-1]) * 24 * 60
            return str(minutes)
        elif resolution.endswith('w'):
            minutes = int(resolution[:-1]) * 7 * 24 * 60
            return str(minutes)
        else:
            raise ValidationError(f"Invalid resolution format: {resolution}")
    
    def _calculate_time_chunks(
        self,
        start_time: int,
        end_time: int,
        resolution: str
    ) -> List[tuple]:
        """Calculate time chunks for batched requests.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            resolution: API resolution format
            
        Returns:
            List of (chunk_start, chunk_end) tuples
        """
        # Convert resolution to minutes
        resolution_minutes = int(resolution)
        
        # Calculate chunk size based on resolution
        if resolution_minutes <= 60:  # 1h or less
            chunk_size = 24 * 60 * 60  # 1 day
        elif resolution_minutes <= 240:  # 4h or less
            chunk_size = 7 * 24 * 60 * 60  # 1 week
        else:
            chunk_size = 30 * 24 * 60 * 60  # 30 days
        
        chunks = []
        current = start_time
        
        while current < end_time:
            chunk_end = min(current + chunk_size, end_time)
            chunks.append((current, chunk_end))
            current = chunk_end
        
        return chunks
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> str:
        """Make API request with rate limiting.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            
        Returns:
            Response data as string (CSV format)
        """
        # Ensure minimum time between requests
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._request_interval:
            await asyncio.sleep(self._request_interval - time_since_last)
        
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making request to: {url}")
        
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                headers=headers
            ) as response:
                response.raise_for_status()
                return await response.text()
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise ExchangeError(f"API request failed: {e}")
        
        finally:
            self._last_request_time = time.time()
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
