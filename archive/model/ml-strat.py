from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

# Import the CryptoTradingModel you just created
from pytorch_trading_model import CryptoTradingModel, prepare_indicator_features

# Import your existing strategy base and components
from src.utils.strategy.base import BaseStrategy
from src.utils.indicators import (
    RsiIndicator, 
    SupertrendIndicator, 
    LorentzianIndicator, 
    MacdIndicator
)

class MLEnhancedStrategy(BaseStrategy):
    """
    Trading strategy that combines traditional indicators with PyTorch ML predictions.
    This strategy:
    1. Uses your existing indicators to generate signals
    2. Enhances those signals with ML model predictions
    3. Combines both signal sources with configurable weights
    """
    
    def __init__(self, config: Dict, indicators: List, weights: Optional[List[float]] = None,
                 ml_model_path: str = 'models/sol_trading_model.pth', ml_weight: float = 0.5):
        """
        Initialize the ML-enhanced strategy.
        
        Args:
            config: Configuration dictionary
            indicators: List of indicator objects implementing generate_signals(df)
            weights: Optional weights for indicators
            ml_model_path: Path to the saved PyTorch model
            ml_weight: Weight given to ML signals (0-1)
        """
        super().__init__(config)
        
        # Traditional strategy components
        self.indicators = indicators
        self.weights = weights if weights is not None else [1] * len(indicators)
        self.threshold = self.config.get("consensus_threshold", 0)
        
        # ML components
        self.ml_model = CryptoTradingModel()
        if Path(ml_model_path).exists():
            self.ml_model.load_model(ml_model_path)
            self.use_ml = True
        else:
            print(f"Warning: No model found at {ml_model_path}. ML enhancement disabled.")
            self.use_ml = False
            
        self.ml_weight = ml_weight
        self.indicator_weight = 1.0 - ml_weight
        self.lookback = 10  # Must match the lookback used in training
        
        # Performance tracking
        self.signal_sources = {
            'indicator_signals': [],
            'ml_signals': [],
            'combined_signals': []
        }
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals using both traditional indicators and ML predictions.
        
        Args:
            df: DataFrame with OHLCV market data
            
        Returns:
        MLEnhancedStrategy: Configured strategy instance
    """
    # Create individual indicators
    rsi = RsiIndicator()
    supertrend = SupertrendIndicator()
    lorentzian = LorentzianIndicator()
    macd = MacdIndicator()
    
    # List of indicators
    indicators = [
        rsi,
        supertrend, 
        lorentzian,
        macd
    ]
    
    # Weights for indicators (modify as needed)
    weights = [1.5, 2.0, 2.0, 1.0]
    
    # Check if ML model file exists
    model_path = config.get('ml_model_path', 'models/sol_trading_model.pth')
    ml_weight = config.get('ml_weight', 0.5)
    
    # Create and return the strategy
    return MLEnhancedStrategy(
        config=config,
        indicators=indicators,
        weights=weights,
        ml_model_path=model_path,
        ml_weight=ml_weight
    )


def example_strategy_usage():
    """
    Example showing how to use the MLEnhancedStrategy in your trading system.
    """
    from datetime import datetime, timedelta
    import asyncio
    from src.core.config import StorageConfig
    from src.storage.processed import ProcessedDataStorage
    import matplotlib.pyplot as plt
    
    # 1. Load historical data
    async def load_data():
        config = StorageConfig()
        storage = ProcessedDataStorage(config)
        
        # Define date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # 60 days of data
        
        # Load SOL/USDT data
        return await storage.load_candles(
            exchange="binance", 
            market="SOL/USDT", 
            resolution="1h",  # Hourly data
            start_time=start_date,
            end_time=end_date
        )
    
    # Run async function to get data
    df = asyncio.run(load_data())
    
    if df is None or len(df) == 0:
        print("No data available. Please check your data storage configuration.")
        return
    
    # 2. Create strategy configuration
    strategy_config = {
        "consensus_threshold": 0.2,
        "ml_model_path": "models/sol_trading_model.pth",
        "ml_weight": 0.6  # Give more weight to ML signals
    }
    
    # 3. Create the ML-enhanced strategy
    strategy = create_ml_strategy(strategy_config)
    
    # 4. Generate signals
    signals = strategy.generate_signals(df)
    
    # 5. Print performance metrics
    metrics = strategy.get_performance_metrics()
    print("\nPerformance Metrics:")
    print(f"Indicator-ML Agreement: {metrics['indicator_ml_agreement']:.4f}")
    print(f"ML Weight: {metrics['ml_weight']}")
    print(f"Indicator Weight: {metrics['indicator_weight']}")
    print("Signal Counts:")
    for signal_type, count in metrics['signal_counts'].items():
        print(f"  {signal_type.capitalize()}: {count}")
    
    # 6. Visualize signals
    plt.figure(figsize=(15, 10))
    
    # Plot price
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='SOL Price')
    
    # Add buy/sell markers
    buy_signals = df.index[signals == 1]
    sell_signals = df.index[signals == -1]
    
    plt.scatter(buy_signals, df.loc[buy_signals, 'close'], 
                marker='^', color='green', s=100, label='Buy')
    plt.scatter(sell_signals, df.loc[sell_signals, 'close'], 
                marker='v', color='red', s=100, label='Sell')
    
    plt.title('SOL/USDT with ML-Enhanced Strategy Signals')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    
    # Plot signal components
    plt.subplot(2, 1, 2)
    plt.plot(df.index, strategy.signal_sources['indicator_signals'], 
             label='Indicator Signals', alpha=0.7)
    plt.plot(df.index, strategy.signal_sources['ml_signals'], 
             label='ML Signals', alpha=0.7)
    plt.plot(df.index, strategy.signal_sources['combined_signals'], 
             label='Combined Signals', linewidth=2)
    
    plt.title('Signal Components')
    plt.xlabel('Date')
    plt.ylabel('Signal Strength')
    plt.legend()
    
    plt.tight_layout()
    plt.show()
    
    print("\nStrategy analysis complete!")


if __name__ == "__main__":
    # Run the example when executing the file directly
    example_strategy_usage():
            pd.Series: Trading signals (1=long, -1=short, 0=neutral)
        """
        # 1. Get traditional indicator signals
        indicator_signals = self._get_indicator_signals(df)
        
        # 2. Get ML model signals if available
        ml_signals = self._get_ml_signals(df) if self.use_ml else pd.Series(0, index=df.index)
        
        # 3. Combine signals with weights
        combined_signals = (
            indicator_signals * self.indicator_weight + 
            ml_signals * self.ml_weight
        )
        
        # 4. Apply threshold to get final signals
        final_signals = combined_signals.apply(
            lambda x: 1 if x > self.threshold else (-1 if x < -self.threshold else 0)
        )
        
        # 5. Store signals for analysis
        self.signal_sources['indicator_signals'] = indicator_signals
        self.signal_sources['ml_signals'] = ml_signals
        self.signal_sources['combined_signals'] = combined_signals
        
        return final_signals
    
    def _get_indicator_signals(self, df: pd.DataFrame) -> pd.Series:
        """Get weighted consensus signals from traditional indicators"""
        weighted_signals = []
        
        for indicator, weight in zip(self.indicators, self.weights):
            signals = indicator.generate_signals(df)
            weighted_signals.append(signals * weight)
            
        if not weighted_signals:
            return pd.Series(0, index=df.index)
            
        combined_df = pd.concat(weighted_signals, axis=1)
        return combined_df.sum(axis=1)
    
    def _get_ml_signals(self, df: pd.DataFrame) -> pd.Series:
        """Get signals from the PyTorch ML model"""
        if not self.use_ml:
            return pd.Series(0, index=df.index)
            
        # Prepare features for the model
        features_df = prepare_indicator_features(df)
        feature_columns = [col for col in features_df.columns if col != 'close']
        
        # Initialize signals with zeros
        ml_signals = pd.Series(0, index=df.index)
        
        # Generate signals only for valid data points
        for i in range(self.lookback, len(df)):
            # Skip if we don't have enough lookback data
            if i - self.lookback < 0:
                continue
                
            # Create feature sequence for this position
            try:
                # Extract features for the lookback window
                lookback_features = []
                for j in range(i - self.lookback, i):
                    if j < len(features_df):
                        row_features = [features_df.iloc[j][col] for col in feature_columns]
                        lookback_features.extend(row_features)
                
                # Get model prediction
                features_array = np.array(lookback_features)
                
                # Skip if we have NaN values
                if np.isnan(features_array).any():
                    continue
                    
                # Get signal from model
                ml_signals.iloc[i] = self.ml_model.get_signal(features_array)
                
            except Exception as e:
                print(f"Error getting ML prediction at index {i}: {e}")
                ml_signals.iloc[i] = 0
        
        return ml_signals
    
    def get_performance_metrics(self) -> Dict:
        """
        Get performance metrics for analysis.
        
        Returns:
            Dict: Signal analysis and other metrics
        """
        indicator_signals = self.signal_sources['indicator_signals']
        ml_signals = self.signal_sources['ml_signals']
        
        # Calculate agreement between indicator and ML signals
        if len(indicator_signals) > 0 and len(ml_signals) > 0:
            agreement = (indicator_signals * ml_signals).apply(lambda x: 1 if x > 0 else 0).mean()
        else:
            agreement = 0
            
        return {
            'indicator_ml_agreement': agreement,
            'ml_weight': self.ml_weight,
            'indicator_weight': self.indicator_weight,
            'signal_counts': {
                'buy': (self.signal_sources['combined_signals'] > 0).sum(),
                'sell': (self.signal_sources['combined_signals'] < 0).sum(),
                'neutral': (self.signal_sources['combined_signals'] == 0).sum()
            }
        }


# Example usage
def create_ml_strategy(config: Dict):
    """
    Create an ML-enhanced trading strategy with your indicators.
    
    Args:
        config: Strategy configuration dictionary
        
    Returns