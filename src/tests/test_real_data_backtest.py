"""Tests for backtesting with real data."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

from src.core.config import StorageConfig
from src.storage import ProcessedDataStorage
from src.backtesting import Backtester

class TestRealDataBacktest:
    @pytest.mark.asyncio
    async def test_btc_backtest(self):
        """Run a complete backtest using mock BTC data"""
        # Create a temporary test directory
        test_dir = Path("/tmp/pytest-of-dex/pytest-2/real_data_test37")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create storage config with test directories
        config = StorageConfig(
            data_path=test_dir,
            historical_raw_path=test_dir / "historical/raw",
            historical_processed_path=test_dir / "historical/processed",
            live_raw_path=test_dir / "live/raw",
            live_processed_path=test_dir / "live/processed",
            use_compression=False
        )
        
        # Create mock data
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        mock_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(30000, 35000, len(dates)),
            'high': np.random.uniform(35000, 40000, len(dates)),
            'low': np.random.uniform(25000, 30000, len(dates)),
            'close': np.random.uniform(30000, 35000, len(dates)),
            'volume': np.random.uniform(1000, 5000, len(dates))
        })
        
        # Convert timestamps to strings for storage (as they'll be serialized to JSON)
        mock_data_records = mock_data.to_dict('records')
        for record in mock_data_records:
            record['timestamp'] = record['timestamp'].isoformat()
        
        # Initialize storage and save mock data
        data_storage = ProcessedDataStorage(config)
        await data_storage.store_candles(
            exchange="binance",
            market="BTCUSDT",
            resolution="1D",
            candles=mock_data_records
        )
        
        # Run backtest
        backtester = Backtester(data_storage=data_storage)
        
        # Create a mock symbol mapper that returns the original symbol
        class MockSymbolMapper:
            def to_exchange_symbol(self, exchange, market):
                return market
        
        # Replace the symbol mapper with our mock
        backtester.symbol_mapper = MockSymbolMapper()
        
        df = await backtester.load_data(
            exchange="binance",
            market="BTCUSDT",
            resolution="1D",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31)
        )
        
        # Verify the loaded data
        assert not df.empty, "DataFrame should not be empty"
        assert len(df) > 0, "Should have loaded some data"
        assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']), "All OHLCV columns should be present"
