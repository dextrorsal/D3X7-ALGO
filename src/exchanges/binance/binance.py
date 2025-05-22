"""
Simplified Binance exchange handler for fetching historical and live candle data.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from binance.spot import Spot
from binance.error import ClientError

from src.core.models import StandardizedCandle, TimeRange
from src.core.exceptions import ExchangeError, ValidationError
from src.exchanges.base import BaseExchangeHandler, ExchangeConfig

logger = logging.getLogger(__name__)


class BinanceHandler(BaseExchangeHandler):
    """Simplified handler for Binance exchange data."""

    def __init__(self, config: ExchangeConfig):
        """Initialize Binance handler with configuration."""
        super().__init__(config)
        self.client = None
        self.base_url = config.base_url or "https://api.binance.com"

        # Initialize timeframe mapping
        self.timeframe_map = {
            "1": "1m",
            "3": "3m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "120": "2h",
            "240": "4h",
            "360": "6h",
            "480": "8h",
            "720": "12h",
            "1D": "1d",
            "3D": "3d",
            "1W": "1w",
            "1M": "1M",
        }

    async def start(self):
        """Start the Binance handler and initialize the client."""
        try:
            # Initialize the client - no API keys needed for public data
            self.client = Spot(base_url=self.base_url)
            logger.info("Started Binance exchange handler")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise ExchangeError(f"Failed to initialize Binance client: {e}")

    async def stop(self):
        """Stop the handler."""
        self.client = None
        await super().stop()
        logger.info("Stopped Binance exchange handler")

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange = None,
        resolution: str = "1",
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> List[StandardizedCandle]:
        """
        Fetch historical candles for a market.

        Args:
            market: Market symbol (e.g., 'BTCUSDT')
            time_range: Time range to fetch data for
            resolution: Candle resolution (default: "1")
            start_time: Start time (if time_range not provided)
            end_time: End time (if time_range not provided)

        Returns:
            List[StandardizedCandle]: List of standardized candles
        """
        try:
            # Handle time range
            if time_range:
                start_time = time_range.start
                end_time = time_range.end
            elif not (start_time and end_time):
                raise ValidationError(
                    "Must provide either time_range or both start_time and end_time"
                )

            # Convert resolution to Binance format
            interval = self.timeframe_map.get(resolution, "1m")

            # Convert times to milliseconds
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)

            try:
                # Fetch candles using the SDK
                klines = self.client.klines(
                    symbol=market,
                    interval=interval,
                    startTime=start_ts,
                    endTime=end_ts,
                    limit=1000,  # Maximum allowed by Binance
                )

                # Convert to StandardizedCandle format
                candles = []
                for kline in klines:
                    candle = self._convert_to_standardized_candle(
                        kline, market, resolution
                    )
                    candles.append(candle)

                return candles

            except ClientError as e:
                logger.error(f"Binance API error: {e}")
                raise ExchangeError(f"Failed to fetch historical candles: {e}")

        except Exception as e:
            logger.error(f"Error fetching historical candles for {market}: {e}")
            raise ExchangeError(f"Failed to fetch historical candles: {e}")

    async def fetch_live_candles(
        self, market: str, resolution: str = "1"
    ) -> StandardizedCandle:
        """
        Fetch latest candle for a market.

        Args:
            market: Market symbol (e.g., 'BTCUSDT')
            resolution: Candle resolution (default: "1")

        Returns:
            StandardizedCandle: Latest candle data
        """
        try:
            # Convert resolution to Binance format
            interval = self.timeframe_map.get(resolution, "1m")

            try:
                # Fetch the most recent candle
                klines = self.client.klines(
                    symbol=market,
                    interval=interval,
                    limit=1,  # We only need the latest candle
                )

                if not klines:
                    raise ExchangeError(f"No data returned for {market}")

                # Convert to StandardizedCandle format
                return self._convert_to_standardized_candle(
                    klines[0], market, resolution
                )

            except ClientError as e:
                logger.error(f"Binance API error: {e}")
                raise ExchangeError(f"Failed to fetch live candle: {e}")

        except Exception as e:
            logger.error(f"Error fetching live candle for {market}: {e}")
            raise ExchangeError(f"Failed to fetch live candle: {e}")

    def _convert_to_standardized_candle(
        self, candle_data: List[Any], market: str, resolution: str
    ) -> StandardizedCandle:
        """
        Convert Binance candle data to StandardizedCandle format.

        Binance kline format:
        [
            0: Open time
            1: Open
            2: High
            3: Low
            4: Close
            5: Volume
            6: Close time
            7: Quote asset volume
            8: Number of trades
            9: Taker buy base asset volume
            10: Taker buy quote asset volume
            11: Ignore
        ]
        """
        return StandardizedCandle(
            timestamp=datetime.fromtimestamp(candle_data[0] / 1000, tz=timezone.utc),
            open=float(candle_data[1]),
            high=float(candle_data[2]),
            low=float(candle_data[3]),
            close=float(candle_data[4]),
            volume=float(candle_data[5]),
            market=market,
            resolution=resolution,
            source="binance",
            trade_count=int(candle_data[8]),
            additional_info={
                "quote_volume": float(candle_data[7]),
                "taker_buy_base_volume": float(candle_data[9]),
                "taker_buy_quote_volume": float(candle_data[10]),
            },
        )

    def validate_market(self, market: str) -> bool:
        """Simple market validation."""
        # For public data fetching, we'll let Binance validate the market
        # This will return True and let the API call handle any invalid markets
        return True

    def _convert_resolution(self, resolution: str) -> str:
        """Convert standard resolution to Binance format."""
        # Common formats that might be already compatible
        if resolution in [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]:
            return resolution

        # Convert from our standard format
        mapping = {
            "1": "1m",
            "3": "3m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "120": "2h",
            "240": "4h",
            "360": "6h",
            "480": "8h",
            "720": "12h",
            "1D": "1d",
            "3D": "3d",
            "1W": "1w",
            "1M": "1M",
        }

        if resolution in mapping:
            return mapping[resolution]

        # Default to 1h if not recognized
        logger.warning(f"Resolution {resolution} not recognized, defaulting to 1h")
        return "1h"

    def _get_interval_seconds(self, interval: str) -> int:
        """Get the number of seconds for a given interval."""
        # Extract the number and unit
        number = int("".join(filter(str.isdigit, interval)))
        unit = "".join(filter(str.isalpha, interval))

        # Convert to seconds
        if unit == "m":
            return number * 60
        elif unit == "h":
            return number * 60 * 60
        elif unit == "d":
            return number * 24 * 60 * 60
        elif unit == "w":
            return number * 7 * 24 * 60 * 60
        elif unit == "M":
            return number * 30 * 24 * 60 * 60  # Approximate
        else:
            return 3600  # Default to 1h

    def validate_standard_symbol(self, market: str) -> bool:
        """Validate a standard market symbol format."""
        # Regular symbols like BTC-USDT need to be converted to BTCUSDT
        converted_market = market.replace("-", "")

        # Check if it's in the available markets
        return converted_market in self._available_markets

    async def convert_standard_symbol(self, market: str) -> str:
        """Convert a standard market symbol format to exchange-specific format."""
        # Regular symbols like BTC-USDT need to be converted to BTCUSDT
        return market.replace("-", "")

    def validate_exchange_symbol(self, market: str) -> bool:
        """Validate an exchange-specific market symbol format."""
        # Check if it's in the available markets
        return market in self._available_markets

    async def convert_exchange_symbol(self, market: str) -> str:
        """Convert an exchange-specific market symbol format to standard format."""
        # Convert from BTCUSDT to BTC-USDT
        # This is a basic implementation - you may need more sophisticated logic
        stablecoins = ["USDT", "BUSD", "USDC", "DAI", "TUSD", "USDP", "FDUSD"]
        for stable in stablecoins:
            if market.endswith(stable):
                base = market[: -len(stable)]
                return f"{base}-{stable}"

        # Handle USD pairs
        if market.endswith("USD"):
            base = market[:-3]
            return f"{base}-USD"

        # Handle BTC pairs
        if market.endswith("BTC"):
            base = market[:-3]
            return f"{base}-BTC"

        # Handle ETH pairs
        if market.endswith("ETH"):
            base = market[:-3]
            return f"{base}-ETH"

        # If no specific handling, return as is with dash
        # This might not be correct for all cases
        return market

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance."""
        if not self._api_key or not self._api_secret:
            raise ExchangeError("API credentials required for account operations")

        try:
            response = await self._api_request(
                "GET", "/api/v3/account", signed=True, weight=10
            )

            balances = {}
            for balance in response.get("balances", []):
                asset = balance.get("asset")
                free = float(balance.get("free", 0))
                locked = float(balance.get("locked", 0))
                total = free + locked

                if total > 0:
                    balances[asset] = {"free": free, "locked": locked, "total": total}

            return balances

        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            raise

    async def get_ticker(self, market: str) -> Dict[str, Any]:
        """Get ticker information for a market."""
        try:
            response = await self._api_request(
                "GET", "/api/v3/ticker/24hr", params={"symbol": market}, weight=1
            )
            return {
                "symbol": response.get("symbol"),
                "last_price": float(response.get("lastPrice", 0)),
                "price_change": float(response.get("priceChange", 0)),
                "price_change_percent": float(response.get("priceChangePercent", 0)),
                "high": float(response.get("highPrice", 0)),
                "low": float(response.get("lowPrice", 0)),
                "volume": float(response.get("volume", 0)),
                "quote_volume": float(response.get("quoteVolume", 0)),
                "open_time": datetime.fromtimestamp(
                    response.get("openTime", 0) / 1000, tz=timezone.utc
                ),
                "close_time": datetime.fromtimestamp(
                    response.get("closeTime", 0) / 1000, tz=timezone.utc
                ),
                "trade_count": int(response.get("count", 0)),
            }

        except Exception as e:
            logger.error(f"Error getting ticker for {market}: {e}")
            raise

    @staticmethod
    async def self_test():
        """Run a self-test to verify the handler is working correctly."""
        try:
            # Create handler with default config
            config = ExchangeConfig(name="binance")
            handler = BinanceHandler(config)

            # Start the handler
            await handler.start()

            try:
                # Test getting markets
                markets = await handler.get_markets()
                print(f"Fetched {len(markets)} markets")
                if not markets:
                    print("Error: No markets found")
                    return False

                # Test fetching candles for BTC/USDT
                if "BTCUSDT" in markets:
                    test_market = "BTCUSDT"
                else:
                    test_market = markets[0]

                print(f"Testing with market: {test_market}")

                # Test fetching historical candles
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=1)

                candles = await handler.fetch_historical_candles(
                    test_market,
                    TimeRange(start=start_time, end=end_time),
                    resolution="1h",
                )

                print(f"Fetched {len(candles)} historical candles")
                if not candles:
                    print("Error: No candles found")
                    return False

                # Test fetching live candle
                live_candle = await handler.fetch_live_candles(test_market, "1h")
                print(f"Fetched live candle: {live_candle}")

                print("All tests passed!")
                return True

            finally:
                # Stop the handler
                await handler.stop()

        except Exception as e:
            print(f"Error during self-test: {e}")
            return False

    async def _make_request_with_retry(self, method, *args, max_retries=3, **kwargs):
        """
        Make an API request with retry logic.

        Args:
            method: The API method to call
            *args: Positional arguments for the method
            max_retries: Maximum number of retry attempts
            **kwargs: Keyword arguments for the method

        Returns:
            The API response

        Raises:
            ExchangeError: If all retries fail
        """
        last_error = None
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Check rate limits before making the request
                await self._check_rate_limits()

                # Make the request
                response = await method(*args, **kwargs)
                return response

            except ClientError as e:
                error_code = e.error_code if hasattr(e, "error_code") else None

                # Check if error is retryable
                if error_code in RETRY_ERROR_CODES:
                    retry_count += 1
                    if retry_count < max_retries:
                        # Exponential backoff: 1s, 2s, 4s, ...
                        wait_time = 2 ** (retry_count - 1)
                        logger.warning(
                            f"Retrying request after {wait_time}s (attempt {retry_count}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                # If not retryable or max retries reached, raise the error
                last_error = e
                break

            except Exception as e:
                # For other exceptions, only retry on connection errors
                if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** (retry_count - 1)
                        logger.warning(
                            f"Retrying request after {wait_time}s (attempt {retry_count}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                last_error = e
                break

        # If we get here, all retries failed
        error_msg = str(last_error) if last_error else "Unknown error"
        raise ExchangeError(f"Request failed after {max_retries} retries: {error_msg}")

    def _setup_test_mode(self, *args, **kwargs):
        """Stub for test compatibility. Does nothing."""
        pass


async def main():
    """Example usage of BinanceHandler."""
    await BinanceHandler.self_test()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run the example
    asyncio.run(main())
