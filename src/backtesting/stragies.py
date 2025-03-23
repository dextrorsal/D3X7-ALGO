# src/backtesting/strategies.py

import numpy as np
import pandas as pd


def moving_average_crossover(data: pd.DataFrame, fast_window: int = 10, slow_window: int = 30) -> np.ndarray:
    """
    Moving Average Crossover strategy.
    
    Args:
        data: DataFrame with OHLCV data (must have 'close' column)
        fast_window: Period for fast moving average
        slow_window: Period for slow moving average
        
    Returns:
        numpy array of integer signals (1 for long, 0 for flat)
    """
    # Calculate moving averages
    fast_ma = data['close'].rolling(window=fast_window).mean()
    slow_ma = data['close'].rolling(window=slow_window).mean()
    
    # Generate signals: 1 when fast MA > slow MA, 0 otherwise
    signals = np.zeros(len(data))
    signals[fast_ma > slow_ma] = 1
    
    # Set signals to NaN where we don't have enough data
    signals[:slow_window] = np.nan
    
    return signals


def donchian_channel_breakout(data: pd.DataFrame, lookback: int = 20) -> np.ndarray:
    """
    Donchian Channel Breakout strategy.
    Enters long when price breaks above the highest high of the lookback period.
    Exits when price breaks below the lowest low of the lookback period.
    
    Args:
        data: DataFrame with OHLCV data (must have 'close', 'high', and 'low' columns)
        lookback: Lookback period for channel calculation
        
    Returns:
        numpy array of integer signals (1 for long, 0 for flat)
    """
    # Calculate highest high and lowest low over lookback period
    highest_high = data['high'].rolling(window=lookback).max().shift(1)
    lowest_low = data['low'].rolling(window=lookback).min().shift(1)
    
    # Initialize signals array
    signals = np.zeros(len(data))
    
    # Set signal for first lookback+1 bars to NaN (not enough data)
    signals[:lookback+1] = np.nan
    
    # Iterate through data to generate signals
    position = 0
    for i in range(lookback+1, len(data)):
        if position == 0:  # Not in a position
            if data['close'].iloc[i] > highest_high.iloc[i]:
                position = 1  # Enter long
        elif position == 1:  # In a long position
            if data['close'].iloc[i] < lowest_low.iloc[i]:
                position = 0  # Exit long
        
        signals[i] = position
    
    return signals


def rsi_strategy(data: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> np.ndarray:
    """
    RSI strategy.
    Goes long when RSI crosses above oversold level, exits when RSI crosses above overbought level.
    
    Args:
        data: DataFrame with OHLCV data (must have 'close' column)
        period: Period for RSI calculation
        oversold: Oversold threshold (typically 30)
        overbought: Overbought threshold (typically 70)
        
    Returns:
        numpy array of integer signals (1 for long, 0 for flat)
    """
    # Calculate price changes
    delta = data['close'].diff()
    
    # Calculate gains and losses
    gains = delta.copy()
    losses = delta.copy()
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = -losses  # Make losses positive
    
    # Calculate average gains and losses
    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Initialize signals array
    signals = np.zeros(len(data))
    
    # Set signal for first period+1 bars to NaN (not enough data)
    signals[:period+1] = np.nan
    
    # Iterate through data to generate signals
    position = 0
    for i in range(period+1, len(data)):
        if position == 0:  # Not in a position
            if rsi.iloc[i-1] < oversold and rsi.iloc[i] > oversold:
                position = 1  # Enter long when RSI crosses above oversold
        elif position == 1:  # In a long position
            if rsi.iloc[i-1] < overbought and rsi.iloc[i] > overbought:
                position = 0  # Exit long when RSI crosses above overbought
        
        signals[i] = position
    
    return signals


def bollinger_band_strategy(data: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> np.ndarray:
    """
    Bollinger Band strategy.
    Goes long when price touches the lower band, exits when price touches the upper band.
    
    Args:
        data: DataFrame with OHLCV data (must have 'close' column)
        window: Period for moving average calculation
        num_std: Number of standard deviations for band width
        
    Returns:
        numpy array of integer signals (1 for long, 0 for flat)
    """
    # Calculate moving average
    rolling_mean = data['close'].rolling(window=window).mean()
    
    # Calculate standard deviation
    rolling_std = data['close'].rolling(window=window).std()
    
    # Calculate Bollinger Bands
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    
    # Initialize signals array
    signals = np.zeros(len(data))
    
    # Set signal for first window bars to NaN (not enough data)
    signals[:window] = np.nan
    
    # Iterate through data to generate signals
    position = 0
    for i in range(window, len(data)):
        if position == 0:  # Not in a position
            if data['close'].iloc[i] <= lower_band.iloc[i]:
                position = 1  # Enter long when price touches lower band
        elif position == 1:  # In a long position
            if data['close'].iloc[i] >= upper_band.iloc[i]:
                position = 0  # Exit long when price touches upper band
        
        signals[i] = position
    
    return signals