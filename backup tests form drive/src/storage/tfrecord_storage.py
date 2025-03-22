"""
TFRecord storage handling for Ultimate Data Fetcher.
Provides efficient storage for machine learning training data.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Union
import pandas as pd
import tensorflow as tf
import torch
from torch.utils.data import Dataset, DataLoader

from ..core.models import StandardizedCandle
from ..core.exceptions import StorageError
from ..core.config import StorageConfig
from .tfrecord import convert_to_tfrecord, TFRecordDataset, get_tf_dataset

logger = logging.getLogger(__name__)


class TFRecordStorage:
    """Handles storage of data in TFRecord format for machine learning."""
    
    def __init__(self, config: StorageConfig):
        """Initialize TFRecord storage with configuration."""
        self.base_path = config.historical_processed_path / "tfrecords"
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized TFRecord storage at {self.base_path}")
    
    def _get_folder_path(self, exchange: str, market: str, resolution: str) -> Path:
        """
        Generate folder path for a given exchange, market, and resolution.
        Creates a structure like processed/tfrecords/exchange/market/resolution/
        """
        folder_path = self.base_path / exchange / market / resolution
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path
    
    async def convert_candles_to_tfrecord(self, exchange: str, market: str, resolution: str, 
                                         candles: Union[List[StandardizedCandle], pd.DataFrame],
                                         records_per_file: int = 1000):
        """
        Convert candle data to TFRecord format.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            candles: List of StandardizedCandle objects or DataFrame
            records_per_file: Number of records per TFRecord file
        """
        try:
            # Create output directory
            output_dir = self._get_folder_path(exchange, market, resolution)
            
            # Convert candles to DataFrame if they're StandardizedCandle objects
            if isinstance(candles, list) and candles and isinstance(candles[0], StandardizedCandle):
                df = pd.DataFrame([c.to_dict() for c in candles])
            elif isinstance(candles, pd.DataFrame):
                df = candles
            else:
                raise ValueError("Candles must be a list of StandardizedCandle objects or a DataFrame")
            
            # Create a temporary directory to store CSV files
            temp_dir = output_dir / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Save DataFrame to CSV
            csv_path = temp_dir / f"{exchange}_{market}_{resolution}.csv"
            df.to_csv(csv_path, index=False)
            
            # Convert to TFRecord
            convert_to_tfrecord(str(temp_dir), str(output_dir), records_per_file)
            
            # Clean up temporary files
            csv_path.unlink(missing_ok=True)
            
            logger.info(f"Converted {len(df)} candles to TFRecord format at {output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert candles to TFRecord: {e}")
            raise StorageError(f"TFRecord conversion failed: {e}")
    
    def get_pytorch_dataloader(self, exchange: str, market: str, resolution: str, 
                              batch_size: int = 32, shuffle: bool = True,
                              num_workers: int = 4, transform=None):
        """
        Get a PyTorch DataLoader for the TFRecord files.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            batch_size: Batch size for DataLoader
            shuffle: Whether to shuffle the data
            num_workers: Number of worker processes for DataLoader
            transform: Optional transform to apply to data
            
        Returns:
            torch.utils.data.DataLoader: DataLoader for the TFRecord files
        """
        try:
            tfrecord_dir = self._get_folder_path(exchange, market, resolution)
            dataset = TFRecordDataset(str(tfrecord_dir), transform=transform)
            
            return DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=shuffle,
                num_workers=num_workers,
                pin_memory=True,
                prefetch_factor=2
            )
            
        except Exception as e:
            logger.error(f"Failed to create PyTorch DataLoader: {e}")
            raise StorageError(f"DataLoader creation failed: {e}")
    
    def get_tensorflow_dataset(self, exchange: str, market: str, resolution: str, batch_size: int = 32):
        """
        Get a TensorFlow Dataset for the TFRecord files.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            batch_size: Batch size for the dataset
            
        Returns:
            tf.data.Dataset: TensorFlow dataset
        """
        try:
            tfrecord_dir = self._get_folder_path(exchange, market, resolution)
            return get_tf_dataset(str(tfrecord_dir), batch_size)
            
        except Exception as e:
            logger.error(f"Failed to create TensorFlow Dataset: {e}")
            raise StorageError(f"TensorFlow Dataset creation failed: {e}") 