# Trading Module

This module contains all trading-related components for the Ultimate Data Fetcher project, implementing a comprehensive trading system for Solana-based DEXs.

## Directory Structure

```
trading/
├── devnet/              # Devnet testing environment
│   ├── drift_auth.py    # Drift authentication
│   └── README.md        # Devnet documentation
├── drift/               # Drift Protocol integration
│   ├── account_manager.py
│   ├── drift_adapter.py
│   └── README.md        # Drift documentation
├── jup/                 # Jupiter Aggregator integration
│   ├── jup_adapter.py   # Core Jupiter interface
│   ├── live_trader.py   # Live trading engine
│   ├── jup_live_strat.py
│   └── README.md        # Jupiter documentation
├── mainnet/             # Mainnet operations
│   ├── sol_wallet.py    # Wallet management
│   └── README.md        # Mainnet documentation
└── tests/               # Test suites
    ├── devnet/          # Devnet-specific tests
    ├── drift/           # Drift protocol tests
    ├── jup/             # Jupiter tests
    └── README.md        # Testing documentation
```

## Core Components

### 1. Drift Protocol Integration (`/drift`)
- **Account Management:** Deposits, withdrawals, PnL tracking
- **Market Operations:** Spot and perpetual futures trading
- **Risk Management:** Position tracking, collateral management
- **Supported Markets:** SOL-PERP, BTC-PERP, ETH-PERP, and spot pairs

### 2. Jupiter Aggregator (`/jup`)
- **Token Swaps:** Best execution routing
- **Price Discovery:** Real-time market data
- **Strategy Implementation:** Trading logic and execution
- **Supported Pairs:** SOL-USDC, BTC-USDC, ETH-USDC (bi-directional)

### 3. Mainnet Operations (`/mainnet`)
- **Wallet Management:** Secure key handling
- **Transaction Signing:** Order execution
- **Security:** Environment-based configuration
- **Balance Tracking:** Token and SOL management

### 4. Devnet Testing (`/devnet`)
- **Authentication:** Test environment setup
- **Account Management:** Test account operations
- **Market Testing:** Order simulation
- **Balance Verification:** Test fund management

## Quick Start

```python
# Mainnet Trading
from src.trading import LiveTrader, DriftAdapter, JupiterAdapter, SolanaWallet

# Initialize components
wallet = SolanaWallet(keypair_path="~/.config/solana/id.json")
drift = DriftAdapter()
jupiter = JupiterAdapter()
trader = LiveTrader(jupiter)

# Devnet Testing
from src.trading import DriftHelper, DriftAccountManager

# Setup test environment
helper = DriftHelper()
manager = DriftAccountManager()
```

## Configuration

### Environment Variables
```bash
# Required
SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"
PRIVATE_KEY_PATH="/path/to/keypair.json"

# Optional
JUPITER_API_KEY="your_api_key"  # If using Pro API
```

### Network Selection
```python
# Mainnet
drift_client = DriftAdapter(env="mainnet")

# Devnet
drift_client = DriftAdapter(env="devnet")
```

## Best Practices

1. **Security:**
   - Never commit private keys
   - Use environment variables
   - Implement proper error handling

2. **Testing:**
   - Always test on devnet first
   - Use test accounts for development
   - Run full test suite before deployment

3. **Performance:**
   - Monitor slippage carefully
   - Implement proper error handling
   - Clean up resources after use

## Integration Points

### Drift ↔ Jupiter
- Price comparison for arbitrage
- Liquidity optimization
- Cross-protocol strategies

### Mainnet ↔ Devnet
- Strategy validation
- Risk management testing
- Performance optimization

## Error Handling

```python
try:
    await trader.execute_strategy()
except InsufficientFundsError:
    logger.error("Insufficient funds for trade")
except SlippageError:
    logger.error("Slippage exceeded threshold")
finally:
    await trader.cleanup()
```

## Development Workflow

1. **Local Development:**
   - Use devnet environment
   - Run tests frequently
   - Monitor resource usage

2. **Testing:**
   - Unit tests in `/tests`
   - Integration tests per component
   - Performance benchmarking

3. **Deployment:**
   - Verify configurations
   - Check security settings
   - Monitor initial transactions

## Architecture

The module follows a layered architecture:

1. **Protocol Layer:**
   - Drift Protocol integration
   - Jupiter Aggregator integration
   - Wallet management

2. **Strategy Layer:**
   - Trading logic
   - Signal generation
   - Risk management

3. **Execution Layer:**
   - Order management
   - Transaction handling
   - Balance tracking

4. **Testing Layer:**
   - Component validation
   - Integration testing
   - Performance monitoring

## Documentation

Each directory contains its own detailed README:
- `/devnet/README.md`: Devnet testing guide
- `/drift/README.md`: Drift protocol integration
- `/jup/README.md`: Jupiter trading system
- `/mainnet/README.md`: Mainnet operations
- `/tests/README.md`: Testing framework

## Contributing

1. Fork the repository
2. Create feature branch
3. Follow code style
4. Add tests
5. Submit pull request

## Support

- Check individual component READMEs
- Review test documentation
- Follow best practices guide