"""Test the Drift exchange handler."""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta

from rich.logging import RichHandler
from rich.console import Console

from src.exchanges.drift import DriftHandler
from src.core.config import ExchangeConfig
from src.core.exceptions import ExchangeError
from src.core.time_range import TimeRange

# Set up logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")
console = Console()

# Set environment variables
os.environ['MAIN_KEY_PATH'] = '/home/dex/.config/solana/keys/id.json'
os.environ['MAINNET_RPC_ENDPOINT'] = 'https://mainnet.helius-rpc.com/?api-key=fc50351b-ef76-49bd-b978-d9b9ba37ebd5'
os.environ['DEVNET_RPC_ENDPOINT'] = 'https://api.devnet.solana.com'

# Convert keypair file to private key string
try:
    with open(os.environ['MAIN_KEY_PATH'], 'r') as f:
        keypair_data = json.load(f)
        private_key = bytes(keypair_data).hex()
        os.environ['PRIVATE_KEY'] = private_key
        logger.info(f"Loaded private key from {os.environ['MAIN_KEY_PATH']}")
except Exception as e:
    logger.error(f"Failed to load keypair: {e}")
    raise

# Test configuration
TEST_CONFIG = {
    'name': 'drift',
    'base_url': 'https://drift-historical-data-devnet.s3.eu-west-1.amazonaws.com',
    'credentials': {},  # Empty credentials since we're using environment variables
    'rate_limit': 10,
    'markets': ['SOL-PERP', 'BTC-PERP'],
    'network': 'devnet'  # Force devnet
}

async def test_drift_handler():
    """Test the Drift exchange handler functionality."""
    try:
        # Create handler with test configuration
        config = ExchangeConfig(**TEST_CONFIG)
        handler = DriftHandler(config)
        
        # Start handler
        logger.info("Starting Drift exchange handler...")
        await handler.start()
        
        # Test market fetching
        logger.info("Testing market fetching...")
        markets = await handler.get_markets()
        logger.info(f"Available markets: {markets}")
        
        # Test historical data fetching
        logger.info("Testing historical data fetching...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        for market in TEST_CONFIG['markets']:
            candles = await handler.fetch_historical_candles(
                market=market,
                time_range=TimeRange(start=start_time, end=end_time),
                resolution='1h'
            )
            logger.info(f"Fetched {len(candles)} candles for {market}")
            if candles:
                logger.info(f"Sample candle for {market}: {candles[0]}")
        
        # Stop handler
        logger.info("Stopping Drift exchange handler...")
        await handler.stop()
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(test_drift_handler())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise 