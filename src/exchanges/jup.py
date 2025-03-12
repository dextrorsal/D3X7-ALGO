"""
JupiterHandler for interacting with Jupiter's new API endpoints.
Uses the price endpoint to fetch live price data and simulate a candle.
"""

import logging
from datetime import datetime, timezone
from typing import List
import asyncio
import pandas as pd
from io import StringIO

from src.core.models import StandardizedCandle, TimeRange
from src.core.exceptions import ExchangeError, ValidationError
from src.exchanges.base import BaseExchangeHandler

logger = logging.getLogger(__name__)

class JupiterHandler(BaseExchangeHandler):
    """Handler for Jupiter DEX using the new API endpoints."""

    def __init__(self, config):
        """
        Initialize the Jupiter handler with the given configuration.
        """
        super().__init__(config)
        # Here, self.config.base_url should be set from the config.
        # For Jupiter, the new base for swap endpoints might be used for swaps,
        # while the price endpoint is separate.
        self.price_url = "https://api.jup.ag/price/v2"  # New price endpoint
        logger.info(f"JupiterHandler initialized with base URL: {self.base_url} and price URL: {self.price_url}")

    async def fetch_historical_candles(
        self,
        market: str,
        time_range: TimeRange,
        resolution: str
    ) -> List[StandardizedCandle]:
        """
        Jupiter does not provide historical candle data via this API.
        """
        logger.warning("Historical candle fetching is not supported for Jupiter.")
        raise NotImplementedError("Historical candle fetching is not implemented for Jupiter.")

    async def fetch_live_candles(
        self,
        market: str,
        resolution: str
    ) -> StandardizedCandle:
        """
        Fetch the latest price for a given market from Jupiter's price endpoint,
        and simulate a candlestick with open=high=low=close equal to the current price.
        
        For demonstration, this implementation supports "SOL-USDC" only.
        """
        # For "SOL-USDC", use the well-known mint addresses:
        if market.upper() == "SOL-USDC":
            input_mint = "So11111111111111111111111111111111111111112"  # SOL
            output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        else:
            raise ValidationError(f"Market {market} not supported by JupiterHandler.")

        # Prepare query parameters as per Jupiter's new API:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            # Use a small amount (in base units) for price quotation.
            "amount": 1000000,  # e.g. 1,000,000 base units
            "slippageBps": 50  # 0.5% slippage tolerance
        }

        try:
            # Use the _make_request method inherited from BaseExchangeHandler.
            # Note: Since _make_request in BaseExchangeHandler concatenates self.base_url with the endpoint,
            # we pass the full price URL as the endpoint and leave self.base_url empty,
            # or modify _make_request if necessary.
            # For this example, we'll assume _make_request works with a full URL.
            response = await self._make_request(method="GET", endpoint=self.price_url, params=params)
            # Depending on the API response, you might need to adjust how you extract the price.
            # For demonstration, assume the response is either a dict with a "price" key
            # or a list of quotes, and we choose the first one.
            if isinstance(response, list):
                quote = response[0]
            else:
                quote = response

            price = float(quote.get("price"))
        except Exception as e:
            logger.error(f"Error fetching live price from Jupiter: {e}")
            raise ExchangeError(f"Failed to fetch live price from Jupiter: {e}")

        # Construct a standardized candle using the current price.
        candle = StandardizedCandle(
            timestamp=datetime.now(timezone.utc),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=0.0,  # Volume not provided by the price API
            source="jupiter",
            resolution=resolution,
            market=market,
            raw_data=response
        )
        return candle
