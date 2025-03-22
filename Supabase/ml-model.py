from pytorch_trading_model import CryptoTradingModel, prepare_indicator_features
from supabase_adapter import SupabaseAdapter
import pandas as pd
import asyncio
from datetime import datetime, timedelta

async def generate_predictions():
    """Generate and store ML predictions."""
    # Initialize Supabase adapter
    adapter = SupabaseAdapter("YOUR_SUPABASE_URL", "YOUR_SUPABASE_API_KEY")
    
    # Load your trained model
    model = CryptoTradingModel()
    model.load_model("models/SOL_USDT_model.pth")
    
    # Define pairs and timeframes
    pairs = [
        {"exchange": "binance", "market": "SOL/USDT"},
        {"exchange": "binance", "market": "BTC/USDT"},
        {"exchange": "binance", "market": "ETH/USDT"}
    ]
    
    timeframes = ["1h"]  # Add more as needed: ["1m", "5m", "15m", "30m", "1h"]
    
    # Set time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)  # Get last 7 days of data
    
    for pair in pairs:
        for timeframe in timeframes:
            print(f"Processing {pair['exchange']} {pair['market']} {timeframe}")
            
            # Load candles from Supabase
            df = await adapter.load_candles(
                pair["exchange"], 
                pair["market"], 
                timeframe, 
                start_time, 
                end_time
            )
            
            if df.empty:
                print(f"No data found for {pair['market']} {timeframe}")
                continue
            
            # Prepare features
            features_df = prepare_indicator_features(df)
            feature_columns = [col for col in features_df.columns if col != 'close']
            
            # Generate predictions for each candle
            for i in range(10, len(features_df)):
                # Create feature sequence for this position
                try:
                    # Extract features for the lookback window
                    lookback_features = []
                    for j in range(i - 10, i):
                        row_features = [features_df.iloc[j][col] for col in feature_columns]
                        lookback_features.extend(row_features)
                    
                    # Get model prediction
                    features_array = np.array(lookback_features)
                    
                    # Skip if we have NaN values
                    if np.isnan(features_array).any():
                        continue
                        
                    # Get prediction from model
                    direction_prob, predicted_change = model.predict(features_array)
                    signal = model.get_signal(features_array)
                    
                    # Store prediction
                    timestamp = df.iloc[i]['timestamp'] if 'timestamp' in df.columns else df.index[i]
                    
                    await adapter.store_prediction(
                        pair["exchange"],
                        pair["market"],
                        timeframe,
                        timestamp,
                        "pytorch_v1.0",
                        direction_prob,
                        predicted_change,
                        signal
                    )
                    
                except Exception as e:
                    print(f"Error generating prediction: {e}")
    
    print("Prediction generation complete!")

if __name__ == "__main__":
    asyncio.run(generate_predictions())