# src/utils/indicators/cci.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class CCI:
    """
    Commodity Channel Index (CCI) indicator implementation.
    Measures current price level relative to an average price level over a period.
    """
    def __init__(self, period=20):
        """
        Initialize CCI.
        
        Args:
            period: Calculation period
        """
        self.period = period
        self.highs = []
        self.lows = []
        self.closes = []
        
    def update(self, high, low, close):
        """
        Update CCI with new price data.
        
        Args:
            high: Current high price
            low: Current low price
            close: Current close price
            
        Returns:
            CCI value
        """
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        # Keep only necessary data points for calculation
        if len(self.closes) > self.period * 2:
            self.highs.pop(0)
            self.lows.pop(0)
            self.closes.pop(0)
            
        if len(self.closes) >= self.period:
            # Calculate using talib for consistency with wrapper
            cci = talib.CCI(
                np.array(self.highs),
                np.array(self.lows),
                np.array(self.closes),
                timeperiod=self.period
            )
            return cci[-1]
        
        return None
    
    def calculate(self, highs, lows, closes):
        """
        Calculate CCI for series of prices.
        
        Args:
            highs: Array or list of high prices
            lows: Array or list of low prices
            closes: Array or list of close prices
            
        Returns:
            Array of CCI values
        """
        if len(closes) < self.period:
            return None
            
        return talib.CCI(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            timeperiod=self.period
        )
    
    @staticmethod
    def is_overbought(cci, threshold=100):
        """Check if CCI indicates overbought condition."""
        return cci > threshold
    
    @staticmethod
    def is_oversold(cci, threshold=-100):
        """Check if CCI indicates oversold condition."""
        return cci < threshold
        
    @staticmethod
    def zero_line_cross(prev_cci, curr_cci):
        """
        Detect CCI crossing the zero line.
        Returns: 1 for bullish cross (negative to positive), 
                -1 for bearish cross (positive to negative),
                 0 for no cross
        """
        if prev_cci < 0 and curr_cci > 0:
            return 1
        elif prev_cci > 0 and curr_cci < 0:
            return -1
        return 0

class CCIIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        cci_config = config.get('indicators', {}).get('cci', {})
        
        self.period = cci_config.get('period', 20)
        self.overbought = cci_config.get('overbought', 100)
        self.oversold = cci_config.get('oversold', -100)
        self.filter_signals_by = cci_config.get('filter_signals_by', 'None')
        self.holding_period = cci_config.get('holding_period', 3)
        self.debug = False  # Set to True for debugging output
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using CCI.
           1 = buy (CCI crosses above oversold level)
           -1 = sell (CCI crosses below overbought level)
           0 = no signal
        """
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0
        
        # Required columns check
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return signals
            
        # Calculate CCI
        cci = talib.CCI(
            df['high'],
            df['low'],
            df['close'],
            timeperiod=self.period
        )
        
        # Previous value for crossover detection
        prev_cci = None
        
        for i in range(len(df)):
            if pd.isna(cci[i]):
                signals.iloc[i] = 0
                continue
                
            # Current value
            curr_cci = cci[i]
            
            # Generate signals based on CCI
            new_signal = 0
            
            # Only generate signals if we have previous values
            if prev_cci is not None:
                # Buy signal: Crosses above oversold level
                if prev_cci < self.oversold and curr_cci > self.oversold:
                    new_signal = 1
                    
                # Sell signal: Crosses below overbought level
                elif prev_cci > self.overbought and curr_cci < self.overbought:
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
            
            # Update previous value
            prev_cci = curr_cci
            
            # Debug output for every 100th bar
            if self.debug and i % 100 == 0:
                print(f"Bar {i}: CCI={curr_cci:.2f}, Signal={new_signal}")
                
        return signals
    
    def _passes_filter(self, df, i):
        # Same filter implementation as other indicators
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
    # Test the CCI indicator
    highs = np.array([10, 12, 15, 11, 9, 8, 10, 11, 12, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10, 11])
    lows = np.array([8, 7, 10, 9, 7, 6, 7, 8, 9, 10, 11, 10, 9, 8, 7, 6, 5, 5, 6, 7, 8, 9])
    closes = np.array([9, 11, 14, 10, 8, 7, 9, 10, 10, 13, 12, 11, 10, 9, 8, 7, 6, 6, 7, 8, 9, 10])
    
    cci_indicator = CCI(period=14)
    cci = cci_indicator.calculate(highs, lows, closes)
    
    print("Final CCI value:", cci[-1])
    print("Overbought:", cci_indicator.is_overbought(cci[-1]))
    print("Oversold:", cci_indicator.is_oversold(cci[-1]))