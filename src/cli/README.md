# D3X7-ALGO CLI

A unified command-line interface for the D3X7-ALGO trading platform. This CLI provides a centralized way to interact with all components of the system including data fetching, wallet management, and trading operations.

## 📥 Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/D3X7-ALGO.git
cd D3X7-ALGO
```

2. Install the CLI:
```bash
# Install in development mode
pip install -e src/cli

# Or install globally
pip install src/cli
```

3. Verify installation:
```bash
d3x7 --help
```

### Configuration

1. Create a `.env` file in your working directory:
```bash
cp src/cli/example.env .env
```

2. Edit the `.env` file with your settings:
```bash
nano .env  # or use your preferred editor
```

## 🏗️ Architecture

The CLI is organized into modular components:

```
src/cli/
├── __init__.py          # Package initialization
├── base.py              # Base CLI component class
├── main.py              # Main CLI entry point
├── data/                # Data fetching components
│   ├── __init__.py
│   └── fetch.py         # Historical and live data fetching
├── trading/            # Trading components
│   ├── __init__.py
│   ├── drift.py        # Drift protocol integration
│   └── jupiter.py      # Jupiter protocol integration
└── utils/             # Utility components
    ├── __init__.py
    └── wallet.py      # Wallet management
```

Each component inherits from `BaseCLI` which provides common functionality for:
- Argument parsing
- Logging setup
- Configuration management
- Error handling

## 🚀 Usage

### Basic Commands

```bash
# Show help
d3x7 --help

# Enable debug logging
d3x7 --debug <command>

# Use custom config file
d3x7 --config path/to/config.env <command>
```

### Data Operations

```bash
# Fetch historical data
d3x7 data fetch --mode historical \
    --markets BTC-PERP ETH-PERP \
    --resolution 1D \
    --start-time "2024-01-01" \
    --end-time "2024-01-31"

# Stream live data
d3x7 data fetch --mode live \
    --markets SOL-PERP \
    --resolution 15
```

### Wallet Management

```bash
# List all wallets
d3x7 wallet list

# Create new wallet
d3x7 wallet create TRADING --keypair path/to/keypair.json

# Check wallet balance
d3x7 wallet balance MAIN --tokens

# Export wallet keys
d3x7 wallet export MAIN --output backup.json
```

### Trading Operations

#### Drift Protocol

```bash
# Open position
d3x7 trade drift position \
    --market SOL-PERP \
    --size 1.0 \
    --side long \
    --leverage 2.0

# Monitor positions
d3x7 trade drift monitor \
    --wallet MAIN \
    --interval 5
```

#### Jupiter Protocol

```bash
# Get swap quote
d3x7 trade jupiter quote \
    --market SOL-USDC \
    --amount 1.0

# Execute swap
d3x7 trade jupiter swap \
    --market SOL-USDC \
    --amount 1.0 \
    --slippage 0.5
```

## 🔧 Configuration

The CLI uses a `.env` configuration file by default. You can specify a different config file using the `--config` flag.

Example configuration:
```env
# Network settings
NETWORK=mainnet
RPC_URL=https://api.mainnet-beta.solana.com

# Wallet settings
ENABLE_ENCRYPTION=true
WALLET_PASSWORD=your-secure-password

# Trading settings
MAX_POSITION_SIZE=1000
DEFAULT_LEVERAGE=1.0
```

## 🛡️ Security Features

- Encrypted wallet storage
- Slippage protection for swaps
- Position size limits
- Leverage restrictions
- Automatic position monitoring

## 🔍 Logging

The CLI uses enhanced logging with different levels:
- `INFO`: Default level, shows important operations
- `DEBUG`: Detailed information (enable with `--debug`)
- `ERROR`: Error messages and stack traces

Logs include:
- Timestamp
- Operation details
- Transaction signatures
- Error messages

## 🤝 Contributing

To add a new CLI component:

1. Create a new module in the appropriate directory
2. Inherit from `BaseCLI`
3. Implement required methods:
   - `setup()`: Initialize resources
   - `cleanup()`: Clean up resources
   - `add_arguments()`: Define command arguments
   - `handle_command()`: Handle command execution
4. Register the component in `main.py`

Example:
```python
from ..base import BaseCLI

class NewComponentCLI(BaseCLI):
    async def setup(self) -> None:
        # Initialize resources
        pass

    async def cleanup(self) -> None:
        # Clean up resources
        pass

    def add_arguments(self, parser) -> None:
        # Add command arguments
        pass

    async def handle_command(self, args) -> None:
        # Handle command execution
        pass
```

## 📚 Error Handling

The CLI provides consistent error handling across all components:
- Human-readable error messages
- Debug information with `--debug`
- Proper cleanup on errors
- Graceful handling of interrupts

## 🔄 Dependencies

- Python 3.8+
- `asyncio` for async operations
- `argparse` for command parsing
- `logging` for log management
- Component-specific dependencies in `requirements.txt` 