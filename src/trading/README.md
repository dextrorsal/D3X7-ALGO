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
├── mainnet/           # Production Trading
│   ├── mainnet_trade.py     # Main trading interface
│   ├── security_limits.py   # Trading security controls
│   ├── drift_position_monitor.py  # Position monitoring
│   └── README.md
├── security/          # Security Framework
│   └── security_manager.py  # Core security controls
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

## Testing

### Overview
The D3X7-ALGO trading system uses a comprehensive testing framework to ensure reliability and safety. Tests are organized by type and functionality in the `tests/` directory.

### Running Tests

The easiest way to run tests is using our test runner script:

```bash
# Run all tests
./src/trading/run_tests.py

# Run specific test types
./src/trading/run_tests.py --unit        # Only unit tests
./src/trading/run_tests.py --integration # Only integration tests
./src/trading/run_tests.py --devnet     # Only devnet tests
./src/trading/run_tests.py --mainnet    # Only mainnet tests

# Additional options
./src/trading/run_tests.py --coverage    # Generate coverage report
./src/trading/run_tests.py --verbose     # Show detailed output
```

### Test Categories

#### Unit Tests
These tests check individual components in isolation:

1. **Security Tests** (`tests/unit/security/`)
   - Validates trading limits
   - Tests risk management
   - Checks emergency controls
   Example:
   ```python
   def test_security_limits():
       limits = SecurityLimits()
       assert limits.check_trade_size(100) is True
   ```

2. **Drift Protocol Tests** (`tests/unit/drift/`)
   - Tests account operations
   - Verifies market interactions
   - Checks authentication flows
   Example:
   ```python
   @pytest.mark.asyncio
   async def test_drift_order():
       result = await drift_adapter.place_order(...)
       assert result.status == "success"
   ```

3. **Jupiter Protocol Tests** (`tests/unit/jup/`)
   - Tests swap operations
   - Verifies route optimization
   - Checks price calculations
   Example:
   ```python
   def test_route_optimization():
       routes = jup_adapter.get_routes(...)
       assert len(routes) > 0
   ```

#### Integration Tests
These tests verify multiple components working together:

1. **Devnet Tests** (`tests/integration/devnet/`)
   - Complete trading workflows
   - System component integration
   - Performance validation
   Example:
   ```python
   @pytest.mark.asyncio
   async def test_complete_trade_flow():
       # Setup wallet and market
       # Execute trade
       # Verify results
   ```

2. **Mainnet Tests** (`tests/integration/mainnet/`)
   - Production environment checks
   - Live system monitoring
   - Real-world performance testing

### Test Fixtures

Our `conftest.py` provides shared test components:

```python
def test_example(wallet_manager, security_limits):
    # Your test code here
    pass
```

Available fixtures:
- `event_loop`: For async testing
- `wallet_manager`: Handles wallet operations
- `security_limits`: Trading safety controls
- `drift_adapter`: Drift protocol interface
- `jup_adapter`: Jupiter protocol interface
- `mock_market_config`: Test market settings
- `mock_prices`: Test price data

### Writing Tests

#### Basic Test Structure
```python
import pytest
from src.trading.security import SecurityLimits

def test_my_feature():
    # 1. Setup
    security = SecurityLimits()
    
    # 2. Action
    result = security.check_limit(100)
    
    # 3. Verify
    assert result is True
```

#### Async Test Structure
```python
import pytest

@pytest.mark.asyncio
async def test_async_feature(drift_adapter):
    # Test async operations
    result = await drift_adapter.get_position()
    assert result is not None
```

### Best Practices

1. **Test Independence**
   - Each test should work on its own
   - Clean up after your tests
   - Don't rely on other test results

2. **Security First**
   - Always test with safe limits
   - Check error cases
   - Verify security controls

3. **Performance**
   - Keep tests fast
   - Use mocks for external services
   - Clean up resources

### Troubleshooting

If tests fail, check these common issues:

1. **Connection Issues**
   - Verify network connectivity
   - Check RPC endpoints
   - Confirm API access

2. **Slow Tests**
   - Look for infinite loops
   - Check timeout settings
   - Verify cleanup operations

3. **Resource Problems**
   - Monitor memory usage
   - Check for unclosed connections
   - Verify cleanup code runs

### Important Notes

- Use devnet for development
- Keep mainnet tests minimal
- Update tests when changing code
- Document complex test scenarios
- Ask for help if stuck!

### Contributing

When adding new tests:
1. Follow the existing directory structure
2. Add clear docstrings
3. Include error cases
4. Update documentation if needed

Need help? Check the development team chat or raise an issue!

## 🔐 Security Framework

### Core Security Manager (`security/`)
The security framework provides comprehensive protection for trading operations:

1. **Risk Management**
   - Position size limits
   - Leverage controls
   - Exposure tracking
   - Loss thresholds

2. **Trade Validation**
   - Pre-trade checks
   - Post-trade verification
   - Emergency controls
   - Volume monitoring

3. **System Protection**
   - Rate limiting
   - Error handling
   - Automatic shutdown
   - Alert system

### Security Implementation
```python
from src.trading.security.security_manager import SecurityManager

# Initialize security manager
security = SecurityManager()

# Configure limits
security.set_position_limits({
    "SOL-PERP": 5.0,
    "BTC-PERP": 0.1
})

# Validate trade
try:
    await security.validate_trade(market="SOL-PERP", size=1.0)
except SecurityLimitError:
    logger.error("Trade exceeds security limits")
```

## 🚀 Mainnet Trading

### Overview
The mainnet directory contains production-ready trading components with comprehensive security controls and monitoring capabilities.

### Components

1. **Trading Interface** (`mainnet_trade.py`)
   - Drift perpetual trades
   - Jupiter token swaps
   - Position monitoring
   - Security integration

2. **Security Controls** (`security_limits.py`)
   - Position size limits
   - Risk management
   - Emergency controls
   - Trade validation

3. **Position Monitor** (`drift_position_monitor.py`)
   - Real-time tracking
   - PnL monitoring
   - Risk metrics
   - Performance analytics

### Usage Examples

```python
# Execute Drift trade
python3 mainnet_trade.py drift --market SOL-PERP --size 1.0 --side buy

# Execute Jupiter swap
python3 mainnet_trade.py jupiter --market SOL-USDC --amount 1.0

# Monitor positions
python3 mainnet_trade.py monitor
```

### Security Configuration
```json
{
    "max_position_size": {
        "SOL-PERP": 2.0,
        "BTC-PERP": 0.05
    },
    "max_leverage": {
        "SOL-PERP": 3,
        "BTC-PERP": 2
    },
    "daily_volume_limit": 5.0
}
```

### Monitoring and Alerts

1. **Position Monitoring**
   - Size limit alerts
   - Leverage warnings
   - PnL thresholds
   - Volume tracking

2. **System Health**
   - Connection status
   - Trade execution
   - Error tracking
   - Performance metrics

3. **Emergency Controls**
   - Automatic shutdown
   - Manual override
   - Reset procedures
   - Incident logging