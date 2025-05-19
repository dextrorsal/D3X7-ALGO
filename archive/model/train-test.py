import os
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Import our model
from pytorch_trading_model import CryptoTradingModel, prepare_indicator_features

# Import storage and indicators
from src.core.config import StorageConfig
from src.storage.processed import ProcessedDataStorage
from src.utils.indicators import (
    RsiIndicator, 
    SupertrendIndicator, 
    LorentzianIndicator, 
    MacdIndicator, 
    BollingerBandsIndicator,
    StochasticIndicator
)

async def load_historical_data(symbol, resolution="1h", days=180):
    """
    Load historical OHLCV data for the specified symbol.
    
    Args:
        symbol: Trading pair (e.g., "SOL/USDT")
        resolution: Candle timeframe (e.g., "1h", "4h", "1d")
        days: Number of days of historical data to load
        
    Returns:
        DataFrame with OHLCV data
    """
    config = StorageConfig()
    storage = ProcessedDataStorage(config)
    
    # Define date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Extract exchange and market from symbol
    parts = symbol.split('/')
    if len(parts) != 2:
        raise ValueError(f"Invalid symbol format: {symbol}. Expected format like 'SOL/USDT'")
    
    # Our storage might store this as binance, bybit, etc.
    # Try the most common exchanges
    exchanges = ["binance", "bybit", "ftx", "kraken", "coinbase"]
    
    for exchange in exchanges:
        try:
            df = await storage.load_candles(
                exchange=exchange,
                market=symbol,
                resolution=resolution,
                start_time=start_date,
                end_time=end_date
            )
            
            if df is not None and len(df) > 0:
                print(f"Successfully loaded {len(df)} candles from {exchange} for {symbol}")
                return df
        except Exception as e:
            print(f"Error loading data from {exchange}: {e}")
    
    print(f"Could not load data for {symbol} from any exchange")
    return None

def calculate_indicators(df):
    """
    Calculate technical indicators for the given DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with indicators added
    """
    # Create indicator instances
    rsi = RsiIndicator()
    supertrend = SupertrendIndicator()
    lorentzian = LorentzianIndicator()
    macd = MacdIndicator()
    bbands = BollingerBandsIndicator()
    stoch = StochasticIndicator()
    
    # Generate signals
    df['rsi_signal'] = rsi.generate_signals(df)
    df['supertrend_signal'] = supertrend.generate_signals(df)
    df['lorentzian_signal'] = lorentzian.generate_signals(df)
    df['macd_signal'] = macd.generate_signals(df)
    df['bbands_signal'] = bbands.generate_signals(df)
    df['stoch_signal'] = stoch.generate_signals(df)
    
    # Calculate raw indicator values using talib
    import talib
    
    # RSI
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    
    # MACD
    macd, macdsignal, macdhist = talib.MACD(
        df['close'], 
        fastperiod=12, 
        slowperiod=26, 
        signalperiod=9
    )
    df['macd'] = macd
    df['macd_signal_line'] = macdsignal
    df['macd_hist'] = macdhist
    
    # Bollinger Bands
    upperband, middleband, lowerband = talib.BBANDS(
        df['close'], 
        timeperiod=20, 
        nbdevup=2, 
        nbdevdn=2
    )
    df['bb_upper'] = upperband
    df['bb_middle'] = middleband
    df['bb_lower'] = lowerband
    
    # Stochastic
    slowk, slowd = talib.STOCH(
        df['high'], 
        df['low'], 
        df['close'], 
        fastk_period=14, 
        slowk_period=3, 
        slowk_matype=0, 
        slowd_period=3, 
        slowd_matype=0
    )
    df['stoch_k'] = slowk
    df['stoch_d'] = slowd
    
    # ADX
    df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    
    # Williams %R
    df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=14)
    
    # Additional features
    df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    df['daily_return'] = df['close'].pct_change()
    df['volatility'] = df['daily_return'].rolling(window=14).std()
    
    # Moving averages
    df['sma_10'] = talib.SMA(df['close'], timeperiod=10)
    df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
    df['ema_10'] = talib.EMA(df['close'], timeperiod=10)
    df['ema_50'] = talib.EMA(df['close'], timeperiod=50)
    
    # Create price-based patterns
    df['ma_crossover'] = (df['sma_10'] > df['sma_50']).astype(int) * 2 - 1
    
    # Drop NaN values
    df = df.dropna()
    
    return df

