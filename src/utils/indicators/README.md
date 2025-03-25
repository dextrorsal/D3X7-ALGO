# 📊 Technical Indicators

This directory contains technical indicators used for market analysis and trading signal generation in the D3X7-ALGO platform.

## 📋 Overview

The indicators module provides:
- Traditional technical indicators (RSI, MACD, Bollinger Bands)
- Advanced indicators (Lorentzian, SuperTrend)
- Machine learning indicators (KNN, Logistic Regression)
- Momentum and trend indicators (ADX, CCI, Williams %R)
- Base indicator interface for custom implementations

## 📁 Structure

```
indicators/
├── base_indicator.py      # Base indicator interface
├── adx.py                # Average Directional Index
├── bollinger_bands.py    # Bollinger Bands
├── cci.py               # Commodity Channel Index
├── knn.py               # K-Nearest Neighbors
├── logistic_regression.py # Logistic Regression
├── lorentzian.py        # Lorentzian Classification
├── macd.py              # Moving Average Convergence Divergence
├── rsi.py               # Relative Strength Index
├── stochastic.py        # Stochastic Oscillator
├── supertrend.py        # SuperTrend
├── williams_r.py        # Williams %R
└── __init__.py          # Package initialization
```

## 🔧 Components

### Base Indicator
The foundation for all technical indicators, providing common functionality.

```python
from src.utils.indicators.base_indicator import BaseIndicator

class CustomIndicator(BaseIndicator):
    def __init__(self, period=14):
        super().__init__()
        self.period = period
    
    def calculate(self, data):
        # Your indicator calculation logic
        pass
```

### Traditional Indicators

#### RSI (Relative Strength Index)
```python
from src.utils.indicators import RSI

rsi = RSI(period=14)
values = rsi.calculate(prices)
```

#### MACD (Moving Average Convergence Divergence)
```python
from src.utils.indicators import MACD

macd = MACD(fast=12, slow=26, signal=9)
macd_line, signal_line, histogram = macd.calculate(prices)
```

#### Bollinger Bands
```python
from src.utils.indicators import BollingerBands

bb = BollingerBands(period=20, std_dev=2)
upper, middle, lower = bb.calculate(prices)
```

### Advanced Indicators

#### Lorentzian Classification
```python
from src.utils.indicators import LorentzianClassifier

classifier = LorentzianClassifier(
    lookback=100,
    dimensions=["price", "volume", "volatility"]
)
signals = classifier.calculate(market_data)
```

#### SuperTrend
```python
from src.utils.indicators import SuperTrend

supertrend = SuperTrend(period=10, multiplier=3)
trend, direction = supertrend.calculate(high, low, close)
```

### Machine Learning Indicators

#### K-Nearest Neighbors
```python
from src.utils.indicators import KNNIndicator

knn = KNNIndicator(n_neighbors=5, features=["rsi", "macd"])
predictions = knn.predict(market_data)
```

#### Logistic Regression
```python
from src.utils.indicators import LogisticRegressionIndicator

lr = LogisticRegressionIndicator(
    features=["price", "volume", "rsi"],
    lookback=50
)
signals = lr.predict(market_data)
```

### Momentum Indicators

#### ADX (Average Directional Index)
```python
from src.utils.indicators import ADX

adx = ADX(period=14)
adx_value, plus_di, minus_di = adx.calculate(high, low, close)
```

#### CCI (Commodity Channel Index)
```python
from src.utils.indicators import CCI

cci = CCI(period=20)
values = cci.calculate(high, low, close)
```

#### Williams %R
```python
from src.utils.indicators import WilliamsR

williams = WilliamsR(period=14)
values = williams.calculate(high, low, close)
```

## 🔄 Signal Generation

Most indicators provide standardized signal outputs:

```python
{
    "value": 65.5,          # Main indicator value
    "signal": "BUY",        # BUY, SELL, HOLD
    "strength": 0.85,       # Signal strength (0-1)
    "metadata": {
        "indicator": "RSI",
        "parameters": {"period": 14},
        "timestamp": 1677686400
    }
}
```

## 🧪 Testing

```bash
# Run all indicator tests
python -m pytest tests/utils/indicators/

# Run specific indicator tests
python -m pytest tests/utils/indicators/test_rsi.py
python -m pytest tests/utils/indicators/test_macd.py
```

## 📚 Resources

- [Indicator Development Guide](docs/utils/indicators/development.md)
- [Machine Learning Integration Guide](docs/utils/indicators/ml_integration.md)
- [Signal Generation Guide](docs/utils/indicators/signals.md)
- [Performance Optimization Guide](docs/utils/indicators/optimization.md) 