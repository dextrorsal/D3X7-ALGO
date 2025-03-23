"""
Simple test for data fetching using the Binance exchange
and testing indicators on the fetched data.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Remove any existing paths and add only the current project root
sys.path = [p for p in sys.path if 'ultimate_data_fetcher' not in p]
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Test data fetching and indicators"""
    logger.info("Starting data fetching and indicator test")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Python path: {sys.path}")
    
    try:
        from src.core.config import Config, ExchangeConfig, ExchangeCredentials
        from src.core.models import TimeRange
        from src.exchanges.binance import BinanceHandler
        
        logger.info("✅ Successfully imported core modules")
        
        # Try to import one indicator
        try:
            from src.utils.indicators.rsi import RsiIndicator
            logger.info("✅ Successfully imported RSI indicator")
            has_indicator = True
        except ImportError as e:
            logger.error(f"❌ Could not import RSI indicator: {e}")
            logger.error(f"Looking in: {os.path.join(project_root, 'src/utils/indicators/rsi.py')}")
            has_indicator = False
        
        # Create a simple configuration for Binance
        exchange_config = ExchangeConfig(
            name="binance",
            credentials=None,  # No need for public API
            rate_limit=5,
            markets=["BTCUSDT", "ETHUSDT", "SOLUSDT"],  # Using Binance's native format
            base_url="https://api.binance.com",
            enabled=True
        )
        
        # Initialize the exchange handler
        handler = BinanceHandler(exchange_config)
        
        # Connect to the exchange
        await handler.start()
        logger.info("✅ Successfully connected to Binance")
        
        try:
            # Define a time range for the last 2 days
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=2)
            time_range = TimeRange(start=start_time, end=end_time)
            
            # Fetch candles for BTC/USDT
            logger.info(f"Fetching BTC/USDT data from {start_time} to {end_time}")
            candles = await handler.fetch_historical_candles(
                market="BTCUSDT",  # Using Binance's native format
                time_range=time_range,
                resolution="1h"  # 1-hour timeframe
            )
            
            if candles and len(candles) > 0:
                logger.info(f"✅ Successfully fetched {len(candles)} candles")
                
                # Convert candles to DataFrame
                df = pd.DataFrame([
                    {
                        'timestamp': candle.timestamp,
                        'open': candle.open,
                        'high': candle.high,
                        'low': candle.low,
                        'close': candle.close,
                        'volume': candle.volume
                    }
                    for candle in candles
                ])
                
                # Set timestamp as index
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                logger.info(f"Data range: {df.index.min()} to {df.index.max()}")
                logger.info(f"Data sample:\n{df.head()}")
                
                # Test RSI indicator if available
                if has_indicator:
                    rsi = RsiIndicator()
                    df['RSI_Signal'] = rsi.generate_signals(df)
                    
                    # Count signals
                    buy_count = (df['RSI_Signal'] == 1).sum()
                    sell_count = (df['RSI_Signal'] == -1).sum()
                    neutral_count = (df['RSI_Signal'] == 0).sum()
                    
                    logger.info(f"RSI Signals: Buy={buy_count}, Sell={sell_count}, Neutral={neutral_count}")
                    
                    # Create a plot
                    plt.figure(figsize=(12, 8))
                    
                    # Plot price
                    plt.subplot(2, 1, 1)
                    plt.plot(df.index, df['close'], label='Close Price', color='black')
                    
                    # Plot buy signals
                    buys = df[df['RSI_Signal'] == 1]
                    plt.scatter(buys.index, buys['close'], marker='^', color='green', s=100, label='Buy')
                    
                    # Plot sell signals
                    sells = df[df['RSI_Signal'] == -1]
                    plt.scatter(sells.index, sells['close'], marker='v', color='red', s=100, label='Sell')
                    
                    plt.title("BTC/USDT with RSI Signals")
                    plt.legend()
                    
                    # Save plot
                    os.makedirs('reports', exist_ok=True)
                    plt.savefig('reports/btc_rsi_signals.png')
                    logger.info("✅ Plot saved to reports/btc_rsi_signals.png")
            else:
                logger.error("❌ No candles fetched")
        except Exception as e:
            logger.error(f"❌ Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            
        # Disconnect from the exchange
        await handler.stop()
        logger.info("Disconnected from Binance")
    
    except Exception as e:
        logger.error(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())