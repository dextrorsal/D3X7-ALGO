# src/data/manager.py

import os
import pandas as pd
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import data providers
from .providers.base_provider import BaseDataProvider
from .providers.csv_provider import CsvDataProvider

class DataManager:
    """
    Manages data providers and selects the appropriate one based on environment settings.
    """
    
    def __init__(self):
        """Initialize data manager with providers based on environment variables"""
        # Initialize CSV provider (always available)
        self.csv_provider = CsvDataProvider()
        
        # Initialize Supabase provider if credentials exist
        self.supabase_provider = None
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if supabase_url and supabase_key:
            # Only import if credentials are available
            from .providers.supabase_provider import SupabaseProvider
            try:
                self.supabase_provider = SupabaseProvider()
                print("Initialized Supabase provider")
            except Exception as e:
                print(f"Error initializing Supabase provider: {e}")
        
        # Default provider based on environment variable
        self.default_provider_type = os.getenv('DEFAULT_DATA_PROVIDER', 'csv')
    
    async def load_candles(self, exchange: str, market: str, resolution: str, 
                         start_time: datetime, end_time: datetime, 
                         provider_type: Optional[str] = None) -> pd.DataFrame:
        """
        Load candles from the specified provider.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            start_time: Start time
            end_time: End time
            provider_type: Optional provider type ('csv' or 'supabase')
            
        Returns:
            DataFrame with OHLCV data
        """
        # Determine which provider to use
        provider_type = provider_type or self.default_provider_type
        
        if provider_type.lower() == 'supabase' and self.supabase_provider:
            df = await self.supabase_provider.load_candles(
                exchange, market, resolution, start_time, end_time
            )
        else:
            # Default to CSV
            df = await self.csv_provider.load_candles(
                exchange, market, resolution, start_time, end_time
            )
        
        # Standardize column names for indicators
        if not df.empty:
            # Ensure timestamp is datetime if it exists as column
            if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    async def store_candles(self, exchange: str, market: str, resolution: str, 
                          candles: list, provider_type: Optional[str] = None) -> bool:
        """
        Store candles using the specified provider.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            candles: List of candles
            provider_type: Optional provider type ('csv' or 'supabase')
            
        Returns:
            Success status
        """
        # Determine which provider to use
        provider_type = provider_type or self.default_provider_type
        
        success = False
        
        if provider_type.lower() == 'supabase' and self.supabase_provider:
            success = await self.supabase_provider.store_candles(
                exchange, market, resolution, candles
            )
        else:
            # For CSV, we use the ProcessedDataStorage directly
            from ..storage.processed import ProcessedDataStorage
            from ..core.config import StorageConfig
            
            storage = ProcessedDataStorage(StorageConfig())
            await storage.store_candles(exchange, market, resolution, candles)
            success = True
        
        return success