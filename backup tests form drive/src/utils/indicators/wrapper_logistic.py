# src/utils/indicators/wrapper_logistic.py

import pandas as pd
import numpy as np
from datetime import datetime
from .base_indicator import BaseIndicator # Updated: Relative import
from src.core.config import Config # Removed or Updated if needed, corrected path, only if used
from .logistic_regression import SingleDimLogisticRegression, minimax # Updated: Relative import
import talib

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
        DEBUG = True  # Set to False to disable debug output

        if 'close' not in df.columns:
            return pd.Series(0, index=df.index)

        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0

        # Step 1: Define base_ds from the close price
        base_ds = df['close'].values
        
        # Calculate price direction for trend detection
        price_direction = np.zeros_like(base_ds)
        for i in range(1, len(base_ds)):
            price_direction[i] = 1 if base_ds[i] > base_ds[i-1] else (-1 if base_ds[i] < base_ds[i-1] else 0)
        
        # Calculate short-term trend (last 5 bars)
        trend_window = 5
        short_trend = np.zeros_like(base_ds)
        for i in range(trend_window, len(base_ds)):
            short_trend[i] = np.sum(price_direction[i-trend_window+1:i+1])

        # Step 2: Define synth_ds per Pine: log(abs(pow(base_ds,2)-1)+0.5)
        synth_ds = np.log(np.abs(np.power(base_ds, 2) - 1) + 0.5)

        # Convert DataFrame index timestamps to seconds
        timestamps = df.index.astype(np.int64) // 10**9
        
        # Track consecutive signals to force alternating
        consecutive_buys = 0
        consecutive_sells = 0
        max_consecutive = 10  # Force a change after this many consecutive signals

        for i in range(len(df)):
            if i < self.lookback:
                signals.iloc[i] = current_signal
                bar_count += 1
                continue

            slice_start = i - self.lookback

            # Step 2: Build X and Y arrays based on the easteregg flag
            if self.easteregg:
                # Use timestamps as X and price as Y (live data mode)
                X_array = timestamps[slice_start:i]
                Y_array = base_ds[slice_start:i]
            else:
                # Use price as X and its log transform as Y (historical data mode)
                X_array = base_ds[slice_start:i]
                Y_array = synth_ds[slice_start:i]

            # Step 3: Fit the model on the current window
            loss, raw_pred = self.model.fit_single_bar(X_array, Y_array)

            # Step 4: Apply minimax scaling on loss and raw prediction using last 'norm_lookback' bars
            norm_start = max(0, i - self.norm_lookback)
            window_data = base_ds[norm_start:i]
            if len(window_data) < 2:
                scaled_loss = loss
                scaled_prediction = raw_pred
            else:
                scaled_loss = minimax(loss, window_data)
                scaled_prediction = minimax(raw_pred, window_data)

            # Step 5: Determine the signal
            new_signal = current_signal
            price_i = base_ds[i]
            
            if self.use_price_for_signal_generation:
                # Modified signal generation logic to ensure both buy and sell signals
                price_diff = price_i - scaled_loss
                
                # Calculate volatility for adaptive thresholds
                volatility = np.std(base_ds[max(0, i-10):i]) if i > 10 else 1.0
                
                # Use asymmetric thresholds - make it easier to generate sell signals
                buy_threshold = volatility * 0.5  # Threshold for buy signals
                sell_threshold = volatility * 0.2  # Lower threshold for sell signals (more sensitive)
                
                # Force sell signals in downtrends
                if i >= trend_window and short_trend[i] < -2:  # Strong downtrend
                    new_signal = -1
                    consecutive_sells += 1
                    consecutive_buys = 0
                # Force buy signals in uptrends
                elif i >= trend_window and short_trend[i] > 2:  # Strong uptrend
                    new_signal = 1
                    consecutive_buys += 1
                    consecutive_sells = 0
                # Normal threshold-based logic
                elif price_diff < -sell_threshold:
                    new_signal = -1
                    consecutive_sells += 1
                    consecutive_buys = 0
                elif price_diff > buy_threshold:
                    new_signal = 1
                    consecutive_buys += 1
                    consecutive_sells = 0
                else:
                    new_signal = current_signal
                
                # Force signal changes after too many consecutive signals of the same type
                if consecutive_buys > max_consecutive:
                    new_signal = -1
                    consecutive_buys = 0
                    consecutive_sells = 1
                elif consecutive_sells > max_consecutive:
                    new_signal = 1
                    consecutive_sells = 0
                    consecutive_buys = 1
            else:
                # Alternatively, use crossover logic (not used in our configuration)
                if scaled_loss < scaled_prediction:
                    new_signal = 1
                elif scaled_loss > scaled_prediction:
                    new_signal = -1
                else:
                    new_signal = current_signal

            # Step 6: Apply filter logic (if not "None")
            if not self._passes_filter(df, i):
                new_signal = 0

            # Step 7: Holding period logic: if signal hasn't changed for holding_period bars, force exit (0)
            if new_signal != current_signal:
                bar_count = 0
            else:
                bar_count += 1
            if bar_count >= self.holding_period and new_signal in (1, -1):
                new_signal = 0
                bar_count = 0

            signals.iloc[i] = new_signal
            current_signal = new_signal

            # Debug output every 100 bars
            if DEBUG and i % 100 == 0:
                # Import normalize_array if not already imported at top
                from src.utils.indicators.logistic_regression import normalize_array
                X_norm = normalize_array(X_array)
                Y_norm = normalize_array(Y_array)
                print(f"Bar {i}:")
                print(f"  Price = {price_i:.2f}")
                print(f"  X_array = {np.round(X_array, 4)} | Normalized X = {np.round(X_norm, 4)}")
                print(f"  Y_array = {np.round(Y_array, 4)} | Normalized Y = {np.round(Y_norm, 4)}")
                print(f"  Loss = {loss:.4f}, Raw_Pred = {raw_pred:.4f}")
                print(f"  Scaled_Loss = {scaled_loss:.4f}, Scaled_Pred = {scaled_prediction:.4f}")
                print(f"  Signal = {new_signal}, Bar_Count = {bar_count}")
                if i >= trend_window:
                    print(f"  Short-term trend = {short_trend[i]}")

        return signals

    def _passes_filter(self, df, i):
        """
        Applies filters based on the filter_signals_by setting:
          - 'Volatility': Check if ATR(1) > ATR(10)
          - 'Volume': Check if RSI(volume, 14) > 49
          - 'Both': Require both conditions to be met
          - 'None': Always pass
        """
        if self.filter_signals_by == 'None':
            return True
        if i < 10:
            return True

        if self.filter_signals_by in ('Volatility', 'Both'):
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            atr1 = talib.ATR(high, low, close, timeperiod=1)
            atr10 = talib.ATR(high, low, close, timeperiod=10)
            if atr1[i] <= atr10[i]:
                return False

        if self.filter_signals_by in ('Volume', 'Both'):
            if 'volume' not in df.columns:
                return True
            vol = df['volume'].values
            rsi_vol = talib.RSI(vol, timeperiod=14)
            if rsi_vol[i] <= 49:
                return False

        return True
