"""
Exchange handlers package.
Provides a unified interface to different cryptocurrency exchanges.
"""

from types import SimpleNamespace
from typing import Union, Dict, Type
from exchanges.base import BaseExchangeHandler
from exchanges.drift import DriftHandler
from exchanges.binance import BinanceHandler
from exchanges.coinbase import CoinbaseHandler
from exchanges.jup import JupiterHandler  # Newly added Jupiter handler
from core.exceptions import ExchangeError

# Registry of available exchange handlers
EXCHANGE_HANDLERS: Dict[str, Type[BaseExchangeHandler]] = {
    'drift': DriftHandler,
    'binance': BinanceHandler,
    'coinbase': CoinbaseHandler,
    'jupiter': JupiterHandler
}

def get_exchange_handler(config: Union[dict, 'ExchangeConfig']) -> BaseExchangeHandler:
    """
    Factory function to get the appropriate exchange handler.
    Automatically converts dictionary-based configs to objects.
    
    Args:
        config: Exchange configuration as a dict or object.
        
    Returns:
        Initialized exchange handler.
        
    Raises:
        ExchangeError: If exchange is not supported.
    """
    # If config is a dictionary, convert it to an object with attribute access.
    if isinstance(config, dict):
        if "name" not in config:
            raise ExchangeError("Exchange configuration must include a 'name' field.")
        config = SimpleNamespace(**config)
    
    handler_class = EXCHANGE_HANDLERS.get(config.name.lower())
    if not handler_class:
        raise ExchangeError(f"Unsupported exchange: {config.name}")
        
    return handler_class(config)

def get_supported_exchanges() -> list:
    return list(EXCHANGE_HANDLERS.keys())

