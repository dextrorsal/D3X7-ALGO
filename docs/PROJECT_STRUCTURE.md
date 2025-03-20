# Ultimate Data Fetcher - Project Structure

## Overview

The Ultimate Data Fetcher is a sophisticated trading system focused on Solana-based DEX interactions, particularly with Drift Protocol and Jupiter Aggregator. This document reflects the current state of the project structure.

## Core Directory Structure

```
ultimate_data_fetcher/
├── config/                    # Configuration files
│   ├── wallets/             # Wallet configurations
│   │   ├── .keys.json          # API keys and secrets
│   │   ├── .indicator.json     # Trading indicator settings
│   │   └── .exchanges.json     # Exchange configurations
│   │
│   ├── src/                    # Source code
│   │   ├── exchanges/         # Exchange integrations
│   │   │   ├── auth/         # Authentication handlers
│   │   │   ├── drift.py      # Drift Protocol implementation
│   │   │   ├── jup.py        # Jupiter Protocol implementation
│   │   │   ├── binance.py    # Binance exchange integration
│   │   │   ├── coinbase.py   # Coinbase exchange integration
│   │   │   ├── bitget.py     # Bitget exchange integration
│   │   │   ├── base.py       # Base exchange classes
│   │   │   └── __init__.py   # Exchange module initialization
│   │   │
│   │   ├── core/            # Core functionality 
│   │   │
│   │   ├── utils/           # Utility functions
│   │   │   ├── wallet/     # Wallet management utilities
│   │   │   │   ├── sol_wallet.py        # Solana wallet implementation
│   │   │   │   ├── wallet_manager.py    # Wallet management system
│   │   │   │   ├── sol_rpc.py          # RPC connection handling
│   │   │   │   ├── wallet_cli.py       # CLI wallet interface
│   │   │   │   ├── check_all_wallets.py # Wallet verification
│   │   │   │   ├── show_all_wallets.py  # Wallet display utility
│   │   │   │   └── phantom_tools/      # Phantom wallet utilities
│   │   │   │       ├── export_for_phantom.py
│   │   │   │       ├── phantom_export.py
│   │   │   │       └── convert_keypair_to_base58.py
│   │   │   │
│   │   │   │   ├── strategy/   # Trading strategy utilities
│   │   │   │   ├── indicators/ # Technical indicators
│   │   │   │   ├── improved_cli.py    # Enhanced CLI functionality
│   │   │   │   ├── logging_wrapper.py # Logging utilities
│   │   │   │   ├── log_setup.py      # Logging configuration
│   │   │   │   └── time_utils.py     # Time management utilities
│   │   │   │
│   │   ├── trading/         # Trading components
│   │   │   ├── drift/      # Drift Protocol trading
│   │   │   │   ├── account_manager.py  # Account management
│   │   │   │   └── drift_adapter.py   # Protocol interface
│   │   │   │
│   │   │   ├── jup/        # Jupiter Protocol trading
│   │   │   ├── devnet/     # Devnet trading environment
│   │   │   ├── mainnet/    # Mainnet trading setup
│   │   │   └── tests/      # Trading-specific tests
│   │   │
│   │   ├── backtesting/     # Backtesting framework
│   │   │
│   │   ├── critical_tests/  # Critical system tests
│   │   │
│   │   ├── pytests/         # PyTest modules
│   │   │
│   │   ├── storage/         # Data storage utilities
│   │   │
│   │   ├── base.py         # Base classes
│   │   ├── crypto_cli.py   # CLI interface
│   │   └── ultimate_fetcher.py # Main implementation
│   │
│   ├── scripts/         # Utility scripts
│   │   ├── trading/    # Trading execution scripts
│   │   │   └── trade.py       # Main trading execution
│   │   │
│   │   ├── fetching/   # Data fetching scripts
│   │   │   ├── fetch.py         # Basic fetch functionality
│   │   │   ├── fetch_all.py     # Comprehensive data fetching
│   │   │   ├── fetch_btc_data.py # Bitcoin data fetching
│   │   │   └── test_fetch.py    # Fetch testing
│   │   │
│   │   └── shell/      # Shell script utilities
│   │       ├── run_sqlite_conda.sh  # Database setup
│   │       ├── use_driftpy.sh      # Drift environment
│   │       └── use_lenv.sh         # Local environment
│   │
│   ├── Entry Points
│   │   ├── check_jup_balance.py  # Jupiter balance checker
│   │   ├── check_jupiter.py      # Jupiter functionality tests
│   │   ├── manage_drift.py       # Drift management interface
│   │   ├── fetch_data.py         # Data fetching entry
│   │   └── trade_live.py         # Live trading entry
│   │
│   └── Configuration
│       ├── .env              # Environment variables
│       ├── requirements.txt  # Project dependencies
│       ├── setup.py         # Package setup
│       └── pytest.ini       # PyTest configuration
```

