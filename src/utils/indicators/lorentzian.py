# src/utils/indicators/lorentzian.py

import math  # Ensure this is imported at the top
import numpy as np
import pandas as pd
import talib
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union

@dataclass
class Feature:
    type: str
    parameter_a: int
    parameter_b: int

@dataclass
class LorentzianSettings:
    # General Settings
    source: str = "close"
    neighbors_count: int = 8
    max_bars_back: int = 2000
    
    # Feature Engineering
    feature_count: int = 5
    color_compression: int = 1
    
    # Filters
    use_volatility_filter: bool = True
    use_regime_filter: bool = False
    use_adx_filter: bool = False
    use_ema_filter: bool = False
    use_sma_filter: bool = False

    # Additional fields
    regime_threshold: float = -0.1
    adx_threshold: int = 20
    ema_period: int = 200
    sma_period: int = 200
    use_dynamic_exits: bool = False
    use_worst_case_estimates: bool = False
    enhance_kernel_smoothing: bool = False
    lag: int = 1
    
    # Kernel settings
    lookback_window: int = 8
    relative_weighting: float = 8.0
    regression_level: int = 25
    show_kernel_estimate: bool = True

class LorentzianClassification:
    """
    A unified LorentzianClassification that:
      1) Calculates TA-based features (RSI, WT, CCI, ADX).
      2) Can generate signals using an ML-core approach (kernel regression + kNN).
      3) Has a `.run()` method for your wrapper_lorentzian.py.
    """

    def __init__(self, settings: LorentzianSettings = None):
        self.settings = settings or LorentzianSettings()
        
        # Default features for TA-based calculations
        self.features = [
            Feature("RSI", 14, 1),
            Feature("WT", 10, 11),
            Feature("CCI", 20, 1),
            Feature("ADX", 20, 2),
            Feature("RSI", 9, 1)
        ]
        
        # Load features from settings if available
        if hasattr(self.settings, 'features'):
            self.features = self.settings.features

    # ----------------------------------------------------------------
    # (A) TA-Based Feature Calculations
    # ----------------------------------------------------------------
    def calculate_rsi_feature(self, data: pd.DataFrame, period: int, parameter_b: int) -> pd.Series:
        """Calculate RSI feature."""
        rsi = talib.RSI(data['close'], timeperiod=period)
        # Apply EMA smoothing if parameter_b > 1
        if parameter_b > 1:
            rsi = talib.EMA(rsi, timeperiod=parameter_b)
        return rsi

    def calculate_wt_feature(self, data: pd.DataFrame, parameter_a: int, parameter_b: int) -> pd.Series:
        """Calculate Wave Trend feature."""
        hlc3 = (data['high'] + data['low'] + data['close']) / 3
        esa = talib.EMA(hlc3, timeperiod=parameter_a)
        d = talib.EMA(abs(hlc3 - esa), timeperiod=parameter_a)
        ci = (hlc3 - esa) / (0.015 * d)
        wt = talib.EMA(ci, timeperiod=parameter_b)
        return wt

    def calculate_cci_feature(self, data: pd.DataFrame, period: int, parameter_b: int) -> pd.Series:
        """Calculate CCI feature."""
        cci = talib.CCI(data['high'], data['low'], data['close'], timeperiod=period)
        # Apply EMA smoothing if parameter_b > 1
        if parameter_b > 1:
            cci = talib.EMA(cci, timeperiod=parameter_b)
        return cci

    def calculate_adx_feature(self, data: pd.DataFrame, period: int, parameter_b: int) -> pd.Series:
        """Calculate ADX feature."""
        adx = talib.ADX(data['high'], data['low'], data['close'], timeperiod=period)
        # Apply EMA smoothing if parameter_b > 1
        if parameter_b > 1:
            adx = talib.EMA(adx, timeperiod=parameter_b)
        return adx

    def calculate_feature(self, feature: Feature, data: pd.DataFrame) -> pd.Series:
        """Calculate a single feature based on Feature(type, parameter_a, parameter_b)."""
        if feature.type == "RSI":
            return self.calculate_rsi_feature(data, feature.parameter_a, feature.parameter_b)
        elif feature.type == "WT":
            return self.calculate_wt_feature(data, feature.parameter_a, feature.parameter_b)
        elif feature.type == "CCI":
            return self.calculate_cci_feature(data, feature.parameter_a, feature.parameter_b)
        elif feature.type == "ADX":
            return self.calculate_adx_feature(data, feature.parameter_a, feature.parameter_b)
        else:
            raise ValueError(f"Unknown feature type: {feature.type}")

    def calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all features (RSI, WT, CCI, ADX, etc.) and return a DataFrame."""
        features_df = pd.DataFrame(index=data.index)
        for i, feat in enumerate(self.features[:self.settings.feature_count]):
            features_df[f'feature_{i+1}'] = self.calculate_feature(feat, data)
        return features_df

    # ----------------------------------------------------------------
    # (B) Filters & Lorentzian Distance
    # ----------------------------------------------------------------
    def apply_volatility_filter(self, data: pd.DataFrame) -> pd.Series:
        """Return True/False for each bar based on whether ATR(14) > ATR(28)."""
        atr14 = talib.ATR(data['high'], data['low'], data['close'], timeperiod=14)
        atr28 = talib.ATR(data['high'], data['low'], data['close'], timeperiod=28)
        return atr14 > atr28

    def calculate_lorentzian_distance(self, features: pd.DataFrame, idx: int) -> float:
        """
        Compute the Lorentzian distance between the most recent feature vector (the last row of features)
        and the historical feature vector at index `idx` by summing the logarithm of (1 + absolute difference)
        for each feature. This emulates the Pine Script logic.
        """
        if idx >= len(features):
            return float('inf')
        
        current_features = features.iloc[-1]
        historical_features = features.iloc[idx]
        
        distance = 0.0
        for col in features.columns:
            distance += math.log(1 + abs(current_features[col] - historical_features[col]))
        
        return distance

    # ----------------------------------------------------------------
    # (C) ML-Core: Kernel Regression, KNN, etc.
    # ----------------------------------------------------------------
    def rational_quadratic_kernel(self, data: pd.DataFrame) -> pd.Series:
        """
        Nadaraya-Watson Kernel Regression with Rational Quadratic Kernel.
        This matches the Pine Script implementation more closely.
        """
        h = self.settings.lookback_window
        r = self.settings.relative_weighting
        x = self.settings.regression_level
        
        source = data['close']
        kernel_sum = np.zeros(len(data))
        weight_sum = np.zeros(len(data))
        
        for i in range(len(data)):
            if i < h:
                continue
            for j in range(max(0, i - h), i):
                time_diff = i - j
                weight = (1 + (time_diff ** 2) / (2 * r * x)) ** (-r)
                kernel_sum[i] += weight * source.iloc[j]
                weight_sum[i] += weight

        kernel_est = kernel_sum / np.where(weight_sum == 0, 1, weight_sum)
        return pd.Series(kernel_est, index=data.index)
    
    def gaussian_kernel(self, data: pd.DataFrame, lag: int = 2) -> pd.Series:
        """
        Gaussian Kernel for smoothing, used for crossover detection.
        """
        h = max(1, self.settings.lookback_window - lag)
        x = self.settings.regression_level
        
        source = data['close']
        kernel_sum = np.zeros(len(data))
        weight_sum = np.zeros(len(data))
        
        for i in range(len(data)):
            if i < h:
                continue
            for j in range(max(0, i - h), i):
                time_diff = i - j
                weight = math.exp(-(time_diff ** 2) / (2 * x))
                kernel_sum[i] += weight * source.iloc[j]
                weight_sum[i] += weight

        kernel_est = kernel_sum / np.where(weight_sum == 0, 1, weight_sum)
        return pd.Series(kernel_est, index=data.index)

    def calculate_training_labels(self, data: pd.DataFrame, lookforward: int = 4) -> np.ndarray:
        """
        Label each bar as +1 if future price is higher after 'lookforward' bars,
        otherwise -1.
        """
        labels = np.zeros(len(data))
        for i in range(len(data) - lookforward):
            if data['close'].iloc[i + lookforward] > data['close'].iloc[i]:
                labels[i] = 1
            else:
                labels[i] = -1
        return labels

    def find_nearest_neighbors(self, features: pd.DataFrame, current_idx: int) -> List[Tuple[float, int]]:
        """
        KNN approach: find the k-nearest neighbors using 'calculate_lorentzian_distance'.
        This implementation more closely matches the Pine Script version.
        """
        distances = []
        predictions = []
        last_distance = -1.0
        max_bars_back = min(current_idx, self.settings.max_bars_back)
        size_loop = max_bars_back
        
        # This matches the Pine Script's loop structure more closely
        for i in range(max(0, current_idx - max_bars_back), current_idx):
            if i % 4 == 0:  # Skip every 4 bars for chronological spacing
                dist = self.calculate_lorentzian_distance(features, i)
                if dist >= last_distance:
                    distances.append(dist)
                    predictions.append(i)
                    if len(predictions) > self.settings.neighbors_count:
                        # Update last_distance to be in the lower 75% of distances
                        idx = math.floor(self.settings.neighbors_count * 3 / 4)
                        last_distance = sorted(distances)[idx] if idx < len(distances) else last_distance
                        # Remove the first element (oldest)
                        distances.pop(0)
                        predictions.pop(0)
        
        return list(zip(distances, predictions))

    def predict_next_bar(self, features: pd.DataFrame, labels: np.ndarray, current_idx: int) -> float:
        """
        Return a sum of the neighbors' labels => positive or negative value indicating bullish/bearish.
        This matches the Pine Script's prediction logic more closely.
        """
        if current_idx < self.settings.max_bars_back:
            return 0
        neighbors = self.find_nearest_neighbors(features, current_idx)
        if not neighbors:
            return 0
        
        # Get predictions from neighbors
        preds = [labels[n_idx] for _, n_idx in neighbors]
        # Return the sum of predictions (not the mean)
        return sum(preds)

    # ============= Filters =============
    def apply_regime_filter(self, data: pd.DataFrame) -> pd.Series:
        """
        Simple example: slope over 5 bars > regime_threshold => True, else False.
        """
        threshold = self.settings.regime_threshold
        slope = data['close'].diff(5)
        return slope > threshold

    def apply_adx_filter(self, data: pd.DataFrame) -> pd.Series:
        """Return True if ADX >= adx_threshold, else False."""
        adx_vals = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
        return adx_vals >= self.settings.adx_threshold

    def apply_ema_filter(self, data: pd.DataFrame) -> pd.Series:
        """
        Return True if close > EMA(ema_period), else False
        for an uptrend-only filter.
        """
        ema_vals = talib.EMA(data['close'], timeperiod=self.settings.ema_period)
        return data['close'] > ema_vals

    def apply_sma_filter(self, data: pd.DataFrame) -> pd.Series:
        sma_vals = talib.SMA(data['close'], timeperiod=self.settings.sma_period)
        return data['close'] > sma_vals

    def apply_dynamic_exits(self, signals: pd.Series, data: pd.DataFrame, kernel_est: pd.Series) -> pd.Series:
        """
        Implement dynamic exits based on kernel regression crossovers.
        This matches the Pine Script implementation more closely.
        """
        if not self.settings.use_dynamic_exits:
            return signals
        
        # Create a copy of signals to avoid modifying the original
        result = signals.copy()
        
        # Track entry and exit conditions
        last_signal_was_bullish = False
        last_signal_was_bearish = False
        bars_since_red_entry = float('inf')
        bars_since_red_exit = float('inf')
        bars_since_green_entry = float('inf')
        bars_since_green_exit = float('inf')
        
        # Kernel changes
        kernel_bullish_change = (kernel_est > kernel_est.shift(1)) & (kernel_est.shift(1) <= kernel_est.shift(2))
        kernel_bearish_change = (kernel_est < kernel_est.shift(1)) & (kernel_est.shift(1) >= kernel_est.shift(2))
        
        # Process signals
        for i in range(2, len(signals)):
            # Update bars since events
            if signals.iloc[i-1] == 1:  # Buy signal
                bars_since_green_entry = 0
                last_signal_was_bullish = True
                last_signal_was_bearish = False
            elif signals.iloc[i-1] == -1:  # Sell signal
                bars_since_red_entry = 0
                last_signal_was_bearish = True
                last_signal_was_bullish = False
            
            if kernel_bullish_change.iloc[i-1]:
                bars_since_green_exit = 0
            if kernel_bearish_change.iloc[i-1]:
                bars_since_red_exit = 0
            
            # Increment counters
            bars_since_green_entry += 1
            bars_since_red_entry += 1
            bars_since_green_exit += 1
            bars_since_red_exit += 1
            
            # Check for valid exits
            is_valid_short_exit = bars_since_red_exit > bars_since_red_entry
            is_valid_long_exit = bars_since_green_exit > bars_since_green_entry
            
            # Apply dynamic exits
            if kernel_bearish_change.iloc[i] and is_valid_long_exit and last_signal_was_bullish:
                result.iloc[i] = 0  # Exit long position
            elif kernel_bullish_change.iloc[i] and is_valid_short_exit and last_signal_was_bearish:
                result.iloc[i] = 0  # Exit short position
        
        return result

    # ----------------------------------------------------------------
    # (D) generate_signals_ml & run
    # ----------------------------------------------------------------
    def generate_signals_ml(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate signals using the ML approach with Lorentzian distance.
        This implementation closely matches the Pine Script version.
        """
        # 1) Calculate features, training labels, and kernel estimates
        feats = self.calculate_features(data)
        labels = self.calculate_training_labels(data)
        kernel_est = self.rational_quadratic_kernel(data)
        kernel_est2 = self.gaussian_kernel(data, self.settings.lag)

        # Initialize arrays for predictions and signals
        predictions = pd.Series(0, index=data.index, dtype=float)
        signals = pd.Series(0, index=data.index, dtype=int)
        
        # 2) KNN-like approach with Lorentzian distance
        for i in range(len(data)):
            if i < self.settings.max_bars_back:
                predictions.iloc[i] = 0
            else:
                # Find nearest neighbors and get prediction
                prediction = self.predict_next_bar(feats, labels, i)
                predictions.iloc[i] = prediction
        
        # 3) Convert predictions to signals
        for i in range(len(data)):
            if predictions.iloc[i] > 0:
                signals.iloc[i] = 1  # Buy signal
            elif predictions.iloc[i] < 0:
                signals.iloc[i] = -1  # Sell signal
            else:
                signals.iloc[i] = 0  # Neutral
        
        # 4) Apply filters
        # Create a copy of signals to avoid modifying the original during filtering
        filtered_signals = signals.copy()
        
        # Volatility filter
        if self.settings.use_volatility_filter:
            vol_filter = self.apply_volatility_filter(data)
            for i in range(len(filtered_signals)):
                if not vol_filter.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        # Kernel trend filter - always apply this
        kernel_bullish = kernel_est > kernel_est.shift(1)
        kernel_bearish = kernel_est < kernel_est.shift(1)
        
        for i in range(1, len(filtered_signals)):
            # Only allow buy signals when kernel is bullish
            if filtered_signals.iloc[i] == 1 and not kernel_bullish.iloc[i]:
                filtered_signals.iloc[i] = 0
            # Only allow sell signals when kernel is bearish
            elif filtered_signals.iloc[i] == -1 and not kernel_bearish.iloc[i]:
                filtered_signals.iloc[i] = 0
        
        # Kernel smoothing (crossover detection)
        if self.settings.enhance_kernel_smoothing:
            for i in range(1, len(filtered_signals)):
                # For buy signals, require kernel2 >= kernel
                if filtered_signals.iloc[i] == 1 and not (kernel_est2.iloc[i] >= kernel_est.iloc[i]):
                    filtered_signals.iloc[i] = 0
                # For sell signals, require kernel2 <= kernel
                elif filtered_signals.iloc[i] == -1 and not (kernel_est2.iloc[i] <= kernel_est.iloc[i]):
                    filtered_signals.iloc[i] = 0
        
        # Regime filter
        if self.settings.use_regime_filter:
            regime_filter = self.apply_regime_filter(data)
            for i in range(len(filtered_signals)):
                if not regime_filter.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        # ADX filter
        if self.settings.use_adx_filter:
            adx_filter = self.apply_adx_filter(data)
            for i in range(len(filtered_signals)):
                if not adx_filter.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        # EMA filter - only apply to buy signals
        if self.settings.use_ema_filter:
            ema_filter = self.apply_ema_filter(data)
            for i in range(len(filtered_signals)):
                if filtered_signals.iloc[i] == 1 and not ema_filter.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        # SMA filter - only apply to buy signals
        if self.settings.use_sma_filter:
            sma_filter = self.apply_sma_filter(data)
            for i in range(len(filtered_signals)):
                if filtered_signals.iloc[i] == 1 and not sma_filter.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        # 5) Handle dynamic exits
        filtered_signals = self.apply_dynamic_exits(filtered_signals, data, kernel_est)
        
        return filtered_signals

    def run(self, data: pd.DataFrame) -> Dict:
        """
        The default "run" method. 
        We'll assume you want the ML-based approach by default.
        """
        signals = self.generate_signals_ml(data)
        kernel = self.rational_quadratic_kernel(data)
        feats = self.calculate_features(data)
        
        # Print signal statistics
        buy_signals = len(signals[signals == 1])
        sell_signals = len(signals[signals == -1])
        neutral_signals = len(signals[signals == 0])
        total_signals = len(signals)
        
        print(f"\nLorentzian Signal Statistics:")
        print(f"Total bars: {total_signals}")
        print(f"Buy signals: {buy_signals} ({buy_signals/total_signals*100:.2f}%)")
        print(f"Sell signals: {sell_signals} ({sell_signals/total_signals*100:.2f}%)")
        print(f"Neutral signals: {neutral_signals} ({neutral_signals/total_signals*100:.2f}%)")
        
        return {
            'signals': signals,
            'kernel_estimate': kernel,
            'features': feats
        }
