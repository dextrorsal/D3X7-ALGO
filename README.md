# Ultimate Data Fetcher

A high-performance framework for cryptocurrency data collection, analysis, and strategy backtesting across multiple exchanges, built with a modular monolith architecture.

## 🌟 Features

- Multi-exchange support (Binance, Coinbase, Drift)
- Historical and real-time data collection with standardized formats
- Advanced technical indicators and strategy backtesting
- Standardized data models across exchanges
- Comprehensive risk analysis tools
- Modular architecture with clear separation of concerns
- Enhanced symbol mapping between exchanges
- Test mode support for reliable testing without API access

## 🏗️ Architecture

The Ultimate Data Fetcher follows a modular monolith architecture with clear separation between components:

1. **Data Acquisition Layer**: Exchange handlers implement standardized interfaces for various exchanges with resilient error handling and rate limiting
2. **Transformation Pipeline**: Standardization of candle data across diverse exchange formats enables unified downstream processing
3. **Strategy Composition Layer**: Indicator framework allows for algorithm composition and backtest evaluation
4. **Execution Layer**: Trade execution is separated from signal generation, following industry best practices

This architecture provides an optimal balance between architectural cleanliness and development velocity.

## 📁 Project Structure

```
ultimate_data_fetcher/
├── src/
│   ├── exchanges/          # Exchange-specific implementations
│   │   ├── base.py         # Base exchange handler interface
│   │   ├── binance.py      # Binance exchange handler
│   │   ├── binance_mock.py # Mock Binance handler for testing
│   │   ├── coinbase.py     # Coinbase exchange handler
│   │   ├── drift.py        # Drift exchange handler
│   │   └── drift_mock.py   # Mock Drift handler for testing
│   ├── storage/            # Data storage implementations
│   │   ├── raw.py          # Raw data storage
│   │   ├── processed.py    # Processed data storage
│   │   ├── live.py         # Live data storage
│   │   ├── tfrecord.py     # TFRecord utilities
│   │   └── __init__.py     # Storage initialization
│   ├── core/               # Core functionality and configurations
│   │   ├── config.py       # Configuration management
│   │   ├── models.py       # Data models
│   │   ├── exceptions.py   # Custom exceptions
│   │   └── symbol_mapper.py # Symbol mapping between exchanges
│   ├── utils/              # Helper functions and utilities
│   │   ├── time_utils.py   # Time-related utilities
│   │   ├── indicators/     # Technical indicators
│   │   │   ├── base_indicator.py # Base indicator class
│   │   │   ├── supertrend.py     # Supertrend indicator
│   │   │   ├── knn.py           # K-Nearest Neighbors indicator
│   │   │   └── lorentzian.py    # Lorentzian classifier
│   │   └── strategy/       # Strategy implementations
│   │       └── base.py     # Base strategy class
│   ├── backtesting/        # Backtesting framework
│   │   ├── backtester.py   # Core backtesting engine
│   │   ├── optimizer.py    # Strategy parameter optimization
│   │   └── risk_analysis.py # Monte Carlo simulation and risk analysis
│   ├── critical_tests/     # Critical functionality tests
│   │   └── test_critical_functionality.py # Critical tests
│   └── tests/              # Regular test suite
│       ├── test_exchanges.py      # Exchange handler tests
│       ├── test_symbol_mapper.py  # Symbol mapper tests
│       ├── test_core.py           # Core functionality tests
│       └── test_backtester.py     # Backtesting tests
├── config/                 # Configuration files
│   └── indicator_settings.json # Indicator configuration
├── data/                   # Data files
│   ├── historical/         # Historical data
│   │   ├── raw/            # Raw historical data
│   │   │   └── binance/    # Binance exchange data
│   │   │       ├── BTCUSDT/ # Bitcoin/USDT pair
│   │   │       │   ├── 1/  # 1-minute timeframe
│   │   │       │   ├── 5/  # 5-minute timeframe
│   │   │       │   └── 15/ # 15-minute timeframe
│   │   │       └── SOLUSDT/ # Solana/USDT pair
│   │   └── processed/      # Processed historical data
│   └── live/               # Live data
│       ├── raw/            # Raw live data
│       └── processed/      # Processed live data
├── logs/                   # Log files
├── fetch.py                # Main entry point script
├── requirements.txt        # Dependencies
├── TESTING.md              # Testing documentation
├── module-structure.md     # Architecture documentation
└── README                  # Project documentation
```

### Key Components

