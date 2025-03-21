# src/utils/indicators/williams_r.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class WilliamsR:
    """
    Williams %R indicator implementation.
    Momentum indicator that measures overbought/oversold levels.
    Similar to Stochastic but scaled differently (-100 to 0).
    """
    def __init__(self, period=14):
        """
        Initialize Williams %R.
        
        Args:
            period: Calculation period
        """
        self.period = period
        self.highs = []
        self.lows = []
        self.closes = []
        
    def update(self, high, low, close):
        """
        Update Williams %R with new price data.
        
        Args:
            high: Current high price
            low: Current low price
            close: Current close price
            
        Returns:
            Williams %R value
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
            willr = talib.WILLR(
                np.array(self.highs),
                np.array(self.lows),
                np.array(self.closes),
                timeperiod=self.period
            )
            return willr[-1]
        
        return None
    
    def calculate(self, highs, lows, closes):
        """
        Calculate Williams %R for series of prices.
        
        Args:
            highs: Array or list of high prices
            lows: Array or list of low prices
            closes: Array or list of close prices
            
        Returns:
            Array of Williams %R values
        """
        if len(closes) < self.period:
            return None
            
        return talib.WILLR(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            timeperiod=self.period
        )
    
    @staticmethod
    def is_overbought(willr, threshold=-20):
        """Check if Williams %R indicates overbought condition."""
        return willr > threshold
    
    @staticmethod
    def is_oversold(willr, threshold=-80):
        """Check if Williams %R indicates oversold condition."""
        return willr < threshold
        
    @staticmethod
    def midline_cross(prev_willr, curr_willr):
        """
        Detect Williams %R crossing the -50 midline.
        Returns: 1 for bullish cross (below to above -50), 
                -1 for bearish cross (above to below -50),
                 0 for no cross
        """
        if prev_willr < -50 and curr_willr > -50:
            return 1
        elif prev_willr > -50 and curr_willr < -50:
            return -1
        return 0
    
    @staticmethod
    def level_cross(prev_willr, curr_willr, level):
        """
        Detect Williams %R crossing a specific level.
        Returns: 1 for upward cross, -1 for downward cross, 0 for no cross
        """
        if prev_willr < level and curr_willr > level:
            return 1
        elif prev_willr > level and curr_willr < level:
            return -1
        return 0

class WilliamsRIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        willr_config = config.get('indicators', {}).get('williams_r', {})
        
        self.period = willr_config.get('period', 14)
        self.overbought = willr_config.get('overbought', -20)
        self.oversold = willr_config.get('oversold', -80)
        self.filter_signals_by = willr_config.get('filter_signals_by', 'None')
        self.holding_period = willr_config.get('holding_period', 3)
        self.use_midline_cross = willr_config.get('use_midline_cross', False)
        self.debug = False  # Set to True for debugging output
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using Williams %R.
           1 = buy (crosses above oversold level or midline from below)
           -1 = sell (crosses below overbought level or midline from above)
           0 = no signal
        """
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0
        
        # Required columns check
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return signals
            
        # Calculate Williams %R
        willr = talib.WILLR(
            df['high'],
            df['low'],
            df['close'],
            timeperiod=self.period
        )
        
        # Previous value for crossover detection
        prev_willr = None
        
        for i in range(len(df)):
            if pd.isna(willr[i]):
                signals.iloc[i] = 0
                continue
                
            # Current value
            curr_willr = willr[i]
            
            # Generate signals based on Williams %R
            new_signal = 0
            
            # Only generate signals if we have previous values
            if prev_willr is not None:
                if self.use_midline_cross:
                    # Buy signal: Crosses above midline (-50)
                    if prev_willr < -50 and curr_willr > -50:
                        new_signal = 1
                        
                    # Sell signal: Crosses below midline (-50)
                    elif prev_willr > -50 and curr_willr < -50:
                        new_signal = -1
                else:
                    # Buy signal: Crosses above oversold level
                    if prev_willr < self.oversold and curr_willr > self.oversold:
                        new_signal = 1
                        
                    # Sell signal: Crosses below overbought level
                    elif prev_willr > self.overbought and curr_willr < self.overbought:
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
            prev_willr = curr_willr
            
            # Debug output for every 100th bar
            if self.debug and i % 100 == 0:
                print(f"Bar {i}: Williams %R={curr_willr:.2f}, Signal={new_signal}")
                
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
    # Test the Williams %R indicator
    highs = np.array([10, 12, 15, 11, 9, 8, 10, 11, 12, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10])
    lows = np.array([8, 7, 10, 9, 7, 6, 7, 8, 9, 10, 11, 10, 9, 8, 7, 6, 5, 5, 6, 7, 8])
    closes = np.array([9, 11, 14, 10, 8, 7, 9, 10, 10, 13, 12, 11, 10, 9, 8, 7, 6, 6, 7, 8, 9])
    
    willr_indicator = WilliamsR(period=14)
    willr = willr_indicator.calculate(highs, lows, closes)
    
    print("Final Williams %R value:", willr[-1])
    print("Overbought:", willr_indicator.is_overbought(willr[-1]))
    print("Oversold:", willr_indicator.is_oversold(willr[-1]))