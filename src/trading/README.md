# D3X7 Trading System

A comprehensive trading system for Solana-based DEXs, focusing on Drift Protocol and Jupiter integration. This system enables sophisticated trading strategies with both spot and perpetual futures markets.

## 🏗 Architecture Overview

```
trading/
├── drift/               # Drift Protocol Integration
│   ├── account_manager.py  # Account & balance management
│   ├── drift_adapter.py    # Core protocol interface
│   └── README.md
├── devnet/             # Development & Testing
│   ├── drift_auth.py      # Auth & client setup
│   └── README.md
├── jup/                # Jupiter Integration
│   ├── jup_adapter.py     # Aggregator interface
│   └── README.md
└── tests/             # Test Suites
    ├── drift/         # Mainnet tests
    ├── devnet/        # Devnet tests
    └── README.md
```

## 🚀 Quick Start

### 1. Installation
```bash
# Clone repository
git clone https://github.com/yourusername/ultimate_data_fetcher.git
cd ultimate_data_fetcher

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Set up environment variables
export HELIUS_RPC_URL="your_helius_rpc_url"
export WALLET_PATH="~/.config/solana/id.json"

# For devnet testing
export DEVNET_RPC_URL="https://api.devnet.solana.com"
export DEVNET_WALLET_PATH="~/.config/solana/devnet.json"
```

### 3. Basic Usage
```python
from src.trading.drift.account_manager import DriftAccountManager
from src.trading.jup.jup_adapter import JupiterAdapter

# Initialize Drift account manager
manager = DriftAccountManager()
await manager.setup()

# Check balances
await manager.show_balances()

# Make a deposit
await manager.deposit_sol(amount=1.0)
```

## 🔧 Core Components

### 1. Drift Protocol Integration
- **Account Management**: Deposits, withdrawals, balance tracking
- **Market Operations**: Spot and perpetual futures trading
- **Risk Management**: Position tracking, collateral management

```python
# Example: Trading on Drift
from src.trading.drift.drift_adapter import DriftAdapter

adapter = DriftAdapter()
await adapter.connect()

# Place a perpetual order
await adapter.place_perp_order(
    market="SOL-PERP",
    side="BUY",
    amount=1.0,
    price=50.0
)
```

### 2. Jupiter Integration
- **Token Swaps**: Best execution routing
- **Price Discovery**: Real-time market data
- **Strategy Implementation**: Trading logic and execution

```python
# Example: Token swap via Jupiter
from src.trading.jup.jup_adapter import JupiterAdapter

jupiter = JupiterAdapter()
await jupiter.swap_tokens(
    input_token="SOL",
    output_token="USDC",
    amount=1.0
)
```

## 🔐 Security Features

1. **Environment Separation**
   - Strict separation of mainnet and devnet environments
   - Dedicated wallets for each environment
   - Environment-specific configuration

2. **Transaction Safety**
   - Confirmation prompts for critical operations
   - Balance verification before transactions
   - Automatic transaction parameter optimization

3. **Error Handling**
   ```python
   try:
       await manager.deposit_sol(amount)
   except InsufficientFundsError:
       logger.error("Insufficient funds")
   finally:
       await manager.drift_client.unsubscribe()
   ```

## 🧪 Testing Framework

### Environment-Based Testing
```bash
# Run mainnet tests
python -m pytest src/trading/tests/drift/

# Run devnet tests
python -m pytest src/trading/tests/devnet/
```

### Test Categories
1. **Integration Tests**: End-to-end workflows
2. **Component Tests**: Individual feature testing
3. **Safety Tests**: Transaction and balance verification

## 📊 Supported Markets

### Perpetual Markets
- SOL-PERP (index: 0)
- BTC-PERP (index: 1)
- ETH-PERP (index: 2)

### Spot Markets
- SOL-USDC (index: 0)
- BTC-USDC (index: 1)
- ETH-USDC (index: 2)

## 🛠 Development Workflow

1. **Local Development**
   ```bash
   # Set up devnet environment
   solana config set --url devnet
   solana airdrop 2  # Get test SOL
   ```

2. **Testing**
   ```bash
   # Run specific test suite
   python -m pytest src/trading/tests/devnet/test_drift_auth.py -v
   ```

3. **Deployment**
   - Verify environment variables
   - Run full test suite
   - Monitor initial transactions

## 📚 Documentation Structure

Each component has detailed documentation:
- [`/drift/README.md`](drift/README.md): Drift Protocol integration
- [`/devnet/README.md`](devnet/README.md): Development environment
- [`/jup/README.md`](jup/README.md): Jupiter integration
- [`/tests/README.md`](tests/README.md): Testing framework

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Add project root to PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:/path/to/ultimate_data_fetcher"
   ```

2. **Connection Issues**
   - Verify RPC endpoints
   - Check wallet configuration
   - Ensure sufficient SOL for fees

3. **Transaction Failures**
   - Check account balances
   - Verify market status
   - Monitor compute unit usage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Update documentation
5. Submit pull request

## 📝 Best Practices

1. **Code Organization**
   - Follow directory structure
   - Use appropriate test environment
   - Maintain documentation

2. **Security**
   - Never commit private keys
   - Use environment variables
   - Implement proper error handling

3. **Testing**
   - Write comprehensive tests
   - Use devnet for development
   - Monitor resource usage

## 🔄 Integration Points

### Drift ↔ Jupiter
- Price comparison
- Liquidity optimization
- Cross-protocol strategies

### Mainnet ↔ Devnet
- Strategy validation
- Risk management
- Performance testing

## 📈 Performance Optimization

1. **Transaction Optimization**
   - Compute unit management
   - Priority fee adjustment
   - Batch operations

2. **Resource Management**
   - Connection pooling
   - Subscription handling
   - Memory optimization

## 🔗 Dependencies

```bash
# Core dependencies
pip install driftpy anchorpy solana-py solders

# Testing dependencies
pip install pytest pytest-asyncio pytest-timeout

# Development tools
pip install black isort mypy
```

## 🏷️ Version History

- v1.0.0: Initial release
  - Drift Protocol integration
  - Jupiter integration
  - Testing framework
  - Documentation

## 📞 Support

- Review component documentation
- Check test examples
- Follow troubleshooting guide
- Submit issues on GitHub