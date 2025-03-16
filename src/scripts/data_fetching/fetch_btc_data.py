import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the necessary modules
from src.core.models import TimeRange
from src.core.config import Config, StorageConfig
from src.ultimate_fetcher import UltimateDataFetcher

async def fetch_btc_data():
    """Fetch 365 days of BTC-USDT data from Binance with 1-day resolution."""
    
    # Create storage config
    storage_config = StorageConfig(
        data_path=Path("data"),
        historical_raw_path=Path("data/historical/raw"),
        historical_processed_path=Path("data/historical/processed"),
        live_raw_path=Path("data/live/raw"),
        live_processed_path=Path("data/live/processed"),
        use_compression=False
    )
    
    # Create main config
    config = Config(storage=storage_config)
    
    # Initialize the data fetcher
    fetcher = UltimateDataFetcher(config)
    await fetcher.start()
    
    try:
        # Calculate date range (365 days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=365)
        time_range = TimeRange(start=start_time, end=end_time)
        
        logger.info(f"Fetching BTC-USDT data from {start_time} to {end_time}")
        
        # Fetch the data
        await fetcher.fetch_historical_data(
            markets=["BTC-USDT"],
            time_range=time_range,
            resolution="1D",
            exchanges=["binance"]
        )
        
        logger.info("Data fetching completed successfully!")
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    finally:
        # Stop the fetcher
        await fetcher.stop()

if __name__ == "__main__":
    asyncio.run(fetch_btc_data()) 