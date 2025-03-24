"""
Drift exchange handler implementation using the Drift Protocol SDK and custom API endpoints.
"""

import asyncio
import logging
import os
import time
import json
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

import aiohttp
import base58
from anchorpy import Provider, Wallet
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Finalized, Processed
from driftpy.drift_client import DriftClient, AccountSubscriptionConfig, DriftClientConfig
from driftpy.drift_user import DriftUser
from driftpy.accounts import get_perp_market_account, get_spot_market_account, get_user_account
from driftpy.constants.config import configs
from driftpy.types import PerpMarketAccount, SpotMarketAccount, UserAccount, TxParams
from driftpy.math.spot_market import get_token_amount
from driftpy.math.perp_position import calculate_perp_pnl
from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
from driftpy.keypair import load_keypair
from driftpy.accounts.oracle import *
from driftpy.accounts.user import User
from driftpy.accounts.bulk_account_loader import BulkAccountLoader
from driftpy.constants.config import Config
from driftpy.constants.numeric_constants import *
from driftpy.drift_client import DriftClient
from driftpy.drift_user import DriftUser
from driftpy.types import MarketType, OrderType, OrderParams
from driftpy.accounts.get_accounts import get_perp_market_account, get_spot_market_account
from driftpy.accounts.oracle import get_markets_and_oracles

from src.core.models import StandardizedCandle, TimeRange
from src.core.exceptions import ExchangeError, ValidationError, NotInitializedError
from .base import BaseExchangeHandler, ExchangeConfig

logger = logging.getLogger(__name__)

