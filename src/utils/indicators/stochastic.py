# src/utils/indicators/stochastic.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class Stochastic:
    """
    Stochastic Oscillator indicator implementation.
    Measures momentum by comparing closing price to price range over a period.
    """
    def __init__(self, k_period=14, d_period=3, slowing=3):
        """
        Initialize Stochastic Oscillator.
        
        Args:
            k_period: Period for %K calculation
            d_period: Period for %D calculation (moving average of %K)
            slowing: Slowing period (moving average of raw %K)
        """
        self.k_period = k_period
        self.d_period = d_period
        self.slowing = slowing
        self.highs = []
        self.lows = []
        self.closes = []
        
    def update(self, high, low, close):
        """
        Update Stochastic Oscillator with new price data.
        
        Args:
            high: Current high price
            low: Current low price
            close: Current close price
            
        Returns:
            Tuple of (k, d) values
        """
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        # Keep only necessary data points for calculation
        if len(self.closes) > self.k_period + self.d_period:
            self.highs.pop(0)
            self.lows.pop(0)
            self.closes.pop(0)
            
        if len(self.closes) >= self.k_period:
            # Calculate using talib for consistency with wrapper
            k, d = talib.STOCH(
                np.array(self.highs),
                np.array(self.lows),
                np.array(self.closes),
                fastk_period=self.k_period,
                slowk_period=self.slowing,
                slowk_matype=0,
                slowd_period=self.d_period,
                slowd_matype=0
            )
            return k[-1], d[-1]
        
        return None, None
    
    def calculate(self, highs, lows, closes):
        """
        Calculate Stochastic Oscillator for series of prices.
        
        Args:
            highs: Array or list of high prices
            lows: Array or list of low prices
            closes: Array or list of close prices
            
        Returns:
            Tuple of arrays (k, d)
        """
        if len(closes) < self.k_period:
            return None, None
            
        return talib.STOCH(
            np.array(highs),
            np.array(lows),
            np.array(closes),
            fastk_period=self.k_period,
            slowk_period=self.slowing,
            slowk_matype=0,
            slowd_period=self.d_period,
            slowd_matype=0
        )
    
    @staticmethod
    def is_overbought(k, d, threshold=80):
        """Check if stochastic indicates overbought condition."""
        return k > threshold and d > threshold
    
    @staticmethod
    def is_oversold(k, d, threshold=20):
        """Check if stochastic indicates oversold condition."""
        return k < threshold and d < threshold
        
    @staticmethod
    def has_bullish_crossover(prev_k, prev_d, curr_k, curr_d):
        """Check for bullish crossover (%K crosses above %D)."""
        return prev_k < prev_d and curr_k > curr_d
        
    @staticmethod
    def has_bearish_crossover(prev_k, prev_d, curr_k, curr_d):
        """Check for bearish crossover (%K crosses below %D)."""
        return prev_k > prev_d and curr_k < curr_d

class StochasticIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        stoch_config = config.get('indicators', {}).get('stochastic', {})
        
        self.k_period = stoch_config.get('k_period', 14)
        self.d_period = stoch_config.get('d_period', 3)
        self.smoothing = stoch_config.get('smoothing', 3)
        self.overbought = stoch_config.get('overbought', 80)
        self.oversold = stoch_config.get('oversold', 20)
        self.filter_signals_by = stoch_config.get('filter_signals_by', 'None')
        self.holding_period = stoch_config.get('holding_period', 3)
        self.debug = False  # Set to True for debugging output
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using Stochastic Oscillator.
           1 = buy (oversold with bullish crossover)
           -1 = sell (overbought with bearish crossover)
           0 = no signal
        """
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0
        
        # Required columns check
        required_cols = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return signals
            
        # Calculate Stochastic Oscillator
        k, d = talib.STOCH(
            df['high'], 
            df['low'], 
            df['close'],
            fastk_period=self.k_period,
            slowk_period=self.smoothing,
            slowk_matype=0,
            slowd_period=self.d_period,
            slowd_matype=0
        )
        
        # Previous values for crossover detection
        prev_k, prev_d = None, None
        
        for i in range(len(df)):
            if pd.isna(k[i]) or pd.isna(d[i]):
                signals.iloc[i] = 0
                continue
                
            # Current values
            curr_k, curr_d = k[i], d[i]
            
            # Generate signals based on Stochastic
            new_signal = 0
            
            # Only generate signals if we have previous values
            if prev_k is not None and prev_d is not None:
                # Buy signal: Oversold with bullish crossover
                if curr_k < self.oversold and curr_d < self.oversold and prev_k < prev_d and curr_k > curr_d:
                    new_signal = 1
                    
                # Sell signal: Overbought with bearish crossover
                elif curr_k > self.overbought and curr_d > self.overbought and prev_k > prev_d and curr_k < curr_d:
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
            prev_k, prev_d = curr_k, curr_d
            
            # Debug output for every 100th bar
            if self.debug and i % 100 == 0:
                print(f"Bar {i}: %K={curr_k:.2f}, %D={curr_d:.2f}, Signal={new_signal}")
                
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
    # Test the Stochastic Oscillator
    highs = np.array([10, 12, 15, 11, 9, 8, 10, 11, 12, 15, 14, 13, 12, 11, 10])
    lows = np.array([8, 7, 10, 9, 7, 6, 7, 8, 9, 10, 11, 10, 9, 8, 7])
    closes = np.array([9, 11, 14, 10, 8, 7, 9, 10, 10, 13, 12, 11, 10, 9, 8])
    
    stochastic = Stochastic(k_period=5, d_period=3, slowing=3)
    k, d = stochastic.calculate(highs, lows, closes)
    
    print("Final %K value:", k[-1])
    print("Final %D value:", d[-1])
    print("Overbought:", stochastic.is_overbought(k[-1], d[-1]))
    print("Oversold:", stochastic.is_oversold(k[-1], d[-1]))