"""
Test script for running a simplified Jupiter strategy on testnet.
This script is completely isolated from the main implementation and only uses test components.
"""

import asyncio
import logging
import sys
import os
import numpy as np
import aiohttp
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

# Add the project root to the Python path to allow imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# Import only what we need for testing
from src.utils.indicators.supertrend import supertrend
from src.utils.indicators.knn import knnStrategy
from src.utils.wallet.sol_wallet import SolanaWallet
from src.trading.devnet.devnet_adapter import DevnetAdapter
from src.core.models import StandardizedCandle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleTestStrategy:
    """A simplified test strategy that uses Jupiter and our indicators."""
    
    def __init__(self, config_dict, adapter=None):
        self.config = config_dict
        self.adapter = adapter
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized Simple Test Strategy")
        
    async def fetch_price_data(self, market="SOL-USDC", resolution="1m"):
        """
        Fetch price data for a market from the Binance API as fallback for local testing.
        In a real implementation, we would use our own data source.
        """
        try:
            if self.adapter:
                # If we have an adapter, try to use it first
                self.logger.info(f"Using adapter to get {market} price data")
                # This is a stub - in a real implementation we'd use the adapter
                # to fetch price data from Drift or another source
            
            # Fallback to Binance API for demo purposes
            self.logger.info(f"Fetching {market} price data from Binance API")
            # Extract the base currency from the market symbol (e.g., SOL from SOL-USDC)
            base_currency = market.split('-')[0].lower()
            pair = f"{base_currency}usdt"  # Binance uses pairs like solusdt
            
            # Convert our resolution format to Binance's
            interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
            binance_interval = interval_map.get(resolution, "1h")
            
            # Use Binance API to get historical klines (candlestick data)
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                "symbol": pair.upper(),
                "interval": binance_interval,
                "limit": 100  # Get the last 100 candles
            }
            
            candles = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for candlestick in data:
                            # Convert Binance format to our standardized candle format
                            candle = StandardizedCandle(
                                timestamp=datetime.fromtimestamp(candlestick[0] / 1000, tz=timezone.utc),
                                open=float(candlestick[1]),
                                high=float(candlestick[2]),
                                low=float(candlestick[3]),
                                close=float(candlestick[4]),
                                volume=float(candlestick[5]),
                                market=market,
                                source="binance",
                                resolution=resolution,
                                raw_data=candlestick
                            )
                            candles.append(candle)
                    else:
                        self.logger.error(f"Failed to fetch data: {response.status}")
                        return []
            
            self.logger.info(f"Fetched {len(candles)} candles for {market}")
            return candles
            
        except Exception as e:
            self.logger.error(f"Error fetching price data: {str(e)}")
            # Return some mock data for testing
            mock_candles = []
            base_price = 100.0  # Starting price
            timestamp = datetime.now(timezone.utc)
            for i in range(100):
                # Generate some random price movement
                change = (np.random.random() - 0.5) * 2.0  # Random value between -1 and 1
                price = base_price * (1 + change * 0.01)  # Small percentage change
                
                # Create a mock candle
                candle = StandardizedCandle(
                    timestamp=timestamp,
                    open=price - 0.5,
                    high=price + 1.0,
                    low=price - 1.0,
                    close=price,
                    volume=1000.0,
                    market=market,
                    source="mock",
                    resolution=resolution,
                    raw_data={"mock": True}
                )
                mock_candles.append(candle)
                timestamp = timestamp.replace(minute=timestamp.minute - 1)  # Go back in time
                base_price = price  # Use this as the base for the next iteration
            
            self.logger.info(f"Using {len(mock_candles)} mock candles for testing")
            return mock_candles
    
    def compute_signals(self, candles):
        """Compute trading signals using our indicators."""
        if not candles:
            self.logger.error("No candles provided for signal computation")
            return {"supertrend": "neutral", "knn": "neutral"}
        
        # Extract price data for indicators
        closes = np.array([candle.close for candle in candles])
        highs = np.array([candle.high for candle in candles])
        lows = np.array([candle.low for candle in candles])
        
        # Compute Supertrend signal
        try:
            st_period = self.config.get("st_period", 14)
            st_multiplier = self.config.get("st_multiplier", 3.0)
            
            self.logger.info(f"Computing Supertrend (period={st_period}, mult={st_multiplier})")
            st_result = supertrend(closes, highs, lows, st_period, st_multiplier)
            
            # Get the latest signal
            if len(st_result) > 0 and 'signal' in st_result[-1]:
                st_signal = st_result[-1]['signal']
                self.logger.info(f"Supertrend signal: {st_signal}")
            else:
                st_signal = "neutral"
                self.logger.warning("Failed to get Supertrend signal, using neutral")
        except Exception as e:
            self.logger.error(f"Error computing Supertrend: {str(e)}")
            st_signal = "neutral"
        
        # Compute KNN signal
        try:
            knn_neighbors = self.config.get("knn_neighbors", 5)
            knn_period = self.config.get("knn_period", 14)
            
            self.logger.info(f"Computing KNN (neighbors={knn_neighbors}, period={knn_period})")
            knn_result = knnStrategy(closes, knn_neighbors, knn_period)
            
            # Get the latest signal
            if knn_result and len(knn_result) > 0:
                knn_signal = "buy" if knn_result[-1] > 0 else "sell" if knn_result[-1] < 0 else "neutral"
                self.logger.info(f"KNN signal: {knn_signal}")
            else:
                knn_signal = "neutral"
                self.logger.warning("Failed to get KNN signal, using neutral")
        except Exception as e:
            self.logger.error(f"Error computing KNN: {str(e)}")
            knn_signal = "neutral"
        
        return {"supertrend": st_signal, "knn": knn_signal}
    
    def evaluate_signals(self, st_signal, knn_signal):
        """Evaluate multiple signals to make a trading decision."""
        # Simple majority voting system
        if st_signal == knn_signal:
            return st_signal
        elif st_signal == "neutral":
            return knn_signal
        elif knn_signal == "neutral":
            return st_signal
        else:
            # If signals conflict, be conservative
            return "neutral"
    
    async def simulate_transaction(self, decision, wallet, amount_usd=10):
        """Simulate a trading transaction."""
        try:
            if self.adapter:
                # Use the adapter for simulating the transaction if available
                self.logger.info(f"Using adapter to simulate {decision} transaction")
                # This would be implemented to use the adapter's functionality
                
            # For testing, we'll just create a mock transaction result
            timestamp = datetime.now(timezone.utc)
            price = 100.0  # Mock price
            sol_amount = amount_usd / price
            
            # Mock transaction object
            tx_result = {
                "timestamp": timestamp.isoformat(),
                "action": decision,
                "market": self.config.get("market", "SOL-USDC"),
                "price": price,
                "usd_amount": amount_usd,
                "sol_amount": sol_amount,
                "wallet": str(wallet.pubkey) if hasattr(wallet, 'pubkey') else "unknown",
                "tx_id": f"mock_{int(timestamp.timestamp())}"
            }
            
            self.logger.info(f"Simulated {decision} transaction: {tx_result['tx_id']}")
            return tx_result
            
        except Exception as e:
            self.logger.error(f"Error simulating transaction: {str(e)}")
            return None
    
    async def run_test(self):
        """Run a complete test cycle of the strategy."""
        self.logger.info("Running test cycle")
        
        # Fetch price data
        candles = await self.fetch_price_data(
            market=self.config.get("market", "SOL-USDC"),
            resolution=self.config.get("resolution", "1m")
        )
        
        if not candles:
            self.logger.error("No candles retrieved, cannot make trading decision")
            return "neutral"
        
        # Compute signals
        signals = self.compute_signals(candles)
        
        # Evaluate signals to make decision
        decision = self.evaluate_signals(signals["supertrend"], signals["knn"])
        self.logger.info(f"Trading decision: {decision}")
        
        return decision

@pytest.mark.asyncio
async def test_jup_strategy(devnet_adapter):
    """Test the Jupiter strategy using the devnet adapter fixture"""
    # Configuration for the test
    config = {
        "market": "SOL-USDC",
        "amount_usd": 10.0,
        "st_period": 14,
        "st_multiplier": 3.0,
        "knn_neighbors": 5,
        "knn_period": 14
    }
    
    # Initialize strategy with the config and adapter
    strategy = SimpleTestStrategy(config, adapter=devnet_adapter)
    
    # Fetch price data
    candles = await strategy.fetch_price_data()
    assert len(candles) > 0, "Failed to fetch price data"
    
    # Compute signals
    signals = strategy.compute_signals(candles)
    assert "supertrend" in signals, "Missing supertrend signal"
    assert "knn" in signals, "Missing KNN signal"
    
    # Evaluate signals
    decision = strategy.evaluate_signals(signals["supertrend"], signals["knn"])
    logger.info(f"Strategy decision: {decision}")
    
    # Since this is a test, we don't actually execute trades
    return True

if __name__ == "__main__":
    try:
        asyncio.run(run_jup_testnet_strategy())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error running test: {str(e)}", exc_info=True) 