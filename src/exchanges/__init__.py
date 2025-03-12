"""
Exchange handlers package.
"""
from typing import Optional, Type

from .base import BaseExchangeHandler
from .binance import BinanceHandler
from .coinbase import CoinbaseHandler
from .drift import DriftHandler
from .jup import JupiterHandler
from .bitget import BitgetHandler

__all__ = [
    'BaseExchangeHandler',
    'BinanceHandler',
    'CoinbaseHandler',
    'DriftHandler',
    'JupiterHandler',
    'BitgetHandler',
    'get_exchange_handler'
]

def get_exchange_handler(exchange_config) -> Optional[BaseExchangeHandler]:
    """
    Get the appropriate exchange handler instance based on the exchange config.
    
    Args:
        exchange_config (ExchangeConfig): Configuration for the exchange
        
    Returns:
        Optional[BaseExchangeHandler]: Exchange handler instance if found, None otherwise
    """
    exchange_map = {
        'binance': BinanceHandler,
        'coinbase': CoinbaseHandler,
        'drift': DriftHandler,
        'jupiter': JupiterHandler,
        'bitget': BitgetHandler
    }
    
    handler_class = exchange_map.get(exchange_config.name.lower())
    if handler_class:
        return handler_class(exchange_config)
    return None