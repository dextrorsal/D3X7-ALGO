import asyncio
import logging
from datetime import datetime, timezone
import aiohttp

# Import JupiterHandler from our exchanges module
from src.exchanges.jup import JupiterHandler
# Import StandardizedCandle model used for candle data
from src.core.models import StandardizedCandle


class JupLiveStrat:
    """A simple live trading strategy using Jupiter Ultra API with Super Trend and KNN indicators."""

    def __init__(self, config, mode="testnet"):
        """Initialize the strategy.

        Args:
            config (dict): Configuration settings (e.g., API keys, base URLs).
            mode (str): Either 'testnet' or 'mainnet'.
        """
        self.config = config
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        
        # Initialize JupiterHandler with the provided configuration
        self.handler = JupiterHandler(config)
        
        # Token addresses (same as in jup_adapter.py)
        self.tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        }
        
        # Price API endpoint
        self.price_url = "https://price.jup.ag/v4/price"
        
        self.logger.info(f"Initialized Jupiter Live Strategy in {mode} mode.")
        
    async def get_current_price(self, market="SOL-USDC"):
        """Get current price using Jupiter's Price API v4.
        
        Args:
            market (str): Market symbol (e.g., "SOL-USDC")
            
        Returns:
            float: Current price
        """
        try:
            base, quote = market.split("-")
            
            if base not in self.tokens or quote not in self.tokens:
                raise ValueError(f"Unsupported market: {market}")
                
            params = {
                "ids": self.tokens[base],
                "vsToken": self.tokens[quote]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.price_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"Price API error: {await response.text()}")
                        
                    data = await response.json()
                    
                    if "data" not in data or self.tokens[base] not in data["data"]:
                        raise Exception("Invalid price response format")
                        
                    price_data = data["data"][self.tokens[base]]
                    return float(price_data["price"])
                    
        except Exception as e:
            self.logger.error(f"Error getting price for {market}: {e}")
            raise
            
    async def generate_signal(self, market="SOL-USDC"):
        """Generate trading signal based on current price and indicators.
        
        Args:
            market (str): Market symbol (e.g., "SOL-USDC")
            
        Returns:
            dict: Signal information including price and recommendation
        """
        try:
            # Get current price
            price = await self.get_current_price(market)
            
            # In a real strategy, we would:
            # 1. Get historical prices
            # 2. Calculate indicators
            # 3. Generate signals based on indicator values
            
            # For demonstration, return a simple signal
            return {
                "market": market,
                "price": price,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signal": "HOLD",  # Could be BUY, SELL, or HOLD
                "confidence": 0.0,  # 0.0 to 1.0
                "indicators": {
                    "price": price,
                    # Add other indicator values here
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {market}: {e}")
            raise

    def compute_super_trend(self, candles, atr_length=10, factor=3):
        """Compute Super Trend signal using the external indicator.
        
        This function extracts high, low, and close prices from candles and calls the external supertrend function.
        
        Args:
            candles (list): A list of StandardizedCandle objects.
            atr_length (int): ATR period for calculating the Super Trend.
            factor (int): Multiplier factor for the ATR.
            
        Returns:
            str: "buy", "sell", or "hold" based on the Super Trend indicator.
        """
        from src.utils.indicators.supertrend import supertrend
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        closes = [candle.close for candle in candles]
        st_values, directions = supertrend(highs, lows, closes, atr_length=atr_length, factor=factor)
        signal = directions[-1]
        if signal == 1:
            return "buy"
        elif signal == -1:
            return "sell"
        else:
            return "hold"

    def compute_knn_signal(self, candles):
        """Compute KNN signal using the external knnStrategy.
        
        Args:
            candles (list): A list of StandardizedCandle objects.
            
        Returns:
            str: "buy", "sell", or "hold" based on the KNN indicator.
        """
        from src.utils.indicators.knn import knnStrategy
        prices = [candle.close for candle in candles]
        volumes = [candle.volume for candle in candles]
        knn_strat = knnStrategy()
        result = knn_strat.calculate(prices, volumes)
        if result is None:
            return "hold"
        if result == 1:
            return "buy"
        elif result == -1:
            return "sell"
        else:
            return "hold"

    def evaluate_signal(self, candles):
        """Combine the signals from Super Trend and KNN and decide on a trading decision.
        
        If both indicators agree on 'buy' or 'sell', that signal is returned; otherwise, the decision is 'hold'.
        
        Args:
            candles (list): A list of StandardizedCandle objects.
        
        Returns:
            str: Trading decision ('buy', 'sell', or 'hold').
        """
        super_trend_signal = self.compute_super_trend(candles)
        knn_signal = self.compute_knn_signal(candles)
        self.logger.info(f"Super Trend signal: {super_trend_signal}, KNN signal: {knn_signal}")
        if super_trend_signal == knn_signal and super_trend_signal is not None:
            return super_trend_signal
        else:
            return "hold"

    async def run_strategy(self):
        """Run the live strategy: fetch current candle, simulate historical data, and evaluate the trading signal."""
        self.logger.info("Running Jupiter Live Strategy asynchronously.")
        try:
            # For our example, we use the supported market 'SOL-USDC'.
            current_candle = await self.handler.fetch_live_candles(market="SOL-USDC", resolution="1m")
        except Exception as e:
            self.logger.error(f"Error fetching live candle: {e}")
            return

        # Simulate historical candles by duplicating the current candle.
        candles = [current_candle for _ in range(10)]
        decision = self.evaluate_signal(candles)
        self.logger.info(f"Trading decision: {decision}")
        print(f"Trading decision: {decision}")


if __name__ == "__main__":
    # Setup a simple test configuration for testnet mode.
    # In a real scenario, this could include API keys and other settings.
    config = {
        "base_url": "",  # base_url is not used for the price endpoint right now
        # Add additional configuration items as necessary
    }
    strat = JupLiveStrat(config, mode="testnet")
    asyncio.run(strat.run_strategy()) 