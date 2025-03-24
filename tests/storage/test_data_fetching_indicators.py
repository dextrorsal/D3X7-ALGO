"""
Simple test script for data fetching and indicators
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Test data fetching and indicators
    """
    logger.info("Starting test script for data fetching and indicators")
    
    # Import modules here to handle import errors gracefully
    try:
        from src.core.config import Config
        from src.core.models import TimeRange
        from src.ultimate_fetcher import UltimateDataFetcher
        
        logger.info("✅ Successfully imported data fetching modules")
    except ImportError as e:
        logger.error(f"❌ Failed to import data fetching modules: {str(e)}")
        return
    
    # Test indicators import
    try:
        from src.utils.indicators.wrapper_rsi import RSIIndicator
        from src.utils.indicators.wrapper_macd import MACDIndicator
        from src.utils.indicators.wrapper_bollinger_bands import BollingerBandsIndicator
        from src.utils.indicators.wrapper_supertrend import SupertrendIndicator
        
        logger.info("✅ Successfully imported indicator modules")
    except ImportError as e:
        logger.error(f"❌ Failed to import indicator modules: {str(e)}")
    
    # Initialize data fetcher
    try:
        config = Config(".env")
        fetcher = UltimateDataFetcher(config=config)
        logger.info("✅ Successfully initialized data fetcher")
    except Exception as e:
        logger.error(f"❌ Failed to initialize data fetcher: {str(e)}")
        return
    
    # Test availability of exchange handlers
    try:
        await fetcher.start()
        logger.info(f"✅ Successfully started data fetcher")
        
        # Print available exchanges
        available_exchanges = list(fetcher.exchange_handlers.keys())
        logger.info(f"Available exchanges: {available_exchanges}")
        
        # Test market availability for each exchange
        for exchange_name, handler in fetcher.exchange_handlers.items():
            try:
                if hasattr(handler, "get_markets"):
                    markets = await handler.get_markets()
                    logger.info(f"✅ {exchange_name}: Found {len(markets)} markets")
                    if markets:
                        logger.info(f"Sample markets: {markets[:5]}")
                else:
                    logger.warning(f"⚠️ {exchange_name}: No get_markets method available")
            except Exception as e:
                logger.error(f"❌ {exchange_name}: Error getting markets: {str(e)}")
        
        # Define time range for historical data (last 3 days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=3)
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Test historical data fetching for BTC-USDT on Binance
        if "binance" in fetcher.exchange_handlers:
            try:
                logger.info("Testing historical data fetch from Binance...")
                await fetcher.fetch_historical_data(
                    markets=["BTCUSDT"],
                    time_range=time_range,
                    resolution="1h",  # 1-hour timeframe
                    exchanges=["binance"]
                )
                logger.info("✅ Historical data fetch complete")
                
                # Try to retrieve the data
                raw_candles = await fetcher.raw_storage.get_candles(
                    exchange="binance",
                    market="BTCUSDT",
                    resolution="1h",
                    time_range=time_range
                )
                
                if raw_candles and len(raw_candles) > 0:
                    logger.info(f"✅ Retrieved {len(raw_candles)} candles from storage")
                    
                    # Test indicators with the data
                    try:
                        import pandas as pd
                        import numpy as np
                        
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
                            for candle in raw_candles
                        ])
                        
                        # Set timestamp as index
                        df.set_index('timestamp', inplace=True)
                        df.sort_index(inplace=True)
                        
                        logger.info(f"Data range: {df.index.min()} to {df.index.max()}")
                        
                        # Test indicators
                        # 1. RSI
                        rsi = RSIIndicator()
                        rsi_values = rsi.calculate_indicator(df)
                        rsi_signals = rsi.generate_signals(df)
                        logger.info(f"✅ RSI calculation successful. Last value: {rsi_values.iloc[-1] if hasattr(rsi_values, 'iloc') else rsi_values[-1]}")
                        
                        # 2. MACD
                        macd = MACDIndicator()
                        macd_values = macd.calculate_indicator(df)
                        macd_signals = macd.generate_signals(df)
                        logger.info(f"✅ MACD calculation successful")
                        
                        # 3. Bollinger Bands
                        bb = BollingerBandsIndicator()
                        bb_values = bb.calculate_indicator(df)
                        bb_signals = bb.generate_signals(df)
                        logger.info(f"✅ Bollinger Bands calculation successful")
                        
                        # 4. Supertrend
                        supertrend = SupertrendIndicator()
                        supertrend_values = supertrend.calculate_indicator(df)
                        supertrend_signals = supertrend.generate_signals(df)
                        logger.info(f"✅ Supertrend calculation successful")
                        
                        # Count signals
                        buy_signals = (supertrend_signals == 1).sum() if hasattr(supertrend_signals, 'sum') else sum(s == 1 for s in supertrend_signals)
                        sell_signals = (supertrend_signals == -1).sum() if hasattr(supertrend_signals, 'sum') else sum(s == -1 for s in supertrend_signals)
                        neutral_signals = (supertrend_signals == 0).sum() if hasattr(supertrend_signals, 'sum') else sum(s == 0 for s in supertrend_signals)
                        
                        logger.info(f"Supertrend signals: Buy: {buy_signals}, Sell: {sell_signals}, Neutral: {neutral_signals}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error testing indicators: {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.error("❌ No data retrieved from storage")
            except Exception as e:
                logger.error(f"❌ Error fetching historical data: {str(e)}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        logger.error(f"❌ Error in data fetcher: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop the data fetcher
        if 'fetcher' in locals() and fetcher:
            await fetcher.stop()
            logger.info("Data fetcher stopped")

if __name__ == "__main__":
    # Run the test function
    asyncio.run(main())