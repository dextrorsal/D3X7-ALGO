# src/utils/indicators/bollinger_bands.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class BollingerBands:
    """
    Bollinger Bands indicator implementation.
    Calculates upper and lower bands based on price volatility.
    """
    def __init__(self, period=20, deviations=2, matype=0):
        """
        Initialize Bollinger Bands.
        
        Args:
            period: Period for the moving average
            deviations: Number of standard deviations for bands
            matype: Moving average type (0=SMA, 1=EMA, etc.)
        """
        self.period = period
        self.deviations = deviations
        self.matype = matype
        self.prices = []
        
    def update(self, price):
        """
        Update Bollinger Bands with a new price.
        
        Args:
            price: New price to update with
            
        Returns:
            Tuple of (upper, middle, lower) band values
        """
        self.prices.append(price)
        
        # Keep only necessary data points for calculation
        if len(self.prices) > self.period * 2:
            self.prices.pop(0)
            
        if len(self.prices) >= self.period:
            # Calculate using talib for consistency with wrapper
            upper, middle, lower = talib.BBANDS(
                np.array(self.prices),
                timeperiod=self.period,
                nbdevup=self.deviations,
                nbdevdn=self.deviations,
                matype=self.matype
            )
            return upper[-1], middle[-1], lower[-1]
        
        return None, None, None
    
    def calculate(self, prices):
        """
        Calculate Bollinger Bands for a series of prices.
        
        Args:
            prices: Array or list of prices
            
        Returns:
            Tuple of arrays (upper, middle, lower)
        """
        if len(prices) < self.period:
            return None, None, None
            
        return talib.BBANDS(
            np.array(prices),
            timeperiod=self.period,
            nbdevup=self.deviations,
            nbdevdn=self.deviations,
            matype=self.matype
        )
    
    @staticmethod
    def percent_b(price, upper, lower):
        """
        Calculate %B - position of price within the bands (0-1).
        
        Args:
            price: Current price
            upper: Upper band value
            lower: Lower band value
            
        Returns:
            %B value (0-1 normally, can be outside this range)
        """
        if upper == lower:  # Avoid division by zero
            return 0.5
            
        return (price - lower) / (upper - lower)
    
    @staticmethod
    def bandwidth(upper, middle, lower):
        """
        Calculate bandwidth - shows volatility.
        
        Args:
            upper: Upper band value
            middle: Middle band value
            lower: Lower band value
            
        Returns:
            Bandwidth as percentage of middle band
        """
        if middle == 0:  # Avoid division by zero
            return 0
            
        return (upper - lower) / middle
        
def is_squeeze(bandwidths, window=20):
    """
    Detect Bollinger Band squeeze - volatility contraction.
    
    Args:
        bandwidths: Series of bandwidth values
        window: Lookback window
        
    Returns:
        True if current bandwidth is lower than minimum of previous window
    """
    if len(bandwidths) < window + 1:
        return False
        
    current = bandwidths.iloc[-1]
    historical_min = bandwidths.iloc[-window-1:-1].min()
    
    return current < historical_min

class BollingerBandsIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        bb_config = config.get('indicators', {}).get('bollinger_bands', {})
        
        self.period = bb_config.get('period', 20)
        self.deviations = bb_config.get('deviations', 2)
        self.filter_signals_by = bb_config.get('filter_signals_by', 'None')
        self.holding_period = bb_config.get('holding_period', 3)
        self.debug = False  # Set to True for debugging output
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using Bollinger Bands.
           1 = buy (price below lower band)
           -1 = sell (price above upper band)
           0 = no signal (price between bands)
        """
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0
        
        if 'close' not in df.columns:
            return signals
            
        # Calculate Bollinger Bands
        upper, middle, lower = talib.BBANDS(
            df['close'], 
            timeperiod=self.period, 
            nbdevup=self.deviations, 
            nbdevdn=self.deviations,
            matype=0  # Simple Moving Average
        )
        
        for i in range(len(df)):
            if pd.isna(upper[i]) or pd.isna(lower[i]):
                signals.iloc[i] = 0
                continue
                
            # Generate signals based on Bollinger Bands
            new_signal = 0
            
            # Buy signal: price crosses below lower band
            if df['close'].iloc[i] < lower[i]:
                new_signal = 1
                
            # Sell signal: price crosses above upper band
            elif df['close'].iloc[i] > upper[i]:
                new_signal = -1
            
            # Apply filters if configured
            if not self._passes_filter(df, i):
                new_signal = 0
                
            # Apply holding period logic
            if new_signal != current_signal:
                bar_count = 0
            else:
                bar_count += 1
                
            if bar_count >= self.holding_period and new_signal != 0:
                new_signal = 0
                bar_count = 0
                
            signals.iloc[i] = new_signal
            current_signal = new_signal
            
            # Debug output for every 100th bar
            if self.debug and i % 100 == 0:
                print(f"Bar {i}: Close={df['close'].iloc[i]:.2f}, Upper={upper[i]:.2f}, "
                      f"Middle={middle[i]:.2f}, Lower={lower[i]:.2f}, Signal={new_signal}")
                
        return signals
    
    def _passes_filter(self, df, i):
        # Same filter implementation as the user's other indicators
        if self.filter_signals_by == 'None':
            return True
        if i < 10:
            return True

        if self.filter_signals_by in ('Volatility', 'Both'):
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            atr1 = talib.ATR(high, low, close, 1)
            atr10 = talib.ATR(high, low, close, 10)
            if atr1[i] <= atr10[i]:
                return False

        if self.filter_signals_by in ('Volume', 'Both'):
            if 'volume' not in df.columns:
                return True
            vol = df['volume'].values
            rsi_vol = talib.RSI(vol, 14)
            if rsi_vol[i] <= 49:
                return False

        return True

# Example usage
if __name__ == "__main__":
    # Test the Bollinger Bands indicator
    data = np.random.normal(0, 1, 100) + np.linspace(0, 5, 100)  # Random data with uptrend
    bb = BollingerBands(period=20, deviations=2)
    upper, middle, lower = bb.calculate(data)
    
    print("Upper Band:", upper[-1])
    print("Middle Band:", middle[-1])
    print("Lower Band:", lower[-1])
    print("Bandwidth:", bb.bandwidth(upper[-1], middle[-1], lower[-1]))
    print("%B:", bb.percent_b(data[-1], upper[-1], lower[-1]))