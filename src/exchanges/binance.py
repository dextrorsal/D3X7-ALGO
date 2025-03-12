"""
Binance exchange handler implementation using the official binance-connector SDK.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from binance.spot import Spot
from binance.error import ClientError

from exchanges.base import BaseExchangeHandler
from core.models import StandardizedCandle, TimeRange
from core.exceptions import ExchangeError, ValidationError

logger = logging.getLogger(__name__)

class BinanceHandler(BaseExchangeHandler):
    """Handler for Binance exchange data using official SDK."""

    def __init__(self, config):
        """Initialize Binance handler with configuration."""
        super().__init__(config)
        self.client = None
        self.timeframe_map = {
            "1": "1m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1h",
            "240": "4h",
            "1D": "1d"
        }

    async def start(self):
        """Start the Binance handler and initialize the client."""
        if not self.client:
            self.client = Spot(
                api_key=self.credentials.api_key if self.credentials else None,
                api_secret=self.credentials.api_secret if self.credentials else None,
                base_url=self.base_url
            )
        logger.info("Started Binance exchange handler")

    async def stop(self):
        """Stop the Binance handler and close connections."""
        self.client = None
        logger.info("Stopped Binance exchange handler")

    def _convert_market_symbol(self, market: str) -> str:
        """Convert internal market symbol to Binance format."""
        return market.replace('-PERP', 'USDT').replace('-', '')

    def _parse_raw_candle(self, raw_data: List, market: str, resolution: str) -> StandardizedCandle:
        """Parse raw candle data into StandardizedCandle format."""
        try:
            # Binance kline format:
            # [
            #   0  Open time
            #   1  Open
            #   2  High
            #   3  Low
            #   4  Close
            #   5  Volume
            #   6  Close time
            #   7  Quote asset volume
            #   8  Number of trades
            #   9  Taker buy base asset volume
            #   10 Taker buy quote asset volume
            #   11 Ignore
            # ]
            candle = StandardizedCandle(
                timestamp=self.standardize_timestamp(raw_data[0]),
                open=float(raw_data[1]),
                high=float(raw_data[2]),
                low=float(raw_data[3]),
                close=float(raw_data[4]),
                volume=float(raw_data[5]),
                source='binance',
                resolution=resolution,
                market=market,
                raw_data=raw_data
            )
            self.validate_candle(candle)
            return candle
        except (IndexError, ValueError) as e:
            raise ValidationError(f"Error parsing Binance candle data: {str(e)}")

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """Fetch historical candle data from Binance."""
        self.validate_market(market)
        binance_symbol = self._convert_market_symbol(market)
        interval = self.timeframe_map.get(resolution)
        if not interval:
            raise ValidationError(f"Invalid resolution: {resolution}")

        try:
            # Convert timestamps to milliseconds for Binance API
            start_ts = int(time_range.start.timestamp() * 1000)
            end_ts = int(time_range.end.timestamp() * 1000)

            klines = self.client.klines(
                symbol=binance_symbol,
                interval=interval,
                startTime=start_ts,
                endTime=end_ts,
                limit=1000
            )

            return [self._parse_raw_candle(kline, market, resolution) for kline in klines]

        except ClientError as e:
            raise ExchangeError(f"Binance API error: {str(e)}")
        except Exception as e:
            raise ExchangeError(f"Failed to fetch historical data: {str(e)}")

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str
    ) -> StandardizedCandle:
        """Fetch live candle data from Binance."""
        self.validate_market(market)
        binance_symbol = self._convert_market_symbol(market)
        interval = self.timeframe_map.get(resolution)
        if not interval:
            raise ValidationError(f"Invalid resolution: {resolution}")

        try:
            klines = self.client.klines(
                symbol=binance_symbol,
                interval=interval,
                limit=1
            )

            if not klines:
                raise ExchangeError(f"No live data available for {market}")

            return self._parse_raw_candle(klines[0], market, resolution)

        except ClientError as e:
            raise ExchangeError(f"Binance API error: {str(e)}")
        except Exception as e:
            raise ExchangeError(f"Failed to fetch live data: {str(e)}")

    async def get_markets(self) -> List[str]:
        """Get available markets from Binance."""
        try:
            exchange_info = self.client.exchange_info()
            markets = []
            for symbol in exchange_info['symbols']:
                if symbol['status'] == 'TRADING':
                    markets.append(f"{symbol['baseAsset']}-{symbol['quoteAsset']}")
            return markets

        except ClientError as e:
            raise ExchangeError(f"Binance API error: {str(e)}")
        except Exception as e:
            raise ExchangeError(f"Failed to fetch markets: {str(e)}")

    async def get_exchange_info(self) -> Dict:
        """Get exchange information."""
        try:
            return self.client.exchange_info()
        except ClientError as e:
            raise ExchangeError(f"Failed to get exchange info: {str(e)}")