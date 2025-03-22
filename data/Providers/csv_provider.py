# src/data/providers/csv_provider.py

import os
import pandas as pd
from datetime import datetime
from .base_provider import BaseDataProvider
from ...storage.processed import ProcessedDataStorage
from ...core.config import StorageConfig

class CsvDataProvider(BaseDataProvider):
    """Data provider that loads from CSV files"""
    
    def __init__(self):
        """Initialize using environment variables"""
        # You might want to set StorageConfig parameters from environment variables
        # For example:
        base_path = os.getenv('DATA_BASE_PATH', 'data')
        use_compression = os.getenv('USE_COMPRESSION', 'False').lower() == 'true'
        
        config = StorageConfig()
        # Override config with environment variables if needed
        if base_path:
            config.historical_processed_path = base_path
        
        config.use_compression = use_compression
        
        self.storage = ProcessedDataStorage(config)
    
    async def load_candles(self, exchange: str, market: str, resolution: str, 
                          start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Load candles from CSV storage"""
        return await self.storage.load_candles(exchange, market, resolution, start_time, end_time)
    
    async def store_candles(self, exchange: str, market: str, resolution: str, 
                          candles: list) -> bool:
        """Store candles to CSV storage"""
        try:
            await self.storage.store_candles(exchange, market, resolution, candles)
            return True
        except Exception as e:
            print(f"Error storing candles to CSV: {e}")
            return False