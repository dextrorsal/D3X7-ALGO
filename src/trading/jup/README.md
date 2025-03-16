# Trading Jupiter Directory

This directory contains components for interacting with Jupiter Aggregator, Solana's leading DEX aggregator for optimal token swaps and trading.

## Directory Structure

```
jup/
├── __init__.py          - Module exports
├── jup_adapter.py       - Jupiter API integration (16KB)
├── live_trader.py       - Live trading implementation (20KB)
├── jup_live_strat.py    - Live trading strategy (4.7KB)
└── paper_report.py      - Paper trading reporting (4.3KB)
```

## Component Details

### 1. `jup_adapter.py`

Core adapter for Jupiter DEX Aggregator integration.

**Key Features:**
- Token swap execution
- Market price fetching
- Route optimization
- Account balance management

**Supported Markets:**
```python
# Base Pairs
- SOL-USDC
- BTC-USDC
- ETH-USDC

# Reverse Pairs
- USDC-SOL
- USDC-BTC
- USDC-ETH
```

**Usage Example:**
```python
from src.trading.jup import JupiterAdapter

async def example():
    adapter = JupiterAdapter(config_path="config.json")
    await adapter.connect()
    
    # Get market price
    price = await adapter.get_market_price("SOL-USDC")
    
    # Execute swap
    result = await adapter.execute_swap(
        market="SOL-USDC",
        input_amount=1.0,
        slippage_bps=50
    )
```

### 2. `live_trader.py`

Implementation of live trading functionality using Jupiter.

**Key Features:**
- Real-time order execution
- Market monitoring
- Position management
- Risk controls
- Performance tracking

**Usage Example:**
```python
from src.trading.jup import LiveTrader

async def example():
    trader = LiveTrader(config_path="config.json")
    await trader.initialize()
    
    # Start trading
    await trader.start_trading()
```

### 3. `jup_live_strat.py`

Live trading strategy implementation.

**Key Features:**
- Strategy definition
- Signal generation
- Entry/exit rules
- Risk management
- Performance metrics

### 4. `paper_report.py`

Paper trading report generation and analysis.

**Key Features:**
- Trade history tracking
- Performance metrics calculation
- Risk analysis
- Report generation
- Strategy evaluation

## Integration Points

### With Drift Protocol
- Compatible with Drift's spot markets
- Supports arbitrage opportunities
- Price comparison functionality

### With Solana Network
- RPC connection management
- Transaction handling
- Account management

## Best Practices

1. **Error Handling:**
   ```python
   try:
       await adapter.execute_swap(market, amount)
   except Exception as e:
       logger.error(f"Swap failed: {e}")
   finally:
       await adapter.disconnect()
   ```

2. **Slippage Management:**
   - Default slippage: 50 bps (0.5%)
   - Adjust based on market conditions
   - Monitor execution prices

3. **Resource Management:**
   - Clean up connections
   - Handle rate limits
   - Monitor API usage

## Configuration

1. **Required Setup:**
   - Solana RPC endpoint
   - Wallet keypair
   - Jupiter API endpoints
   - Market configurations

2. **API Endpoints:**
   - Quote API: `https://quote-api.jup.ag/v6`
   - Swap API: `https://quote-api.jup.ag/v6/swap`

## Token Support

1. **Major Tokens:**
   ```
   - SOL:  So11111111111111111111111111111111111111112
   - USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
   - BTC:  9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E
   - ETH:  7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs
   ```

2. **Decimal Precision:**
   - SOL: 9 decimals
   - USDC: 6 decimals
   - BTC: 8 decimals
   - ETH: 8 decimals

## Security Considerations

1. **Transaction Safety:**
   - Verify slippage limits
   - Check output amounts
   - Validate signatures

2. **API Security:**
   - Handle rate limits
   - Secure API keys
   - Monitor usage

3. **Wallet Security:**
   - Secure keypair storage
   - Transaction signing
   - Balance verification

## Dependencies

- `solana`: Solana web3 library
- `base58`: Address encoding
- `requests`: API communication
- `asyncio`: Async operations
- `logging`: Error tracking

## Notes

- Uses Jupiter v6 API
- Supports versioned transactions
- Implements best execution routing
- Handles token decimal conversions
- Provides detailed logging