class DriftHandler(BaseExchangeHandler):
    """Handler for Drift exchange data."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Drift exchange handler with configuration."""
        super().__init__(config)
        self.network = config.get('network', 'mainnet')
        self.program_id = 'dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH' if self.network == 'mainnet' else 'DRiP2Pn2YbLqbpn3TKwJtPVENa1fRzxsRnTcVXX5whaT'
        self.rpc_url = os.getenv('MAINNET_RPC_ENDPOINT') if self.network == 'mainnet' else os.getenv('DEVNET_RPC_ENDPOINT')
        self.rate_limit = config.get('rate_limit', 10)
        self.markets = config.get('markets', [])
        self.base_url = config.get('base_url')
        self.client = None
        self.connection = None
        self.keypair = None
        self.market_lookup = {}
        self.logger = logging.getLogger(__name__)
        
        # Market caching
        self._available_markets = set()
        self._market_cache = {}
        self._last_market_update = None
        self._market_cache_ttl = timedelta(minutes=15)
        
        # Rate limiting setup
        self._last_request_time = 0
        self._request_interval = 1.0 / self.rate_limit
        
        # Retry configuration
        self._retry_config = {
            'max_retries': 3,
            'base_delay': 1,
            'max_delay': 10
        }
        
        # Get keypair path from config or environment
        self.keypair_path = (
            config.get('private_key_path') if config.get('private_key_path')
            else os.environ.get('MAIN_KEY_PATH')  # Use MAIN_KEY_PATH as that's what we verified has 15 SOL
        )
        if not self.keypair_path:
            logger.warning("No keypair path provided. Some functionality may be limited.")

    async def start(self) -> None:
        """Start the Drift exchange handler."""
        try:
            self.logger.info("Starting Drift exchange handler...")
            await self._initialize_connection()
            await super().start()
        except Exception as e:
            self.logger.error(f"Failed to start Drift handler: {e}")
            raise

    async def _initialize_connection(self) -> None:
        """Initialize connection to Drift."""
        try:
            # Load keypair from file
            key_bytes = None
            with open(os.getenv('MAIN_KEY_PATH'), 'r') as f:
                key_json = json.load(f)
                key_bytes = bytes(key_json)
            
            if not key_bytes:
                raise ExchangeError("Failed to load keypair from MAIN_KEY_PATH")
                
            self.keypair = Keypair.from_bytes(key_bytes)
            self.logger.info(f"Loaded keypair from {os.getenv('MAIN_KEY_PATH')}")
            
            # Initialize Solana connection
            self.connection = AsyncClient(self.rpc_url)
            self.logger.info(f"Connected to Solana RPC at {self.rpc_url}")
            
            # Initialize Drift client with proper configuration for devnet/mainnet
            self.client = DriftClient(
                connection=self.connection,
                wallet=self.keypair,
                program_id=self.program_id,
                opts=DriftClientConfig(
                    env=self.network,
                    skip_preflight=True,
                    commitment='confirmed'
                )
            )
            
            # Initialize user account if needed
            try:
                await self.client.initialize_user()
                self.logger.info("Initialized new Drift user account")
            except Exception as e:
                if "already in use" in str(e):
                    self.logger.info("User account already exists")
                else:
                    raise e
                    
            # Add default subaccount if needed
            try:
                await self.client.add_sub_account(0)
                self.logger.info("Added default subaccount (0)")
            except Exception as e:
                if "already exists" in str(e):
                    self.logger.info("Default subaccount already exists")
                else:
                    raise e
                    
            # Verify we can fetch the user account
            user = await self.client.get_user()
            if not user:
                raise ExchangeError("Failed to fetch user account after initialization")
                
            self.logger.info("Successfully initialized Drift connection")
            self.authenticated = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection: {str(e)}")
            raise ExchangeError(f"Failed to initialize connection: {str(e)}")

    async def stop(self) -> None:
        """Stop the handler and close all connections."""
        # Close aiohttp session
        if self._session:
            await self._session.close()
            self._session = None
        
        # Close all Solana RPC connections
        for connection in self._connections:
            if hasattr(connection, 'close'):
                try:
                    await connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
        
        # Clear connection list
        self._connections = []
        
        # Reset state
        self.client = None
        self.connection = None
        self.keypair = None
        self.market_lookup = {}
        self.authenticated = False
        
        await super().stop()
        logger.info("Stopped Drift exchange handler")

    async def _init_market_lookup(self) -> None:
        """Initialize market lookup tables."""
        if not self.client:
            raise NotInitializedError("Drift client not initialized")
        
        try:
            # Get all perpetual markets
            perp_markets = await self.client.get_perp_market_accounts()
            
            # Sort markets by index for consistency
            sorted_perp_markets = sorted(perp_markets, key=lambda x: x.market_index)
            
            # Extract market names and cache them
            self._available_markets = {
                bytes(x.account.name).decode("utf-8").strip()
                for x in sorted_perp_markets
            }
            
            # Cache market metadata for later use
            for market in sorted_perp_markets:
                market_index = market.market_index
                market_name = bytes(market.account.name).decode("utf-8").strip()
                
                # Add to lookup tables
                self.market_name_lookup[market_index] = market_name
                self.market_index_lookup[market_name] = market_index
                
                # Cache market account
                self._market_cache[market_name] = {
                    'account': market.account,
                    'timestamp': time.time()
                }
            
            self.market_lookup_initialized = True
            logger.info(f"Initialized {len(self._available_markets)} markets")
            
        except Exception as e:
            logger.error(f"Error initializing market lookup: {e}")
            raise

    async def get_markets(self) -> List[str]:
        """Get list of available markets on Drift."""
        if not self.market_lookup_initialized:
            await self._init_market_lookup()
        return list(self._available_markets)

    async def get_market_account(self, market_name: str) -> PerpMarketAccount:
        """
        Get perp market account by market name.
        
        Args:
            market_name: Market name (e.g. "BTC-PERP")
            
        Returns:
            PerpMarketAccount: The perpetual market account
        """
        if not market_name.endswith("-PERP"):
            market_name = f"{market_name}-PERP"
        
        # Check if market is in cache and still valid
        if market_name in self._market_cache:
            cached = self._market_cache[market_name]
            if time.time() - cached['timestamp'] < 3600:  # 1 hour cache
                return cached['account']
        
        # Get market index
        if not self.market_lookup_initialized:
            await self._init_market_lookup()
            
        market_index = self.market_index_lookup.get(market_name)
        if market_index is None:
            raise ValidationError(f"Market {market_name} not found")
        
        # Get market account
        market_account = await get_perp_market_account(
            self.client.program,
            market_index
        )
        
        # Update cache
        self._market_cache[market_name] = {
            'account': market_account,
            'timestamp': time.time()
        }
        
        return market_account

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """
        Fetch historical candles from Drift using historical data API.
        
        Args:
            market: Market symbol (e.g. "BTC-PERP")
            time_range: Time range to fetch
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            List of StandardizedCandle objects
        """
        # Ensure market is in proper format
        if not market.endswith("-PERP"):
            market = f"{market}-PERP"
        
        # Get market index
        if not self.market_lookup_initialized:
            await self._init_market_lookup()
        
        market_index = self.market_index_lookup.get(market)
        if market_index is None:
            raise ValidationError(f"Market {market} not found")
        
        # Convert resolution to API format
        api_resolution = self._convert_resolution(resolution)
        
        # Convert time range to Unix timestamps (seconds)
        start_time = int(time_range.start.timestamp())
        end_time = int(time_range.end.timestamp())
        
        # Calculate appropriate batching based on resolution and time range
        time_chunks = self._calculate_time_chunks(start_time, end_time, api_resolution)
        
        all_candles = []
        for chunk_start, chunk_end in time_chunks:
            try:
                # Format API endpoint for historical data
                endpoint = f"/historical/candles/{market_index}/{api_resolution}"
                params = {
                    'startTime': chunk_start,
                    'endTime': chunk_end
                }
                
                # Make API request to historical endpoint
                response = await self._api_request("GET", endpoint, params, use_live_api=False)
                
                # Process candles
                if response and 'data' in response:
                    for candle_data in response['data']:
                        try:
                            # Convert timestamp to datetime
                            timestamp = datetime.fromtimestamp(
                                int(candle_data['time']) / 1000,  # Convert milliseconds to seconds
                                tz=timezone.utc
                            )
                            
                            # Create standardized candle
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
                            logger.warning(f"Error processing candle data: {e}")
                            continue
                
                # Respect rate limits
                await asyncio.sleep(self._request_interval)
                
            except Exception as e:
                logger.error(f"Error fetching historical candles for {market}: {e}")
                raise ExchangeError(f"Failed to fetch historical candles: {e}")
                
        # Sort candles by timestamp
        all_candles.sort(key=lambda x: x.timestamp)
        
        logger.info(f"Fetched {len(all_candles)} historical candles for {market}")
        return all_candles

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str
    ) -> StandardizedCandle:
        """
        Fetch current live candle using the live API endpoint.
        
        Args:
            market: Market symbol (e.g. "BTC-PERP")
            resolution: Candle resolution (e.g. "1m", "1h", "1d")
            
        Returns:
            StandardizedCandle for the current period
        """
        # Ensure market is in proper format
        if not market.endswith("-PERP"):
            market = f"{market}-PERP"
        
        try:
            # Get market index
            if not self.market_lookup_initialized:
                await self._init_market_lookup()
                
            market_index = self.market_index_lookup.get(market)
            if market_index is None:
                raise ValidationError(f"Market {market} not found")
            
            # Format API endpoint for live data
            endpoint = f"/v2/candles/{market_index}/latest"
            params = {
                'resolution': self._convert_resolution(resolution)
            }
            
            # Make API request to live endpoint
            response = await self._api_request("GET", endpoint, params, use_live_api=True)
            
            if not response or 'data' not in response:
                raise ExchangeError(f"No live data returned for {market}")
                
            candle_data = response['data']
            
            # Convert timestamp to datetime
            timestamp = datetime.fromtimestamp(
                int(candle_data['time']) / 1000,  # Convert milliseconds to seconds
                tz=timezone.utc
            )
            
            # Create standardized candle
            return StandardizedCandle(
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
            
        except Exception as e:
            logger.error(f"Error fetching live candle for {market}: {e}")
            raise ExchangeError(f"Failed to fetch live candle: {e}")

    def _convert_resolution(self, resolution: str) -> str:
        """
        Convert standard resolution format to Drift API format.
        
        Args:
            resolution: Resolution in standard format (e.g. "1m", "1h", "1d")

        Returns:
            Resolution in Drift API format
        """
        # Standardize resolution format
        resolution = resolution.lower()
        
        # Map of standard resolutions to Drift API resolutions
        resolution_map = {
            "1m": "1MIN",
            "1": "1MIN",
            "5m": "5MIN",
            "5": "5MIN",
            "15m": "15MIN",
            "15": "15MIN",
            "30m": "30MIN",
            "30": "30MIN",
            "1h": "1H",
            "60": "1H",
            "4h": "4H",
            "240": "4H",
            "1d": "1D",
            "1440": "1D",
            "1w": "1W",
            "10080": "1W"
        }
        
        # Return mapped resolution or default to 1h
        if resolution in resolution_map:
            return resolution_map[resolution]
        else:
            logger.warning(f"Unsupported resolution: {resolution}. Defaulting to 1H")
            return "1H"

    def _calculate_time_chunks(self, start_time: int, end_time: int, resolution: str) -> List[tuple]:
        """
        Calculate time chunks for API requests based on resolution.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            resolution: Resolution in Drift API format

        Returns:
            List of (chunk_start, chunk_end) tuples
        """
        # Maximum number of candles per request
        max_candles = 1000
        
        # Calculate seconds per candle based on resolution
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
        
        # Calculate max time range per request
        max_time_range = seconds_per_candle * max_candles
        
        # Create time chunks
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
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_live_api: bool = False
    ) -> Any:
        """
        Make a request to the Drift API with rate limiting.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body
            headers: HTTP headers
            use_live_api: Whether to use the live API endpoint
            
        Returns:
            API response as JSON
        """
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        # Apply rate limiting
        now = time.time()
        time_since_last_request = now - self._last_request_time
        if time_since_last_request < self._request_interval:
            await asyncio.sleep(self._request_interval - time_since_last_request)
        self._last_request_time = time.time()
        
        # Choose appropriate base URL
        base_url = self.live_api_url if use_live_api else self.base_url
        url = f"{base_url}{endpoint}"
        
        # Default headers
        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
        # Add rate limit headers if available
        if self.rate_limit:
            headers['X-RateLimit-Limit'] = str(self.rate_limit)
            
        # Make request with retries
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # Initial delay in seconds
        
        while retry_count < max_retries:
            try:
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    json=data,
                    headers=headers
                ) as response:
                    # Check for errors
                    if response.status >= 400:
                        error_text = await response.text()
                        if response.status == 429:
                            # Rate limit exceeded - use header or default
                            retry_after = int(response.headers.get('Retry-After', '60'))
                            logger.warning(f"Rate limit exceeded. Retry after {retry_after}s. Error: {error_text}")
                            await asyncio.sleep(retry_after)
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"Drift API error ({response.status}): {error_text}")
                            raise ExchangeError(f"Drift API error ({response.status}): {error_text}")
                            
                    # Parse response
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                retry_count += 1
                wait_time = retry_delay * (2 ** (retry_count - 1))
                logger.warning(f"Request failed (attempt {retry_count}/{max_retries}): {str(e)}")
                logger.warning(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
                if retry_count >= max_retries:
                    logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                    raise ExchangeError(f"Drift API request failed: {str(e)}")
                    
        raise ExchangeError("Maximum retries exceeded")

    def validate_standard_symbol(self, market: str) -> bool:
        """
        Validate if a market is supported in standard format.
        
        Args:
            market: Market symbol (e.g. "BTC-PERP")
            
        Returns:
            True if the market is valid, False otherwise
        """
        # Ensure market is in proper format
        if not market.endswith("-PERP"):
            market = f"{market}-PERP"
            
        return market in self._available_markets

    async def convert_standard_symbol(self, market: str) -> str:
        """
        Convert a standard market symbol to Drift format.
        
        Args:
            market: Standard market symbol (e.g. "BTC", "BTC-USD")
            
        Returns:
            Market symbol in Drift format (e.g. "BTC-PERP")
        """
        # If already in proper format, return as is
        if market.endswith("-PERP"):
            return market
            
        # Convert from base format (e.g. "BTC" to "BTC-PERP")
        if "-" not in market:
            return f"{market}-PERP"
            
        # Convert from spot format (e.g. "BTC-USD" to "BTC-PERP")
        if market.endswith("-USD") or market.endswith("-USDC"):
            base = market.split("-")[0]
            return f"{base}-PERP"
            
        # If we don't recognize the format, just return with -PERP suffix
        return f"{market}-PERP"

    @staticmethod
    async def self_test() -> bool:
        """
        Run a self-test to verify that the handler is working correctly.

        Returns:
            True if tests pass, False otherwise
        """
        try:
            # Create handler with default config
            config = ExchangeConfig(name="drift")
            handler = DriftHandler(config)
            
            # Start the handler
            await handler.start()
            
            try:
                # Test basic market fetching
                markets = await handler.get_markets()
                print(f"Found {len(markets)} markets")
                if not markets:
                    print("Error: No markets found")
                    return False

                # Test historical data fetching
                if "BTC-PERP" in markets:
                    end_time = datetime.now(timezone.utc)
                    start_time = end_time - timedelta(days=1)
                    
                    candles = await handler.fetch_historical_candles(
                        "BTC-PERP",
                        TimeRange(start=start_time, end=end_time),
                        resolution="1h"
                    )
                    
                    print(f"Fetched {len(candles)} historical candles")
                    if not candles:
                        print("Error: No candles found")
                        return False
                    
                    # Test live candle fetching
                    live_candle = await handler.fetch_live_candles("BTC-PERP", "1h")
                    print(f"Fetched live candle: {live_candle}")
                
                print("All tests passed!")
                return True
                
            finally:
                # Ensure we clean up
                await handler.stop()
            
        except Exception as e:
            print(f"Error during self-test: {e}")
            return False

async def main():
    """Example usage of DriftHandler."""
    await DriftHandler.self_test()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the example
    asyncio.run(main())
