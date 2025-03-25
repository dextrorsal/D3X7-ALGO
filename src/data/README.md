# 📊 Data Management

This directory contains the data processing, storage, and management components of the D3X7-ALGO platform.

## 🔍 Overview

The data components provide:
- Historical data fetching
- Real-time data streaming
- Data storage and caching
- Data validation and cleaning
- Market data normalization

## 📁 Structure

```
data/
├── providers/         # Data provider implementations
│   ├── supabase_provider.py  # Supabase data provider
│   └── __init__.py   # Provider initialization
├── __init__.py       # Package initialization
└── README.md         # This file
```

## 🚀 Quick Start

```python
from src.data.providers.supabase_provider import SupabaseProvider
from src.core.models import TimeRange
from datetime import datetime, timedelta

# Initialize provider
provider = SupabaseProvider()

# Set time range
end_time = datetime.now()
start_time = end_time - timedelta(days=30)
time_range = TimeRange(start_time, end_time)

# Fetch and process data
raw_data = await provider.fetch_historical_data("SOL", time_range)
```

## 📥 Data Providers

### Supabase Provider
The Supabase provider offers:
- Historical market data storage
- Real-time data streaming
- Data caching
- Query optimization

Example:
```python
from src.data.providers.supabase_provider import SupabaseProvider

provider = SupabaseProvider()

# Fetch historical data
candles = await provider.fetch_historical_candles(
    market="SOL",
    time_range=time_range,
    interval="1h"
)

# Store new data
await provider.store_candles(
    market="SOL",
    candles=new_candles
)
```

## 🔄 Data Processing

### Features
- Data cleaning and normalization
- Missing data handling
- Outlier detection
- Feature engineering
- Data aggregation

### Example
```python
from src.data.processors import DataProcessor

processor = DataProcessor()
cleaned_data = processor.clean_data(raw_data)
features = processor.engineer_features(cleaned_data)
```

## 💾 Data Storage

### Features
- Efficient data caching
- Multiple storage backends
- Data versioning
- Compression
- Fast retrieval

### Example
```python
from src.data.storage import DataStorage

storage = DataStorage()
await storage.save_candles(market="SOL", candles=processed_data)
cached_data = await storage.get_candles(
    market="SOL",
    time_range=time_range
)
```

## ✅ Data Validation

### Features
- Schema validation
- Data integrity checks
- Quality metrics
- Anomaly detection
- Format verification

### Example
```python
from src.data.validators import DataValidator

validator = DataValidator()
is_valid = validator.validate_candles(candles)
if not is_valid:
    print(validator.get_errors())
```

## 📊 Data Analysis

### Features
- Basic statistics
- Technical indicators
- Market analysis
- Volume profiling
- Correlation analysis

### Example
```python
from src.data.analysis import MarketAnalyzer

analyzer = MarketAnalyzer(candles)
vwap = analyzer.calculate_vwap()
volume_profile = analyzer.get_volume_profile()
```

## 🧪 Testing

```bash
# Run all data tests
python -m pytest tests/data/

# Run specific component tests
python -m pytest tests/data/providers/
```

## 🔄 Integration

### With Exchanges
```python
from src.exchanges.drift import DriftClient
from src.data.providers.supabase_provider import SupabaseProvider

# Fetch from exchange and store
drift_client = DriftClient()
provider = SupabaseProvider()

data = await drift_client.fetch_historical_data("SOL")
await provider.store_data(data)
```

### With Trading System
```python
from src.trading.strategies import Strategy
from src.data.providers.supabase_provider import SupabaseProvider

# Provide data to strategy
provider = SupabaseProvider()
strategy = Strategy()

data = await provider.fetch_historical_data("SOL")
signals = strategy.generate_signals(data)
```

## 📚 Resources

- [Data Management Guide](docs/data/management.md)
- [Provider Integration Guide](docs/data/providers.md)
- [Storage Guide](docs/data/storage.md)
- [Validation Guide](docs/data/validation.md) 