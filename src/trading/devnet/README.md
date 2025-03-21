# Devnet Testing Module

This module provides tools and utilities for testing on Solana's devnet, including token creation, market simulation, and test trading functionality.

## Features

- SOL airdrop requests
- Test token creation and minting
- Test market creation
- Simulated trading
- Account management
- Multi-wallet support

## CLI Usage

The Devnet module is integrated into the main D3X7-ALGO CLI. Here are the available commands:

### Basic Commands

```bash
# Request SOL Airdrop
d3x7 devnet airdrop --wallet test_wallet [--amount 1.0]

# Create Test Token
d3x7 devnet create-token --name "Test Token" --symbol TEST --wallet creator_wallet [--decimals 9]

# Mint Test Tokens
d3x7 devnet mint --token TEST --amount 1000 --to-wallet recipient --authority-wallet creator_wallet

# Create Test Market
d3x7 devnet create-market --base-token TEST --quote-token USDC --wallet creator_wallet

# Execute Test Trade
d3x7 devnet test-trade --market TEST/USDC --side buy --amount 10 --wallet trading_wallet
```

### Example Usage

1. Setting up a test environment:
```bash
# First, get some SOL
d3x7 devnet airdrop --wallet my_wallet --amount 2.0

# Create a test token
d3x7 devnet create-token --name "My Test Token" --symbol MTT --wallet my_wallet

# Mint some tokens
d3x7 devnet mint --token MTT --amount 1000000 --to-wallet my_wallet --authority-wallet my_wallet

# Create a market
d3x7 devnet create-market --base-token MTT --quote-token USDC --wallet my_wallet
```

2. Testing trading operations:
```bash
# Execute a test buy
d3x7 devnet test-trade --market MTT/USDC --side buy --amount 100 --wallet my_wallet

# Execute a test sell
d3x7 devnet test-trade --market MTT/USDC --side sell --amount 50 --wallet my_wallet
```

## Python API Usage

You can also use the Devnet adapter directly in your Python code:

```python
from d3x7_algo.trading.devnet import DevnetAdapter

async def example():
    adapter = DevnetAdapter()
    await adapter.initialize()
    
    try:
        # Request airdrop
        result = await adapter.request_airdrop(wallet, 1.0)
        print(f"Airdrop received: {result['signature']}")
        
        # Create test token
        token = await adapter.create_test_token(
            "Test Token",
            "TEST",
            9,
            wallet
        )
        print(f"Token created: {token['mint_address']}")
        
        # Create test market
        market = await adapter.create_test_market(
            "TEST",
            "USDC",
            wallet
        )
        print(f"Market created: {market['market_address']}")
        
    finally:
        await adapter.cleanup()
```

## Configuration

Configure Devnet through environment variables or the config file:

```env
SOLANA_NETWORK=devnet
DEVNET_RPC_ENDPOINT=https://api.devnet.solana.com
DEVNET_WALLET_PATH=/path/to/test/wallet.json
```

## Security Notes

While this is a testing environment, it's still important to:
- Keep test wallet keys secure
- Monitor airdrop limits
- Clean up test tokens and markets
- Use separate wallets for testing

## Error Handling

The CLI provides clear error messages for common issues:
- Airdrop limits exceeded
- Invalid wallet configurations
- Network connectivity issues
- Insufficient balance
- Invalid market parameters

## Logging

Comprehensive logging is available:

```python
import logging
logging.getLogger("d3x7_algo.trading.devnet").setLevel(logging.DEBUG)
```

## Dependencies

- Python 3.10+
- solana-py
- anchorpy
- rich (for CLI output)

## Contributing

When adding features:
1. Follow existing code structure
2. Add appropriate tests
3. Update documentation
4. Include example usage
5. Consider cleanup procedures

## Support

For issues and feature requests, please use the issue tracker on our repository.