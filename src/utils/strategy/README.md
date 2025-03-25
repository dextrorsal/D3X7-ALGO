# 🎯 Trading Strategies

This directory contains the trading strategy implementations used in the D3X7-ALGO platform.

## 📋 Overview

The strategy module provides:
- Base strategy interface
- Solana spot trading strategies
- Machine learning based strategies
- Multi-timeframe segmented strategies
- Multi-indicator combination strategies

## 📁 Structure

```
strategy/
├── base.py                      # Base strategy interface
├── sol_spot.py                  # Solana spot trading
├── ml_stratagies.py            # Machine learning strategies
├── segmented.py                # Multi-timeframe strategies
├── multi_indicator_strategy.py  # Combined indicator strategies
└── __init__.py                 # Package initialization
```

## 🔧 Components

### Base Strategy
The foundation for all trading strategies, defining common interfaces and utilities.

```python
from src.utils.strategy.base import BaseStrategy

class CustomStrategy(BaseStrategy):
    def __init__(self, market, indicators):
        super().__init__()
        self.market = market
        self.indicators = indicators
    
    async def generate_signals(self, data):
        # Your signal generation logic
        pass
```

### Solana Spot Trading
Specialized strategies for spot trading on Solana markets.

```python
from src.utils.strategy.sol_spot import SolSpotStrategy

# Initialize spot strategy
strategy = SolSpotStrategy(
    market="SOL",
    indicators=[RSI(14), MACD()],
    risk_params={
        "max_position": 10,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 4.0
    }
)

# Generate trading signals
signals = await strategy.generate_signals(market_data)
```

### Machine Learning Strategies
ML-powered trading strategies using trained models.

```python
from src.utils.strategy.ml_stratagies import MLStrategy

# Initialize ML strategy
strategy = MLStrategy(
    model_path="models/sol_classifier.pkl",
    features=["rsi", "macd", "bb", "adx"],
    market="SOL"
)

# Train model
await strategy.train(historical_data)

# Generate predictions
signals = await strategy.predict(market_data)
```

### Segmented Trading
Multi-timeframe strategies that combine signals from different intervals.

```python
from src.utils.strategy.segmented import SegmentedStrategy

# Initialize segmented strategy
strategy = SegmentedStrategy(
    timeframes=["1m", "5m", "15m"],
    sub_strategies=[
        SolSpotStrategy(market="SOL"),
        MLStrategy(market="SOL")
    ],
    weights=[0.3, 0.7]
)

# Generate combined signals
signals = await strategy.generate_signals(market_data)
```

### Multi-Indicator Strategy
Strategies that combine multiple technical indicators.

```python
from src.utils.strategy.multi_indicator_strategy import MultiIndicatorStrategy

# Initialize multi-indicator strategy
strategy = MultiIndicatorStrategy(
    market="SOL",
    indicators={
        "trend": [SMA(20), EMA(50)],
        "momentum": [RSI(14), MACD()],
        "volatility": [BollingerBands(20)]
    },
    weights={
        "trend": 0.4,
        "momentum": 0.4,
        "volatility": 0.2
    }
)

# Generate signals
signals = await strategy.generate_signals(market_data)
```

## 🔄 Signal Generation

All strategies implement the `generate_signals()` method which returns standardized trading signals:

```python
{
    "market": "SOL",
    "timestamp": 1677686400,
    "signal": "BUY",  # BUY, SELL, HOLD
    "confidence": 0.85,
    "params": {
        "entry_price": 100.50,
        "stop_loss": 98.50,
        "take_profit": 104.50,
        "position_size": 5.0
    },
    "metadata": {
        "strategy_name": "MLStrategy",
        "indicators_used": ["RSI", "MACD"],
        "timeframe": "5m"
    }
}
```

## 🧪 Testing

```bash
# Run all strategy tests
python -m pytest tests/utils/strategy/

# Run specific strategy tests
python -m pytest tests/utils/strategy/test_sol_spot.py
python -m pytest tests/utils/strategy/test_ml_strategies.py
```

## 📚 Resources

- [Strategy Development Guide](docs/utils/strategy/development.md)
- [Machine Learning Models Guide](docs/utils/strategy/ml_models.md)
- [Risk Management Guide](docs/utils/strategy/risk_management.md)
- [Backtesting Guide](docs/utils/strategy/backtesting.md) 