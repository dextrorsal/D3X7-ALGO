# src/utils/indicators/adx.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class ADX:
    """
    Average Directional Index (ADX) indicator implementation.
    Measures trend strength without regard to trend direction.
    """
    def __init__(self, period=14):
        """
        Initialize ADX.
        
        Args:
            period: Calculation period
        """
        self.period = period
        self.highs = []
        self.lows = []
        self.closes = []
        
    def update(self, high, low, close):
        """
        Update ADX with new price data.
        
        Args:
            high: Current high price
            low: Current low price
            close: Current close price
            
        Returns:
            Tuple of (ADX, +DI, -DI) values
        """
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        # Keep only necessary data points for calculation
        if len(self.closes) > self.period * 3:
            self.highs.pop(0)
            self.lows.pop(0)
            self.closes.pop(0)
            
        if len(self.closes) >= self.period:
            # Calculate using talib for consistency with wrapper
            adx, plus_di, minus_di = talib.ADXR(
                np.array(self.highs),
                np.array(self.lows),
                np.array(self.closes),
                timeperiod=self.period
            )
            return adx[-1], plus_di[-1], minus_di[-1]
        
        return None, None, None
    
    def calculate(self, highs, lows, closes):
        """
        Calculate ADX for series of prices.
        
        Args:
            highs: Array or list of high prices
            lows: Array or list of low prices
            closes: Array or list of close prices
            
        Returns:
            Tuple of arrays (adx, +di, -di)
        """
        if len(closes) < self.period:
            return None, None, None
            
        return talib.ADX(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            timeperiod=self.period
        ), talib.PLUS_DI(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            timeperiod=self.period
        ), talib.MINUS_DI(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            timeperiod=self.period
        )
    
    @staticmethod
    def is_strong_trend(adx, threshold=25):
        """Check if ADX indicates a strong trend (above threshold)."""
        return adx > threshold
    
    @staticmethod
    def is_weak_trend(adx, threshold=20):
        """Check if ADX indicates a weak trend (below threshold)."""
        return adx < threshold
        
    @staticmethod
    def trend_direction(plus_di, minus_di):
        """
        Determine trend direction based on +DI and -DI.
        Returns: 1 for bullish (+DI > -DI), 
                -1 for bearish (+DI < -DI),
                 0 for no trend (+DI == -DI)
        """
        if plus_di > minus_di:
            return 1
        elif plus_di < minus_di:
            return -1
        return 0
    
    @staticmethod
    def di_crossover(prev_plus_di, prev_minus_di, curr_plus_di, curr_minus_di):
        """
        Detect DI crossover.
        Returns: 1 for bullish cross (+DI crosses above -DI), 
                -1 for bearish cross (+DI crosses below -DI),
                 0 for no cross
        """
        if prev_plus_di < prev_minus_di and curr_plus_di > curr_minus_di:
            return 1
        elif prev_plus_di > prev_minus_di and curr_plus_di < curr_minus_di:
            return -1
        return 0

class ADXIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        adx_config = config.get('indicators', {}).get('adx', {})
        
        self.period = adx_config.get('period', 14)
        self.threshold = adx_config.get('threshold', 25)
        self.filter_signals_by = adx_config.get('filter_signals_by', 'None')
        self.holding_period = adx_config.get('holding_period', 3)
        self.use_crossover = adx_config.get('use_crossover', True)
        self.debug = False  # Set to True for debugging output
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using ADX.
           1 = buy (+DI crosses above -DI with strong ADX)
           -1 = sell (-DI crosses above +DI with strong ADX)
           0 = no signal
        """
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0
        
        # Required columns check
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return signals
            
        # Calculate ADX and Directional Indicators
        adx = talib.ADX(
            df['high'],
            df['low'],
            df['close'],
            timeperiod=self.period
        )
        
        plus_di = talib.PLUS_DI(
            df['high'],
            df['low'],
            df['close'],
            timeperiod=self.period
        )
        
        minus_di = talib.MINUS_DI(
            df['high'],
            df['low'],
            df['close'],
            timeperiod=self.period
        )
        
        # Previous values for crossover detection
        prev_plus_di, prev_minus_di = None, None
        
        for i in range(len(df)):
            if pd.isna(adx[i]) or pd.isna(plus_di[i]) or pd.isna(minus_di[i]):
                signals.iloc[i] = 0
                continue
                
            # Current values
            curr_adx = adx[i]
            curr_plus_di = plus_di[i]
            curr_minus_di = minus_di[i]
            
            # Generate signals based on ADX and DI
            new_signal = 0
            
            # Only generate signals if we have previous values and ADX is above threshold
            if prev_plus_di is not None and prev_minus_di is not None and curr_adx > self.threshold:
                if self.use_crossover:
                    # Buy signal: +DI crosses above -DI
                    if prev_plus_di < prev_minus_di and curr_plus_di > curr_minus_di:
                        new_signal = 1
                        
                    # Sell signal: -DI crosses above +DI
                    elif prev_plus_di > prev_minus_di and curr_plus_di < curr_minus_di:
                        new_signal = -1
                else:
                    # Alternative: Use current DI values without requiring crossover
                    if curr_plus_di > curr_minus_di:
                        new_signal = 1
                    elif curr_plus_di < curr_minus_di:
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
            
            # Update previous values
            prev_plus_di, prev_minus_di = curr_plus_di, curr_minus_di
            
            # Debug output for every 100th bar
            if self.debug and i % 100 == 0:
                print(f"Bar {i}: ADX={curr_adx:.2f}, +DI={curr_plus_di:.2f}, -DI={curr_minus_di:.2f}, Signal={new_signal}")
                
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
    # Test the ADX indicator
    highs = np.array([10, 12, 15, 15, 15, 15, 16, 17, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 7, 8, 9, 10, 11])
    lows = np.array([8, 7, 10, 10, 10, 10, 12, 13, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 3, 4, 5, 6, 7])
    closes = np.array([9, 11, 14, 14, 14, 14, 15, 16, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10])
    
    adx_indicator = ADX(period=14)
    adx, plus_di, minus_di = adx_indicator.calculate(highs, lows, closes)
    
    print("Final ADX value:", adx[-1])
    print("Final +DI value:", plus_di[-1])
    print("Final -DI value:", minus_di[-1])
    print("Is strong trend:", adx_indicator.is_strong_trend(adx[-1]))
    print("Trend direction:", adx_indicator.trend_direction(plus_di[-1], minus_di[-1]))