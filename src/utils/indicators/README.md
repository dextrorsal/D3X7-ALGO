# D3X7 Trading Indicators

This folder contains technical indicators for trading strategy development and signal generation within the D3X7 algorithmic trading platform.

## 📊 Indicator Structure

Each indicator follows a consistent dual-class pattern:

1. **Base Class** - Core calculation logic (e.g., `ADX`, `WilliamsR`)
   - Handles raw calculations
   - Offers utility methods for analyzing indicator values
   - Maintains minimal state for streaming calculations

2. **Indicator Class** - Signal generation wrapper (e.g., `ADXIndicator`, `WilliamsRIndicator`)
   - Implements the `BaseIndicator` interface
   - Loads configuration from settings files
   - Generates trading signals (1 = buy, -1 = sell, 0 = neutral)
   - Applies filters and signal processing logic

## 🛠️ Available Indicators

| Indicator | Description | File |
|-----------|-------------|------|
| RSI | Relative Strength Index - Momentum oscillator measuring speed and change of price movements | `rsi.py` |
| MACD | Moving Average Convergence Divergence - Trend-following momentum indicator | `macd.py` |
| Supertrend | Combines ATR with moving averages for trend determination | `supertrend.py` |
| Bollinger Bands | Volatility bands placed above and below a moving average | `bollinger_bands.py` |
| KNN | K-Nearest Neighbors machine learning classifier for price action | `knn.py` |
| Logistic Regression | ML-based classification of price movements | `logistic_regression.py` |
| Lorentzian | Advanced classification using Lorentzian model | `lorentzian.py` |
| ADX | Average Directional Index for trend strength measurement | `adx.py` |
| CCI | Commodity Channel Index for identifying cyclical trends | `cci.py` |
| Stochastic | Momentum oscillator comparing closing price to price range | `stochastic.py` |
| Williams %R | Momentum indicator showing overbought/oversold levels | `williams_r.py` |

## 🔧 Usage Examples

### Basic Usage with Base Class (Raw Calculations)

```python
from src.utils.indicators.rsi import RsiBase

# Create the indicator instance
rsi = RsiBase(period=14)

# For a single update (streaming data)
new_rsi_value = rsi.update(close_price)

# For batch calculation
prices = [100, 102, 99, 101, 103, 102, 105]
rsi_values = rsi.calculate(prices)

# Analysis helpers
is_overbought = RsiBase.is_overbought(rsi_value, threshold=70)
is_oversold = RsiBase.is_oversold(rsi_value, threshold=30)
```

### Signal Generation with Indicator Class

```python
from src.utils.indicators.rsi import RsiIndicator
import pandas as pd

# Create the indicator instance (loads settings from config)
rsi_indicator = RsiIndicator()

# Prepare data
df = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# Generate trading signals
signals = rsi_indicator.generate_signals(df)
# Result: Series of 1 (buy), -1 (sell), or 0 (neutral)
```

## 📝 Signal Generation Process

Most indicators follow this general approach for signal generation:

1. Calculate the raw indicator values using TA-Lib
2. Process each price bar sequentially
3. Look for specific conditions (crossovers, thresholds)
4. Apply configured filters (volatility, volume)
5. Consider holding period logic
6. Generate the appropriate signal (buy, sell, neutral)

## ⚙️ Indicator Configuration

Indicator parameters are loaded from `config/indicator_settings.json` and typically include:

- **Calculation Parameters**: Periods, thresholds, etc.
- **Signal Filters**: Options like `filter_signals_by` with values (`None`, `Volatility`, `Volume`, `Both`)
- **Holding Period**: How many bars to maintain a signal
- **Other indicator-specific parameters**

## 🔄 Contributing

When creating a new indicator:

1. Implement the base calculation class
2. Create an indicator class that extends `BaseIndicator`
3. Export both classes in the module's `__init__.py`
4. Follow the consistent naming pattern: `IndicatorName` for base and `IndicatorNameIndicator` for signal wrapper

## 🔗 Integration

All indicators are accessible through the module's `__init__.py` for easy importing:

```python
from src.utils.indicators import RsiIndicator, MacdIndicator
``` 