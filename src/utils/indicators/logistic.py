# src/utils/indicators/logistic_regression.py

import numpy as np
import pandas as pd
import talib
from datetime import datetime
from .base_indicator import BaseIndicator
from src.core.config import Config

def sigmoid(z):
    return 1 / (1 + np.exp(-z))

def minimax(value, data_window):
    """
    Scale 'value' into the range defined by the min and max of 'data_window'.
    If min equals max, return the original value.
    """
    lo = np.min(data_window)
    hi = np.max(data_window)
    if np.isclose(hi, lo):
        return value
    return (hi - lo) * (value - lo) / (hi - lo) + lo

def normalize_array(arr):
    """
    Normalize a 1D array to the range [0,1] using min-max scaling.
    """
    lo = np.min(arr)
    hi = np.max(arr)
    if np.isclose(hi, lo):
        return arr  # avoid division by zero
    return (arr - lo) / (hi - lo)

class SingleDimLogisticRegression:
    """
    Replicates the Pine Script's single-weight logistic regression logic.
    For each bar, using 'lookback' points of data (X and Y),
    it fits a single weight 'w' via gradient descent and returns (loss, prediction),
    where prediction is the sigmoid output on the last data point.
    """
    def __init__(self, lookback=3, learning_rate=0.0009, iterations=1000):
        self.lookback = lookback
        self.learning_rate = learning_rate
        self.iterations = iterations

    def fit_single_bar(self, X, Y):
        """
        Fit a single-weight logistic regression on the provided arrays X and Y,
        each of length 'lookback'. Returns a tuple (loss, pred), where 'pred' is
        the final sigmoid output computed on the last element of the normalized X.
        """
        # Normalize X and Y to [0, 1]
        X_norm = normalize_array(X)
        Y_norm = normalize_array(Y)
        p = len(X_norm)
        w = 0.0  # initialize the single weight

        # Gradient descent
        for i in range(self.iterations):
            z = X_norm * w
            pred = sigmoid(z)
            error = pred - Y_norm
            gradient = np.sum(X_norm * error) / p
            w = w - self.learning_rate * gradient

        # Compute final prediction and loss
        last_pred = sigmoid(X_norm[-1] * w)
        final_loss = np.mean(np.power(sigmoid(X_norm * w) - Y_norm, 2))

        return final_loss, last_pred

class LogisticRegressionIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json'):
        config = Config()
        lr_config = config.get('indicators', {}).get('logistic_regression', {})

        self.lookback = lr_config.get('lookback', 3)
        self.norm_lookback = lr_config.get('norm_lookback', 2)
        self.learning_rate = lr_config.get('learning_rate', 0.0009)
        self.iterations = lr_config.get('iterations', 1000)
        self.filter_signals_by = lr_config.get('filter_signals_by', 'None')
        self.use_price_for_signal_generation = lr_config.get('use_price_data', True)
        self.easteregg = lr_config.get('easteregg', False)  # For historical data, set to false
        self.holding_period = lr_config.get('holding_period', 5)

        # Initialize the single-dim logistic regression model
        self.model = SingleDimLogisticRegression(
            lookback=self.lookback,
            learning_rate=self.learning_rate,
            iterations=self.iterations
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Replicates the Pine Script's bar-by-bar single-weight logistic regression logic:
          1. For each bar i, define base[i] and synth[i].
          2. Gather the last 'lookback' data points into arrays X and Y.
          3. Run fit_single_bar() to obtain (loss, raw prediction).
          4. Apply minimax scaling on loss and raw prediction using the last 'norm_lookback' bars.
          5. Determine the signal:
               - If use_price_data is True:
                   * if current price < scaled_loss then SELL (-1)
                   * if current price > scaled_loss then BUY (1)
                   * else hold (0)
               - Otherwise, use crossover logic.
          6. Apply filters (Volatility, Volume, Both, or None).
          7. Implement holding period logic (force exit after N bars).
        """
        DEBUG = False  # Set to False to disable debug output

        if 'close' not in df.columns:
            return pd.Series(0, index=df.index)

        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0

        # Essential data structures
        n = len(df)
        losses = np.zeros(n)
        raws = np.zeros(n)
        normalized_losses = np.zeros(n)
        normalized_preds = np.zeros(n)

        # Define base/synth data sources
        # Compute base array (close values) and synth array (volume percentage changes)
        base = df['close'].values
        
        # For synth we'll use a function of volume if available, otherwise use 'high'
        if 'volume' in df.columns:
            vol = df['volume'].values
            vol_pct = np.zeros_like(vol)
            for i in range(1, len(vol)):
                if vol[i-1] != 0:
                    vol_pct[i] = (vol[i] - vol[i-1]) / vol[i-1] * 100
            synth = vol_pct
        else:
            synth = df['high'].values

        # Loop through each bar starting from lookback
        for i in range(self.lookback, n):
            # Extract data windows for base and synth
            base_window = base[i-self.lookback:i]
            synth_window = synth[i-self.lookback:i]

            # Get loss and raw prediction using single weight logistic regression
            loss, raw = self.model.fit_single_bar(base_window, synth_window)
            losses[i] = loss
            raws[i] = raw

            # Apply minimax scaling using the last 'norm_lookback' bars
            if i >= self.lookback + self.norm_lookback:
                losses_window = losses[i-self.norm_lookback:i]
                raws_window = raws[i-self.norm_lookback:i]
                
                normalized_losses[i] = minimax(loss, losses_window)
                normalized_preds[i] = minimax(raw, raws_window)

                # A funny easteregg that acts as a very rough proxy for time-based position management
                if self.easteregg:
                    hour = datetime.now().hour
                    hour_scaling = hour / 24.0  # Normalize hour to 0-1
                    
                    if hour_scaling > 0.5:  # After noon, start to de-risk
                        normalized_losses[i] = normalized_losses[i] * (1 + hour_scaling)
                        normalized_preds[i] = normalized_preds[i] * (1 - hour_scaling)

                # Determine signal
                new_signal = 0
                if self.use_price_for_signal_generation:
                    # Compare current price to scaled loss
                    curr_price = base[i]
                    if curr_price < normalized_losses[i]:
                        new_signal = -1  # SELL
                    elif curr_price > normalized_losses[i]:
                        new_signal = 1   # BUY
                else:
                    # Use crossover logic
                    if i > 0:
                        norm_loss_prev = normalized_losses[i-1]
                        norm_pred_prev = normalized_preds[i-1]
                        
                        # Buy when pred crosses above loss
                        if norm_pred_prev <= norm_loss_prev and normalized_preds[i] > normalized_losses[i]:
                            new_signal = 1
                        # Sell when pred crosses below loss
                        elif norm_pred_prev >= norm_loss_prev and normalized_preds[i] < normalized_losses[i]:
                            new_signal = -1

                # Apply filters
                if not self._passes_filter(df, i):
                    new_signal = 0

                # Handle holding period logic
                if new_signal != current_signal:
                    bar_count = 0
                else:
                    bar_count += 1
                    
                if bar_count >= self.holding_period and current_signal != 0:
                    new_signal = 0
                    bar_count = 0

                # Set signal and update current signal
                signals.iloc[i] = new_signal
                current_signal = new_signal

                if DEBUG and i % 100 == 0:
                    print(f"Bar {i}: Loss={loss:.6f}, NormLoss={normalized_losses[i]:.6f}, "
                          f"Raw={raw:.6f}, NormPred={normalized_preds[i]:.6f}, Signal={new_signal}")

        return signals

    def _passes_filter(self, df, i):
        """Apply filters to the signal generation process."""
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
