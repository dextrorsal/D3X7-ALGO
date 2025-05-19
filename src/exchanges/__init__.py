"""
Exchange handlers package.
"""

from typing import Optional, Type
import logging
import importlib.util
import sys

from .base import BaseExchangeHandler
from .binance.binance import BinanceHandler
from .coinbase.coinbase import CoinbaseHandler
from .bitget import BitgetHandler

# Initialize logger
logger = logging.getLogger(__name__)

__all__ = [
    "BaseExchangeHandler",
    "BinanceHandler",
    "CoinbaseHandler",
    "get_exchange_handler",
]

# Conditionally import handlers that have special dependencies
try:
    from .drift import DriftHandler

    __all__.append("DriftHandler")
except ImportError as e:
    logger.warning(f"Could not import DriftHandler: {e}")
    DriftHandler = None

try:
    from .jupiter.jup import JupiterHandler

    __all__.append("JupiterHandler")
except ImportError as e:
    logger.warning(f"Could not import JupiterHandler: {e}")
    JupiterHandler = None

try:
    from .bitget import BitgetHandler

    __all__.append("BitgetHandler")
except ImportError as e:
    logger.warning(f"Could not import BitgetHandler: {e}")
    BitgetHandler = None


def get_exchange_handler(exchange_config) -> Optional[BaseExchangeHandler]:
    """
    Get the appropriate exchange handler instance based on the exchange config.

    Args:
        exchange_config (ExchangeConfig): Configuration for the exchange

    Returns:
        Optional[BaseExchangeHandler]: Exchange handler instance if found, None otherwise
    """
    exchange_map = {
        "binance": BinanceHandler,
        "coinbase": CoinbaseHandler,
        "drift": DriftHandler,
        "jupiter": JupiterHandler,
        "bitget": BitgetHandler,
    }

    handler_class = exchange_map.get(exchange_config.name.lower())
    if handler_class is None:
        logger.error(f"No handler found for exchange {exchange_config.name}")
        return None

    try:
        return handler_class(exchange_config)
    except Exception as e:
        logger.error(f"Error initializing handler for {exchange_config.name}: {e}")
        return None


"""Exchange implementations."""