- **exchanges/** - Exchange handlers with standardized interfaces
  - `base.py` - Base exchange handler interface
  - `binance.py`, `coinbase.py`, `drift.py` - Exchange-specific implementations
  - `binance_mock.py`, `drift_mock.py` - Mock handlers for testing

- **storage/** - Data storage implementations
  - Raw data storage
  - Processed OHLCV data
  - Real-time data handling
  - TFRecord support

- **core/** - Core functionality
  - Configuration management
  - Error handling
  - Rate limiting
  - Symbol mapping

- **backtesting/** - Backtesting framework
  - Backtesting engine
  - Strategy optimization
  - Risk analysis

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.11+ required
python --version

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

1. **Fetch Historical Data**
```bash
python fetch.py historical \
    --exchange binance \
    --markets BTC-USDT,ETH-USDT \
    --resolution 1h \
    --days 30
```

2. **Live Data Streaming**
```bash
python fetch.py live \
    --exchange coinbase \
    --markets BTC-USD,ETH-USD \
    --resolution 1m \
    --interval 60
```

3. **Run Backtesting**
```bash
python backtest.py \
    --strategy supertrend \
    --market BTC-USDT \
    --timeframe 1D \
    --capital 10000 \
    --start-date 2023-01-01
```

### CLI Reference

#### Historical Data Fetching
```bash
python fetch.py historical [OPTIONS]

Options:
  --exchange TEXT     Exchange name (binance/coinbase/drift)
  --markets TEXT     Comma-separated market pairs
  --resolution TEXT  Timeframe (1m/5m/15m/1h/4h/1D)
  --days INTEGER    Number of days to fetch
  --start-date TEXT Optional start date (YYYY-MM-DD)
  --end-date TEXT   Optional end date (YYYY-MM-DD)
```

#### Live Data Streaming
```bash
python fetch.py live [OPTIONS]

Options:
  --exchange TEXT     Exchange name
  --markets TEXT     Comma-separated market pairs
  --resolution TEXT  Timeframe
  --interval INTEGER Fetch interval in seconds
```

## 📊 Data Storage

Data is stored in a structured format:
```
data/
├── raw/
│   ├── binance/
│   ├── coinbase/
│   └── drift/
└── processed/
    ├── ohlcv/
    └── indicators/
```

## 🔧 Configuration

Create a `config.yaml` in the project root:

```yaml
exchanges:
  binance:
    api_key: "your_api_key"
    api_secret: "your_api_secret"
  coinbase:
    api_key: "your_api_key"
    api_secret: "your_api_secret"
  drift:
    program_id: "your_program_id"

storage:
  base_path: "data/"
  compression: true

logging:
  level: "INFO"
  file: "ultimate_data_fetcher.log"
```

## 🧪 Testing

The project includes a comprehensive test suite with both regular and critical tests. See [TESTING.md](TESTING.md) for detailed information on running tests.

Quick test commands:

```bash
# Run all tests
PYTHONPATH=/home/dex/ultimate_data_fetcher/src python3 -m pytest src/tests/ -v -p no:anchorpy | cat

# Run critical tests
PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest -v src/critical_tests/ -p no:anchorpy --tb=short | cat

# Run tests with specific market format
PYTHONPATH=/home/dex/ultimate_data_fetcher/src pytest src/critical_tests/ -p no:anchorpy --market-format=binance
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](docs/README.md)
- [Issue Tracker](https://github.com/yourusername/crypto-data-fetcher/issues)
- [Change Log](CHANGELOG.md)

# Jupiter Ultra API Integration

This project demonstrates a successful integration with Jupiter's Ultra API for optimal token swaps on Solana. The implementation includes both mainnet and devnet support, with comprehensive testing on the devnet using SOL-TEST pairs.

## Features

### 1. Jupiter Ultra API Integration
- Uses the latest Ultra API endpoint (`https://api.jup.ag/ultra/v1`)
- Supports both mainnet and devnet environments
- Implements optimal swap routing with price impact consideration
- Handles RFQ and Aggregator swap types

### 2. Token Support
- **Mainnet**:
  - SOL (`So11111111111111111111111111111111111111112`)
  - USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- **Devnet**:
  - SOL (`So11111111111111111111111111111111111111112`)
  - TEST (`7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs`)

### 3. Price Data Integration
- Uses Jupiter's Price API v4 for efficient price data
- Supports real-time price updates
- Implements price impact calculation

### 4. Trading Features
- Market price fetching
- Order execution via Ultra API
- Account balance management
- Slippage control
- Transaction signing and submission

## Components

### 1. Jupiter Adapter (`src/trading/jup/jup_adapter.py`)
- Core adapter for Jupiter Ultra API integration
- Handles API requests and responses
- Manages wallet connections
- Implements swap execution logic

### 2. Exchange Handler (`src/exchanges/jup.py`)
- Price data fetching and standardization
- Candle data simulation for strategy testing
- Integration with the broader exchange handler system

### 3. Live Trader (`src/trading/jup/live_trader.py`)
- Live trading implementation using Ultra API
- Trade execution and management
- Position tracking
- Trade logging

### 4. Live Strategy (`src/trading/jup/jup_live_strat.py`)
- Strategy implementation using Ultra API
- Price data processing
- Signal generation
- Indicator calculations

## Testing

### Ultra API Test Results
Successfully tested the following functionality:
1. Connection to Jupiter Ultra API
2. Price data fetching
3. Order quote retrieval
4. Swap execution (devnet)

Test output for SOL-TEST swap on devnet:
```
✓ Connected to Jupiter on devnet
✓ Got order for 0.1 SOL -> TEST
  Request ID: c069ad58-48b1-4948-9d6b-cf5e470584bc
  Input amount: 100000000 SOL
  Output amount: 669121 TEST
  Price impact: 0%
  Swap type: aggregator
✓ Order includes transaction to sign
✓ Successfully tested Jupiter Ultra API order functionality
```

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ultimate_data_fetcher
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run tests:
```bash
python -m src.trading.tests.jup.test_ultra_api
```

## Usage

### Basic Swap Example
```python
from src.trading.jup.jup_adapter import JupiterAdapter

async def example():
    # Initialize adapter
    adapter = JupiterAdapter(network="devnet")
    
    # Get quote for 0.1 SOL to TEST
    quote = await adapter.get_ultra_quote(
        market="SOL-TEST",
        input_amount=0.1
    )
    
    # Execute swap
    result = await adapter.execute_swap(
        market="SOL-TEST",
        input_amount=0.1
    )
    
    print(f"Swap executed: {result['signature']}")
```

### Price Data Example
```python
from src.exchanges.jup import JupiterHandler
from src.core.config import Config

async def example():
    # Initialize handler
    config = Config({"name": "jupiter"})
    handler = JupiterHandler(config)
    
    # Get current SOL/USDC price
    candle = await handler.fetch_live_candles(
        market="SOL-USDC",
        resolution="1m"
    )
    
    print(f"Current SOL price: ${candle.close}")
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.