async def main():
    """Main function to train and test the model"""
    # Create models directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Define trading pairs to analyze
    symbols = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT']
    
    # Load and process data for each symbol
    for symbol in symbols:
        print(f"\n=== Processing {symbol} ===")
        
        # 1. Load historical data
        df = await load_historical_data(symbol, resolution="1h", days=180)
        if df is None or len(df) < 100:
            print(f"Not enough data for {symbol}, skipping...")
            continue
            
        # 2. Calculate indicators
        print(f"Calculating indicators for {symbol}...")
        df = calculate_indicators(df)
        
        # 3. Prepare features
        print(f"Preparing features for {symbol}...")
        features_df = prepare_indicator_features(df)
        
        # Define feature columns to use (all except close)
        feature_columns = [col for col in features_df.columns if col != 'close']
        
        # Print available features
        print(f"Using {len(feature_columns)} features: {', '.join(feature_columns[:5])}...")
        
        # 4. Initialize model with custom configuration
        model = CryptoTradingModel(config={
            'hidden_size': 128,           # Larger network
            'num_layers': 3,              # Deeper network
            'dropout': 0.3,               # Stronger regularization
            'learning_rate': 0.0005,      # Smaller learning rate
            'batch_size': 32,             # Smaller batch size
            'num_epochs': 100,            # Train for more epochs
            'train_test_split': 0.2,      # 20% test data
            'class_weight': 1.0,          # Equal weight for classification
            'regr_weight': 0.5            # Less weight for regression
        })
        
        # 5. Train the model
        print(f"Training model for {symbol}...")
        history = model.train(
            df=features_df,
            feature_columns=feature_columns,
            target_column='close',
            lookback=10
        )
        
        # 6. Plot training history
        plt.figure(figsize=(15, 10))
        
        # Plot training and test loss
        plt.subplot(2, 2, 1)
        plt.plot(history['train_loss'], label='Train Loss')
        plt.plot(history['test_loss'], label='Test Loss')
        plt.title(f'Model Loss - {symbol}')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        # Plot classification accuracy
        plt.subplot(2, 2, 2)
        plt.plot(history['class_accuracy'])
        plt.title(f'Classification Accuracy - {symbol}')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        
        # Plot regression MSE
        plt.subplot(2, 2, 3)
        plt.plot(history['regr_mse'])
        plt.title(f'Regression MSE - {symbol}')
        plt.xlabel('Epoch')
        plt.ylabel('MSE')
        
        plt.tight_layout()
        plt.savefig(f"models/{symbol.replace('/', '_')}_training.png")
        plt.close()
        
        # 7. Save the model
        model_path = f"models/{symbol.replace('/', '_')}_model.pth"
        model.save_model(model_path)
        print(f"Model saved to {model_path}")
        
        # 8. Calculate and display feature importance
        X, y = model.prepare_data(features_df, feature_columns, 'close', lookback=10)
        importance = model.feature_importance(X, feature_columns)
        
        # Plot feature importance
        plt.figure(figsize=(12, 8))
        
        # Get top 15 features
        top_features = dict(sorted(importance.items(), key=lambda item: item[1], reverse=True)[:15])
        
        # Create bar plot
        plt.barh(list(top_features.keys()), list(top_features.values()))
        plt.title(f'Top 15 Feature Importance - {symbol}')
        plt.xlabel('Importance Score')
        plt.tight_layout()
        plt.savefig(f"models/{symbol.replace('/', '_')}_importance.png")
        plt.close()
        
        # Print top 10 features
        print(f"\nTop 10 Features for {symbol}:")
        for i, (feature, score) in enumerate(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]):
            print(f"{i+1}. {feature}: {score:.4f}")
        
        # 9. Backtest the model on validation data
        print(f"\nBacktesting model for {symbol}...")
        
        # Get validation data (last 20% of the dataset)
        val_start_idx = int(len(df) * 0.8)
        val_df = df.iloc[val_start_idx:]
        
        # Generate signals
        signals = pd.Series(0, index=val_df.index)
        
        # Get features for validation data
        val_features = prepare_indicator_features(val_df)
        val_feature_cols = [col for col in val_features.columns if col != 'close']
        
        # Generate signals for validation data
        for i in range(10, len(val_features)):
            # Create feature sequence
            try:
                lookback_features = []
                for j in range(i - 10, i):
                    if j < len(val_features):
                        row_features = [val_features.iloc[j][col] for col in val_feature_cols if col in val_features.columns]
                        lookback_features.extend(row_features)
                
                features_array = np.array(lookback_features)
                
                # Skip if we have NaN values
                if np.isnan(features_array).any():
                    continue
                    
                # Get signal from model
                signals.iloc[i] = model.get_signal(features_array)
                
            except Exception as e:
                print(f"Error at index {i}: {e}")
                signals.iloc[i] = 0
        
        # Calculate performance metrics
        val_df['signal'] = signals
        val_df['next_return'] = val_df['close'].pct_change(1).shift(-1)
        val_df['strategy_return'] = val_df['signal'] * val_df['next_return']
        
        # Calculate cumulative returns
        val_df['cumulative_market_return'] = (1 + val_df['next_return']).cumprod() - 1
        val_df['cumulative_strategy_return'] = (1 + val_df['strategy_return']).cumprod() - 1
        
        # Plot performance
        plt.figure(figsize=(15, 10))
        
        # Plot price and signals
        plt.subplot(2, 1, 1)
        plt.plot(val_df.index, val_df['close'], label='Price')
        
        # Add buy/sell markers
        buy_signals = val_df.index[val_df['signal'] == 1]
        sell_signals = val_df.index[val_df['signal'] == -1]
        
        plt.scatter(buy_signals, val_df.loc[buy_signals, 'close'], 
                    marker='^', color='green', s=100, label='Buy')
        plt.scatter(sell_signals, val_df.loc[sell_signals, 'close'], 
                    marker='v', color='red', s=100, label='Sell')
        
        plt.title(f'{symbol} Price with ML Model Signals')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        
        # Plot returns
        plt.subplot(2, 1, 2)
        plt.plot(val_df.index, val_df['cumulative_market_return'], 
                 label='Market Return', alpha=0.7)
        plt.plot(val_df.index, val_df['cumulative_strategy_return'], 
                 label='Strategy Return', linewidth=2)
        
        plt.title(f'{symbol} Performance Comparison')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(f"models/{symbol.replace('/', '_')}_backtest.png")
        plt.close()
        
        # Print performance metrics
        market_return = val_df['cumulative_market_return'].iloc[-1]
        strategy_return = val_df['cumulative_strategy_return'].iloc[-1]
        
        print(f"\nBacktest Results for {symbol}:")
        print(f"Market Return: {market_return:.2%}")
        print(f"Strategy Return: {strategy_return:.2%}")
        print(f"Outperformance: {strategy_return - market_return:.2%}")
        
        # Win rate
        wins = (val_df['strategy_return'] > 0).sum()
        total_trades = (val_df['signal'] != 0).sum()
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        print(f"Win Rate: {win_rate:.2%} ({wins} / {total_trades})")
        print(f"Average Return per Trade: {val_df['strategy_return'].mean():.4%}")
        
        # Calculate Sharpe Ratio
        risk_free_rate = 0.02  # 2% annual risk-free rate
        daily_risk_free = (1 + risk_free_rate) ** (1/365) - 1
        excess_returns = val_df['strategy_return'] - daily_risk_free
        sharpe_ratio = np.sqrt(365) * (excess_returns.mean() / excess_returns.std())
        
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"Max Drawdown: {(val_df['cumulative_strategy_return'].min()):.2%}")
        
        print(f"\n=== Completed analysis for {symbol} ===\n")
    
    print("\nAll models trained and tested!")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())