## Key Implementations

### 1. Exchange Integrations (`src/exchanges/`)
Currently implemented exchanges:
- Drift Protocol (`drift.py`) - Solana perpetuals
- Jupiter (`jup.py`) - Solana DEX aggregator
- Binance (`binance.py`) - CEX integration
- Coinbase (`coinbase.py`) - CEX integration
- Bitget (`bitget.py`) - CEX integration

### 2. Configuration Management (`config/`)
- Wallet configurations in `wallets/`
- Exchange API configurations in `.exchanges.json`
- Indicator settings in `.indicator.json`
- Secure key storage in `.keys.json`

### 3. Entry Points
Main application interfaces:
- `check_jup_balance.py`: Jupiter balance monitoring
- `check_jupiter.py`: Jupiter protocol testing
- `manage_drift.py`: Drift protocol management
- `fetch_data.py`: Data collection interface
- `trade_live.py`: Live trading execution

### 4. Utility Components (`src/utils/`)
Core utility modules providing essential functionality:

#### Wallet Management (`utils/wallet/`)
- `sol_wallet.py`: Core Solana wallet implementation
- `wallet_manager.py`: Multi-wallet management system
- `sol_rpc.py`: RPC connection and interaction
- Wallet Tools:
  - Balance checking (`check_all_wallets.py`)
  - Wallet visualization (`show_all_wallets.py`)
  - Phantom wallet integration tools

#### General Utilities
- `improved_cli.py`: Enhanced command-line interface
- `logging_wrapper.py` & `log_setup.py`: Logging system
- `time_utils.py`: Time management and synchronization
- Strategy and indicator utilities for trading analysis

### 5. Trading Components (`src/trading/`)
Trading system implementation:

#### Protocol-Specific Trading
- **Drift Protocol** (`trading/drift/`):
  - Account management and position handling
  - Protocol interaction and order execution
  - Custom trading strategies

- **Jupiter Protocol** (`trading/jup/`):
  - Swap execution and routing
  - Price discovery and optimization
  - Liquidity management

#### Environment Management
- `devnet/`: Development and testing environment
- `mainnet/`: Production trading setup
- `tests/`: Trading-specific test suites

### 6. Script Components (`src/scripts/`)
Utility scripts for various operations:

#### Trading Scripts (`scripts/trading/`)
- `trade.py`: Main trading execution script
  - Order execution
  - Position management
  - Trading flow control

#### Data Fetching (`scripts/fetching/`)
- `fetch.py`: Core fetching functionality
- `fetch_all.py`: Comprehensive data collection
- `fetch_btc_data.py`: Bitcoin-specific data
- Testing and validation scripts

#### Shell Utilities (`scripts/shell/`)
- Database setup and management
- Environment configuration
- Development utilities

## Development Status

This is a living document that reflects the current state of the project. The structure above represents the actual implementation, not an idealized version. As the project evolves, this document should be updated to maintain accuracy.

### Active Development Areas
- Drift Protocol integration
- Jupiter Protocol integration
- Exchange implementations
- Testing infrastructure

### Current Focus
- Devnet testing and validation
- Exchange integration refinement
- Core functionality development