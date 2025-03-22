"""Integration tests for the Drift protocol functionality."""
import pytest
import logging
from dotenv import load_dotenv
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_account_creation(drift_adapter):
    """Test successful initialization."""
    assert drift_adapter.client is not None
    logger.info("DriftAdapter initialized successfully")

@pytest.mark.asyncio
async def test_market_data(drift_tools):
    """Test market data retrieval."""
    try:
        markets = await drift_tools.get_markets()
        assert markets is not None
        assert len(markets) > 0
        logger.info(f"Retrieved {len(markets)} markets")
    except Exception as e:
        logger.error(f"Error in test_market_data: {e}")
        pytest.fail(f"Failed to retrieve market data: {e}")

@pytest.mark.asyncio
async def test_orderbook_data(drift_tools):
    """Test order book data retrieval."""
    try:
        markets = await drift_tools.get_markets()
        assert markets is not None
        assert len(markets) > 0
        
        # Get first market for testing
        market = markets[0]
        logger.info(f"Testing order book for market: {market}")
        
        prices = await drift_tools.get_prices([market])
        assert prices is not None
        assert len(prices) > 0
        logger.info(f"Retrieved prices for market: {prices}")
    except Exception as e:
        logger.error(f"Error in test_orderbook_data: {e}")
        pytest.fail(f"Failed to retrieve orderbook data: {e}")

@pytest.mark.asyncio
async def test_market_prices(drift_tools):
    """Test retrieval of market prices."""
    try:
        markets = await drift_tools.get_markets()
        prices = await drift_tools.get_prices(markets)
        assert prices is not None
        assert len(prices) > 0
        logger.info(f"Retrieved prices for {len(prices)} markets")
    except Exception as e:
        logger.error(f"Error in test_market_prices: {e}")
        pytest.fail(f"Failed to retrieve market prices: {e}")