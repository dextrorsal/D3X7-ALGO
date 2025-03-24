import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config

class MacdBase:
    """
    Moving Average Convergence Divergence (MACD) calculator
    """
    def __init__(self, fast_period=12, slow_period=26, signal_period=9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.prices = []

    def update(self, price):
        """Update MACD calculation with new price"""
        self.prices.append(price)
        if len(self.prices) > max(self.fast_period, self.slow_period, self.signal_period) * 3:
            self.prices.pop(0)
            
        if len(self.prices) >= max(self.fast_period, self.slow_period, self.signal_period):
            macd, signal, hist = talib.MACD(
                np.array(self.prices), 
                fastperiod=self.fast_period,
                slowperiod=self.slow_period,
                signalperiod=self.signal_period
            )
            return macd[-1], signal[-1], hist[-1]
        return None, None, None

class MacdIndicator(BaseIndicator):
    """MACD indicator wrapper with signal generation functionality"""
    
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        macd_config = config.get('indicators', {}).get('macd', {})
        
        self.fast_period = macd_config.get('fast_period', 12)
        self.slow_period = macd_config.get('slow_period', 26)
        self.signal_period = macd_config.get('signal_period', 9)
        self.filter_signals_by = macd_config.get('filter_signals_by', 'None')
        self.holding_period = macd_config.get('holding_period', 5)
        self.debug = False
        self.model = MacdBase(self.fast_period, self.slow_period, self.signal_period)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0

        if 'close' not in df.columns:
            return signals

        macd, signal, hist = talib.MACD(
            df['close'], 
            fastperiod=self.fast_period, 
            slowperiod=self.slow_period, 
            signalperiod=self.signal_period
        )

        for i in range(len(df)):
            if pd.isna(macd[i]) or pd.isna(signal[i]):
                signals.iloc[i] = 0
                continue

            new_signal = 0
            # Signal logic: Buy when MACD crosses above Signal, Sell when it crosses below
            if i > 0 and macd[i-1] <= signal[i-1] and macd[i] > signal[i]:
                new_signal = 1  # Buy
            elif i > 0 and macd[i-1] >= signal[i-1] and macd[i] < signal[i]:
                new_signal = -1  # Sell

            if not self._passes_filter(df, i):
                new_signal = 0

            if new_signal != current_signal:
                bar_count = 0
            else:
                bar_count += 1
                
            if bar_count >= self.holding_period and new_signal != 0:
                new_signal = 0
                bar_count = 0

            signals.iloc[i] = new_signal
            current_signal = new_signal

            if self.debug and i % 100 == 0:
                print(f"Bar {i}: MACD={macd[i]:.4f}, Signal={signal[i]:.4f}, Hist={hist[i]:.4f}, Signal={new_signal}")

        return signals

    def _passes_filter(self, df, i):
        # Filter implementation similar to RSI
        if self.filter_signals_by == 'None':
            return True
        if i < 10:
            return True

        # Volatility filter
        if self.filter_signals_by in ('Volatility', 'Both'):
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            atr1 = talib.ATR(high, low, close, 1)
            atr10 = talib.ATR(high, low, close, 10)
            if atr1[i] <= atr10[i]:
                return False

        # Volume filter
        if self.filter_signals_by in ('Volume', 'Both'):
            if 'volume' not in df.columns:
                return True
            vol = df['volume'].values
            rsi_vol = talib.RSI(vol, 14)
            if rsi_vol[i] <= 49:
                return False

        return True