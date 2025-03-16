# src/utils/indicators/wrapper_lorentzian.py

import pandas as pd
import numpy as np
from .lorentzian import LorentzianClassification, LorentzianSettings, Feature # Updated: Relative import
from .base_indicator import BaseIndicator # Updated: Relative import
from src.core.config import Config # Removed or Updated if needed, corrected path, only if used


class LorentzianIndicator(BaseIndicator):
    def __init__(self, config_path='config/indicator_settings.json', **kwargs):
        config = Config()
        lorentzian_config = config.get('indicators', {}).get('lorentzian', {})
        
        general_settings = lorentzian_config.get('general_settings', {})
        filter_settings = lorentzian_config.get('filters', {})
        kernel_settings = lorentzian_config.get('kernel_settings', {})
        
        # Load features from config
        features_config = lorentzian_config.get('features', [])
        features = []
        for feature_config in features_config:
            features.append(Feature(
                type=feature_config.get('type', 'RSI'),
                parameter_a=feature_config.get('parameter_a', 14),
                parameter_b=feature_config.get('parameter_b', 1)
            ))
        
        # If no features in config, use defaults
        if not features:
            features = [
                Feature("RSI", 14, 1),
                Feature("WT", 10, 11),
                Feature("CCI", 20, 1),
                Feature("ADX", 20, 2),
                Feature("RSI", 9, 1)
            ]

        settings = LorentzianSettings(
            neighbors_count = general_settings.get('neighbors_count', 8),
            max_bars_back = general_settings.get('max_bars_back', 2000),
            feature_count = min(5, len(features)),  # Use at most 5 features
            color_compression = general_settings.get('color_compression', 1),
            use_volatility_filter = filter_settings.get('use_volatility_filter', True),
            use_regime_filter = filter_settings.get('use_regime_filter', False),
            regime_threshold = filter_settings.get('regime_threshold', -0.1),
            use_adx_filter = filter_settings.get('use_adx_filter', False),
            adx_threshold = filter_settings.get('adx_threshold', 20),
            use_ema_filter = filter_settings.get('use_ema_filter', False),
            ema_period = filter_settings.get('ema_period', 200),
            use_sma_filter = filter_settings.get('use_sma_filter', False),
            sma_period = filter_settings.get('sma_period', 200),
            use_worst_case_estimates = general_settings.get('use_worst_case_estimates', False),
            use_dynamic_exits = general_settings.get('use_dynamic_exits', False),
            enhance_kernel_smoothing = kernel_settings.get('enhance_kernel_smoothing', False),
            lag = kernel_settings.get('lag', 2),
            # Add kernel settings
            lookback_window = kernel_settings.get('lookback_window', 8),
            relative_weighting = kernel_settings.get('relative_weighting', 8.0),
            regression_level = kernel_settings.get('regression_level', 25),
            show_kernel_estimate = kernel_settings.get('show_kernel_estimate', True)
        )

        self.model = LorentzianClassification(settings)
        # Set features explicitly
        self.model.features = features
        
        # Add fallback parameters for signal generation
        self.fast_ma_period = kwargs.get('fast_ma_period', 10)
        self.slow_ma_period = kwargs.get('slow_ma_period', 30)
    
    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expose LorentzianClassification's feature calculation method
        through this wrapper.
        """
        return self.model.calculate_features(df) 

    # NEW: Pass-through method to compute distances
    def calculate_distances(self, features: pd.DataFrame, idx: int) -> list:
        """
        Calculate distances for a given index.
        Here, we simply delegate to the model's calculate_lorentzian_distance method
        and return it in a list (so the calling code can compute a mean, etc.).
        """
        distance = self.model.calculate_lorentzian_distance(features, idx)
        return [distance]
    
    # NEW: Pass-through method to get an adaptive threshold
    def get_adaptive_threshold(self, distances: list) -> float:
        """
        Calculate an adaptive threshold based on the list of distances.
        For example, we return the mean of the distances as a simple threshold.
        """
        return np.mean(distances)    

    def generate_fallback_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate signals using a simple moving average crossover strategy as a fallback
        when the Lorentzian model doesn't produce signals.
        """
        signals = pd.Series(0, index=df.index)
        
        # Calculate fast and slow moving averages
        fast_ma = df['close'].rolling(window=self.fast_ma_period).mean()
        slow_ma = df['close'].rolling(window=self.slow_ma_period).mean()
        
        # Generate signals based on crossovers
        for i in range(self.slow_ma_period, len(df)):
            if fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                signals.iloc[i] = 1  # Buy signal
            elif fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                signals.iloc[i] = -1  # Sell signal
        
        return signals
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals using Lorentzian Classification"""
        try:
            # Initialize signals
            signals = pd.Series(0, index=df.index)
            
            # Ensure minimum data length
            min_required = 20  # Minimum for TA calculations
            if len(df) < min_required:
                print(f"Insufficient data: need at least {min_required} points")
                return signals
            
            print("Running Lorentzian model...")
            # Run the model
            result = self.model.run(df)
            
            if result is None:
                print("No results from Lorentzian model, using fallback strategy")
                return self.generate_fallback_signals(df)
            
            # Extract and process signals
            if isinstance(result, dict) and 'signals' in result:
                model_signals = result['signals']
                if isinstance(model_signals, pd.Series):
                    signals = model_signals
            
            # If no buy or sell signals were generated, use the fallback strategy
            if len(signals[signals != 0]) == 0:
                print("Lorentzian model didn't generate any non-zero signals, using fallback strategy")
                return self.generate_fallback_signals(df)
            
            return signals
            
        except Exception as e:
            print(f"Error in Lorentzian signal generation: {str(e)}")
            print("Error details:")
            import traceback
            traceback.print_exc()
            print("Using fallback strategy due to error")
            return self.generate_fallback_signals(df)