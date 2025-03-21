# 🤖 D3X7-ALGO Trading Platform

A sophisticated algorithmic trading platform for Solana crypto markets with advanced trading capabilities, devnet testing tools, and ML-based strategy integration.

<div align="center">
  <img src="https://solana.com/_next/image?url=%2F_next%2Fstatic%2Fmedia%2Flogotype.e4df684f.svg&w=256&q=75" alt="Solana Logo" width="400"/>
</div>

## 📚 Table of Contents

- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Development Guide](#-development-guide)
- [Security Features](#-security-features)
- [Logging](#-logging)
- [Contributing](#-contributing)
- [License](#-license)

## 🏗️ Architecture

D3X7-ALGO is designed around several key systems that work together to provide a complete trading solution.

### 🔄 Core Components

#### 📈 Trading Engine
The heart of D3X7-ALGO, providing trading capabilities across multiple Solana DEXes:
- **Drift Protocol**: Full integration for perpetual futures trading
- **Jupiter**: Optimal token swapping with the best prices across Solana
- **Serum/OpenBook**: Direct market access for limit orders
- **Position Management**: Track, monitor, and manage all positions

#### 🔐 Wallet Management System
Located in `src/utils/wallet/`, providing comprehensive and secure wallet handling:
- **Encryption**: Military-grade encryption for wallet keypairs
- **Multi-Wallet Support**: Manage main wallets and trading sub-accounts
- **Balance Management**: Monitor and manage SOL and token balances
- **Testing Tools**: Airdrop functionality for devnet testing

#### 🧪 Devnet Testing Framework
Located in `src/trading/devnet/`, providing a complete suite for safe, risk-free testing:
- **Token Operations**: Create and mint test tokens
- **Market Operations**: Create and interact with test markets
- **Transaction Simulation**: Test trades without risking real funds
- **Compatibility Layer**: Bridges different Solana SDK versions

#### 🧠 ML Trading System
Located in `src/ml/`, providing machine learning capabilities:
- **Strategy Models**: Predictive models for market behavior
- **Data Processing**: Clean and prepare data for model training
- **Backtesting**: Test strategies against historical data
- **Inference Engine**: Real-time prediction for live trading

## 📁 Project Structure

```
D3X7-ALGO/
├── src/                    # Main source code
│   ├── cli/                # Command-line interface
│   │   ├── main.py         # Main entry point for CLI
│   │   ├── base.py         # Base classes and utilities for CLI
│   │   └── trading/        # Trading commands submodule
│   │       ├── devnet_cli.py   # Commands for devnet testing
│   │       ├── drift_cli.py    # Commands for Drift protocol
│   │       ├── jup_cli.py      # Commands for Jupiter swaps
│   │       └── wallet_cli.py   # Commands for wallet management
│   │
│   ├── trading/            # Core trading functionality
│   │   ├── devnet/         # Devnet testing components
│   │   │   ├── devnet_adapter.py   # Adapter for devnet operations
│   │   │   ├── devnet_cli_test.py  # Standalone testing tool
│   │   │   └── solana_shim.py      # SDK compatibility layer
│   │   │
│   │   ├── drift/          # Drift protocol integration
│   │   │   ├── drift_adapter.py    # Adapter for Drift operations
│   │   │   ├── drift_client.py     # Client for Drift protocol
│   │   │   └── management/          # Position management tools
│   │   │       ├── position_monitor.py  # Monitor positions
│   │   │       └── risk_manager.py      # Manage trading risk
│   │   │
│   │   ├── jup/            # Jupiter aggregator integration
│   │   │   ├── jup_adapter.py      # Adapter for Jupiter
│   │   │   └── quote_service.py    # Price quote service
│   │   │
│   │   └── mainnet/        # Mainnet-specific components
│   │       ├── market_maker.py     # Market making strategies
│   │       └── trade_executor.py   # Execute trade orders
│   │
│   ├── utils/              # Utility functions and helpers
│   │   ├── wallet/         # Wallet management utilities
│   │   │   ├── wallet_manager.py   # Manage multiple wallets
│   │   │   ├── sol_wallet.py       # Solana wallet implementation
│   │   │   └── encryption.py       # Secure encryption tools
│   │   │
│   │   ├── config/         # Configuration utilities
│   │   │   ├── config_manager.py   # Load and manage config
│   │   │   └── defaults.py         # Default configuration values
│   │   │
│   │   └── helpers/        # General helper utilities
│   │       ├── time_utils.py       # Time-related helpers
│   │       ├── logging_utils.py    # Logging configuration
│   │       └── math_utils.py       # Math and conversion helpers
│   │
│   └── ml/                 # Machine learning components
│       ├── models/         # ML model definitions
│       │   ├── lstm.py           # LSTM network model
│       │   └── transformer.py    # Transformer model
│       │
│       ├── data/           # Data processing for ML
│       │   ├── processors.py     # Data preprocessing tools
│       │   └── features.py       # Feature engineering
│       │
│       └── inference/      # Model inference for live trading
│           ├── predictor.py      # Make predictions from models
│           └── ensemble.py       # Combine multiple models
│
├── scripts/                # Utility scripts
│   ├── setup.sh            # Environment setup script
│   └── install_deps.sh     # Install dependencies
│
├── config/                 # Configuration files
│   └── default_config.ini  # Default configuration
│
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test fixtures
│
└── docs/                   # Documentation
    ├── api/                # API documentation
    ├── guides/             # User guides
    └── examples/           # Example code and usage
```

### 📂 Folder Descriptions

#### 🖥️ `src/cli/` - Command Line Interface
This folder contains all the code for the command-line interface that users interact with.
- `main.py`: The entry point for all CLI commands, processes arguments and calls appropriate handlers
- `base.py`: Contains shared functionality for all CLI commands like argument parsing
- `trading/`: Sub-commands specifically for trading operations
  - `devnet_cli.py`: Commands for devnet testing (creating tokens, airdrops, etc.)
  - `drift_cli.py`: Commands for interacting with Drift Protocol
  - `jup_cli.py`: Commands for performing Jupiter swaps
  - `wallet_cli.py`: Commands for wallet management (balance checking, transfers)

#### 💱 `src/trading/` - Trading Functionality
The core trading functionality broken down by platform or purpose.
- `devnet/`: Components for testing on Solana's devnet
  - `devnet_adapter.py`: Main interface for devnet operations
  - `devnet_cli_test.py`: Standalone script for testing devnet features
  - `solana_shim.py`: Compatibility layer between different Solana SDK versions
- `drift/`: Integration with Drift Protocol for perpetual futures
  - `drift_adapter.py`: Interface for Drift operations
  - `drift_client.py`: Client implementation for Drift Protocol
  - `management/`: Tools for managing positions
- `jup/`: Integration with Jupiter for token swaps
  - `jup_adapter.py`: Interface for Jupiter operations
  - `quote_service.py`: Service for getting price quotes
- `mainnet/`: Components specific to mainnet operations
  - `market_maker.py`: Market making strategy implementation
  - `trade_executor.py`: Execute trade orders on mainnet

#### 🛠️ `src/utils/` - Utility Functions
Helper functions and utilities used throughout the application.
- `wallet/`: Wallet management utilities
  - `wallet_manager.py`: Manage multiple wallets
  - `sol_wallet.py`: Solana wallet implementation
  - `encryption.py`: Tools for securely encrypting wallet data
- `config/`: Configuration utilities
  - `config_manager.py`: Load and manage configuration
  - `defaults.py`: Default configuration values
- `helpers/`: General helper utilities
  - `time_utils.py`: Time-related helper functions
  - `logging_utils.py`: Logging configuration
  - `math_utils.py`: Math and conversion helpers

#### 🧠 `src/ml/` - Machine Learning
Components for machine learning-based trading strategies.
- `models/`: ML model definitions
  - `lstm.py`: Long Short-Term Memory network model
  - `transformer.py`: Transformer-based model
- `data/`: Data processing for ML
  - `processors.py`: Tools for data preprocessing
  - `features.py`: Feature engineering functions
- `inference/`: Make predictions from trained models
  - `predictor.py`: Prediction tools
  - `ensemble.py`: Combine multiple models

## 🚀 Quick Start

### 📥 Installation

Setting up D3X7-ALGO is simple with these steps:

```bash
# Clone the repository
git clone https://github.com/yourusername/D3X7-ALGO.git
cd D3X7-ALGO

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package and dependencies
pip install -e .

# Set up your configuration
cp .env.example .env
# Open .env in your favorite text editor and add your settings
```

### 🔧 Requirements

- Python 3.9 or higher
- Solana CLI tools (for wallet creation/management)
- Internet connection (for RPC access)

## 📋 Usage Examples

Here are some common tasks you can perform with D3X7-ALGO:

### 🧪 Devnet Testing

The devnet testing tool lets you create and test tokens without using real funds:

```bash
# Request SOL airdrop on devnet (free test SOL)
python src/trading/devnet/devnet_cli_test.py airdrop --wallet MAIN --amount 2.0

# Create a test token with your details
python src/trading/devnet/devnet_cli_test.py create-token --name "GameCoin" --symbol "GAME" --wallet MAIN

# Mint some tokens to your wallet
python src/trading/devnet/devnet_cli_test.py mint --token GAME --amount 1000 --to-wallet MAIN

# Create a trading market for your token (advanced)
python src/trading/devnet/devnet_cli_test.py create-market --base GAME --quote USDC --wallet MAIN
```

### 📊 Trading Operations

Once configured, you can perform trades across different DEXes:

```bash
# Check your wallet balance
d3x7 wallet balance

# Place a Drift perpetual futures trade
d3x7 trade drift position --market SOL-PERP --size 1.0 --side long

# Execute a token swap via Jupiter (best price across Solana)
d3x7 trade jupiter swap --from SOL --to USDC --amount 1.0

# Close a position
d3x7 trade drift close --market SOL-PERP
```

### 🔐 Wallet Management

Manage your wallets securely:

```bash
# List all connected wallets
d3x7 wallet list

# Create a new wallet
d3x7 wallet create --name TRADING

# Transfer funds between wallets
d3x7 wallet transfer --from MAIN --to TRADING --amount 1.0 --token SOL
```

## ⚙️ Configuration

### 📝 Environment Variables

Create a `.env` file with your configuration (shown with example values):

```env
# Solana RPC Endpoints
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_MAINNET_RPC_URL=https://api.mainnet-beta.solana.com

# Wallet File Paths (regular JSON key files)
MAIN_KEY_PATH=/home/user/.config/solana/keys/id.json
KP_KEY_PATH=/home/user/.config/solana/keys/kp_trade.json
AG_KEY_PATH=/home/user/.config/solana/keys/ag_trade.json

# Encrypted Wallet Paths (optional, for extra security)
MAIN_EC_PATH=/home/user/.config/solana/trading/main.enc
KP_EC_PATH=/home/user/.config/solana/trading/kp_trade.enc
AG_EC_PATH=/home/user/.config/solana/trading/ag_trade.enc

# Wallet Password (for encrypted wallets)
WALLET_PASSWORD=your_secure_password

# Trading Parameters
DEFAULT_SLIPPAGE=0.5
MAX_POSITION_SIZE=100
RISK_PERCENTAGE=2.0

# Logging Configuration
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=logs/trading.log
```

### 🛠️ Configuration Files

Additional configuration options can be set in `config/default_config.ini`:

```ini
[general]
; General application settings
debug_mode = false
auto_update = true

[trading]
; Trading specific settings
default_market = SOL-PERP
trading_enabled = true
risk_management = true

[security]
; Security settings
encrypt_wallets = true
timeout_minutes = 30
require_confirmation = true
```

## 🔬 Development Guide

### ✨ Key Features

#### 🔒 Secure Wallet Management
D3X7-ALGO includes a robust wallet management system:
- **Encrypted Storage**: All wallet keypairs can be stored with AES-256 encryption
- **Multiple Wallet Support**: Use different wallets for different strategies or risk levels
- **Safety Checks**: Prevents accidental trades above your risk tolerance

#### 🧪 Devnet Testing
Before risking real funds, test everything on devnet:
- **Test Tokens**: Create your own tokens with custom parameters
- **Test Markets**: Create markets between any tokens
- **No Financial Risk**: Use free airdropped SOL for all tests

#### 🤖 ML-Based Trading
Leverage machine learning for smarter trades:
- **Predictive Models**: LSTM and Transformer models trained on market data
- **Backtesting**: Test strategies against historical price action
- **Live Inference**: Make predictions on current market conditions
- **Feature Engineering**: Extract meaningful features from raw market data

### 🧩 Adding New Features

#### 🔄 New Exchange Support
To add support for a new exchange or protocol:

1. Create a new adapter in appropriate `src/trading/` subdirectory
   ```python
   # Example: src/trading/new_protocol/new_protocol_adapter.py
   class NewProtocolAdapter:
       def __init__(self, config_path=None):
           # Initialize adapter
           pass
           
       async def connect(self):
           # Connect to the protocol
           pass
           
       async def place_order(self, market, side, amount, price=None):
           # Implement order placement
           pass
   ```

2. Implement the required interface methods
3. Add to CLI command structure for user access

#### 📈 New Trading Strategies
To implement a new trading strategy:

1. Create a strategy in `src/strategies/`
   ```python
   # Example: src/strategies/mean_reversion.py
   class MeanReversionStrategy:
       def __init__(self, window_size=20):
           self.window_size = window_size
           
       def should_enter(self, price_data):
           # Determine if we should enter a position
           pass
           
       def should_exit(self, position, price_data):
           # Determine if we should exit a position
           pass
   ```

2. Integrate with execution engine
3. Add appropriate CLI commands

## 🔐 Security Features

D3X7-ALGO takes security seriously:

- **Encrypted Wallet Storage**: Wallets can be stored with strong encryption
- **API Key Security**: Secure handling of API keys and secrets
- **Transaction Simulation**: Preview transaction effects before execution
- **Slippage Controls**: Set maximum allowed slippage to prevent bad trades
- **Position Limits**: Set maximum position sizes to limit risk
- **Timeout Protection**: Automatic timeout after period of inactivity
- **Error Recovery**: Graceful handling of connection issues and errors

## 📝 Logging

Comprehensive logging helps with debugging and monitoring:

- **Trading Operations**: All trades are logged with details
- **Wallet Management**: Track wallet operations
- **Error Tracking**: Detailed error logs for troubleshooting
- **Performance Metrics**: Track execution times and system performance
- **Configurable Levels**: Set logging verbosity (DEBUG, INFO, WARNING, ERROR)

Example log output:
```
2025-03-21 10:15:32,874 - INFO - Successfully connected to Solana devnet
2025-03-21 10:15:33,125 - INFO - Wallet MAIN balance: 5.0 SOL
2025-03-21 10:15:35,412 - INFO - Created token GameCoin (GAME) with mint address 82z1otgmy6VYq84YTmqHVwcegTAWpi3Ysp3XtN8W6V6
2025-03-21 10:15:38,766 - INFO - Minted 1000 GAME to wallet MAIN
```

## 🤝 Contributing

We welcome contributions to D3X7-ALGO!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure nothing broke
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### 📋 Contribution Guidelines

- Follow the coding style of the project
- Add tests for new features
- Update documentation to reflect changes
- Keep pull requests focused on a single feature or bug fix

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📊 Project Status

D3X7-ALGO is under active development. Check the `CHANGELOG.md` for version updates and changes.