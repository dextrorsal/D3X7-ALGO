"""
Drift exchange handler implementation.
"""

import logging
from typing import List, Optional
from datetime import datetime

from ...core.models import TimeRange, StandardizedCandle
from ...core.config import ExchangeConfig
from ..base import BaseExchangeHandler
from .client import DriftClient
from .data import DriftDataProvider
from .auth import DriftAuth

logger = logging.getLogger(__name__)

class DriftHandler(BaseExchangeHandler):
    """Handler for Drift exchange operations."""
    
    def __init__(self, config: ExchangeConfig, wallet_manager=None, drift_config=None):
        """Initialize the Drift handler.
        
        Args:
            config: Exchange configuration
            wallet_manager: Wallet manager instance
            drift_config: Drift-specific configuration (for devnet/mainnet settings)
        """
        super().__init__(config)
        self.wallet_manager = wallet_manager
        self.drift_config = drift_config
        self.client = None
        self.data_provider = None
        self.auth = None
        
        # Valid resolutions
        self.valid_resolutions = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    
    async def start(self):
        """Start the Drift handler."""
        try:
            if not self.wallet_manager:
                raise ValueError("Wallet manager is required for Drift handler")
            
            # Initialize authentication
            self.auth = DriftAuth(self.wallet_manager)
            await self.auth.authenticate()
            
            # Initialize client with authenticated wallet and config
            self.client = DriftClient(
                self.auth.get_wallet(),
                network="devnet" if self.drift_config else "mainnet",
                config=self.drift_config
            )
            await self.client.initialize()
            
            # Initialize data provider
            self.data_provider = DriftDataProvider(self.client)
            
            logger.info("Started Drift handler")
        except Exception as e:
            logger.error(f"Failed to start Drift handler: {e}")
            await self.stop()  # Cleanup on failure
            raise
    
    async def stop(self):
        """Stop the Drift handler."""
        try:
            if self.data_provider:
                await self.data_provider.cleanup()
                self.data_provider = None
                
            if self.client:
                await self.client.cleanup()
                self.client = None
                
            if self.auth:
                await self.auth.cleanup()
                self.auth = None
                
            logger.info("Stopped Drift handler")
        except Exception as e:
            logger.error(f"Error stopping Drift handler: {e}")
    
    def _validate_resolution(self, resolution: str):
        """Validate candle resolution."""
        resolution = resolution.lower()  # Convert to lowercase first
        if resolution not in self.valid_resolutions:
            raise ValueError(
                f"Invalid resolution {resolution}. "
                f"Must be one of: {', '.join(self.valid_resolutions)}"
            )
    
    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """Fetch historical candle data from Drift."""
        try:
            if not self.data_provider:
                raise ValueError("Data provider not initialized")
            
            self._validate_resolution(resolution)
            if not self.validate_market(market):
                raise ValueError(f"Market {market} not found")
            
            candles = await self.data_provider.fetch_historical_candles(
                market=market,
                time_range=time_range,
                resolution=resolution
            )
            
            return candles
        except ValueError as e:
            logger.error(f"Error fetching historical candles from Drift: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching historical candles from Drift: {e}")
            return []
    
    async def fetch_live_candles(
        self,
        market: str,
        resolution: str
    ) -> StandardizedCandle:
        """Fetch live candle data from Drift."""
        try:
            if not self.data_provider:
                raise ValueError("Data provider not initialized")
            
            self._validate_resolution(resolution)
            self.validate_market(market)
            
            candle = await self.data_provider.fetch_live_candle(
                market=market,
                resolution=resolution
            )
            
            return candle
        except Exception as e:
            logger.error(f"Error fetching live candles from Drift: {e}")
            return None
    
    async def get_markets(self) -> List[str]:
        """Get available markets from Drift."""
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Since get_markets is not async, we don't need to await it
            markets = self.client.get_markets()
            return markets
        except Exception as e:
            logger.error(f"Error getting markets from Drift: {e}")
            return []
    
    def validate_market(self, market: str) -> bool:
        """Validate if a market is supported by Drift."""
        try:
            if not self.client:
                return False
            return market in self.client.market_name_lookup
        except Exception:
            return False 