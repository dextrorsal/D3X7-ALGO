# src/data/providers/base_provider.py

import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

class BaseDataProvider(ABC):
    """Base class for all data providers"""
    
    @abstractmethod
    async def load_candles(self, exchange: str, market: str, resolution: str, 
                          start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Load candles for the given parameters"""
        pass

# src/data/providers/csv_provider.py

import pandas as pd
from datetime import datetime
from .base_provider import BaseDataProvider
from ...storage.processed import ProcessedDataStorage
from ...core.config import StorageConfig

class CsvDataProvider(BaseDataProvider):
    """Data provider that loads from CSV files"""
    
    def __init__(self, config=None):
        """Initialize with optional config"""
        if config:
            self.config = config
        else:
            self.config = StorageConfig()
        self.storage = ProcessedDataStorage(self.config)
    
    async def load_candles(self, exchange: str, market: str, resolution: str, 
                          start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Load candles from CSV storage"""
        return await self.storage.load_candles(exchange, market, resolution, start_time, end_time)