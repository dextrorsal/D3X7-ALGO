# D3X7-ALGO Drift Trading Module

This module provides a comprehensive interface for trading on the Drift Protocol, including both CLI and GUI interfaces.

## Features

- Position Management (Long/Short)
- Real-time Position Monitoring
- Account Health Tracking
- Subaccount Management
- GUI Trading Interface
- Security Validations
- Risk Management

## CLI Usage

The Drift module is integrated into the main D3X7-ALGO CLI. Here are the available commands:

### Basic Commands

```bash
# Launch GUI Trading Interface
d3x7 drift gui --wallet my_wallet [--dark-mode]

# List Available Wallets
d3x7 drift list

# Check Balance and Positions
d3x7 drift balance --wallet my_wallet [--subaccount 0]

# List Subaccounts
d3x7 drift subaccounts [--wallet my_wallet]
```

### Trading Commands

```bash
# Open a Position
d3x7 drift position --market SOL-PERP --size 1.0 --side long --leverage 2.0 [--reduce-only]

# Close a Position
d3x7 drift close --market SOL-PERP [--size 0.5]

# Monitor Positions
d3x7 drift monitor --markets SOL-PERP,BTC-PERP --interval 5

# Check Position Health
d3x7 drift health --market SOL-PERP
```

## GUI Features

The GUI interface (`drift_qt_gui.py`) provides:

- Real-time price charts
- Order book visualization
- Position management
- Account overview
- Trade history
- Dark/Light theme support

## Examples

Check the `examples/` directory for sample scripts:

1. Basic Trading Example:
```python
from d3x7_algo.trading.drift import DriftAdapter

async def basic_trade():
    adapter = DriftAdapter()
    await adapter.initialize()
    
    # Open a long position
    await adapter.open_position(
        market="SOL-PERP",
        size=1.0,
        side="long",
        leverage=2.0
    )
```

2. Position Monitoring Example:
```python
from d3x7_algo.trading.drift import DriftPositionMonitor

async def monitor_positions():
    monitor = DriftPositionMonitor()
    await monitor.start(["SOL-PERP", "BTC-PERP"])
    
    # Monitor will emit events for position changes
    monitor.on_position_update(lambda pos: print(f"Position updated: {pos}"))
```

## Security Features

The module includes built-in security features:

- Position size limits
- Leverage restrictions
- Slippage protection
- Liquidation warnings
- Rate limiting

## Configuration

Configure the Drift module through environment variables or the config file:

```env
DRIFT_MAX_POSITION_SIZE=1000
DRIFT_MAX_LEVERAGE=5
DRIFT_SLIPPAGE_TOLERANCE=0.01
```

## Dependencies

- Python 3.10+
- PyQt6 (for GUI)
- driftpy
- anchorpy
- solana-py

## Contributing

When adding new features:

1. Follow the existing code structure
2. Add appropriate tests
3. Update documentation
4. Include example usage
5. Consider security implications

## Error Handling

The module provides detailed error messages for common issues:

- Insufficient margin
- Invalid position sizes
- Network connectivity issues
- Rate limit exceeded
- Invalid market symbols

## Logging

Comprehensive logging is available at different levels:

```python
import logging
logging.getLogger("d3x7_algo.trading.drift").setLevel(logging.DEBUG)
```

## Support

For issues and feature requests, please use the issue tracker on our repository.