"""
Bitget exchange client wrapper with common trading operations.
"""

import json
import logging
from typing import Dict, List, Optional, Union
from decimal import Decimal

from bitget import Bitget
from bitget.exceptions import BitgetAPIException

from .config import (
    USDT_FUTURES, COIN_FUTURES, SPOT,
    LONG, SHORT, BUY, SELL,
    LIMIT, MARKET,
    ISOLATED, CROSS
)

logger = logging.getLogger(__name__)

class BitgetClient:
    """
    A wrapper around the Bitget API client with common trading operations
    and error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        testnet: bool = False
    ):
        """Initialize the Bitget client."""
        self.client = Bitget(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            use_server_time=True,
            testnet=testnet
        )
    
    def get_balance(self, coin: str = 'USDT') -> Decimal:
        """Get available balance for a specific coin."""
        try:
            balances = self.client.get_account_assets()
            for balance in balances:
                if balance['coin'] == coin:
                    return Decimal(balance['available'])
            return Decimal('0')
        except BitgetAPIException as e:
            logger.error(f"Error getting balance for {coin}: {str(e)}")
            raise
    
    def get_position(
        self,
        symbol: str,
        product_type: str = USDT_FUTURES
    ) -> Optional[Dict]:
        """Get current position for a symbol."""
        try:
            positions = self.client.get_positions(
                symbol=symbol,
                productType=product_type
            )
            return positions[0] if positions else None
        except BitgetAPIException as e:
            logger.error(f"Error getting position for {symbol}: {str(e)}")
            raise
    
    def get_leverage(
        self,
        symbol: str,
        product_type: str = USDT_FUTURES
    ) -> int:
        """Get current leverage for a symbol."""
        try:
            position = self.get_position(symbol, product_type)
            return int(position['leverage']) if position else 1
        except BitgetAPIException as e:
            logger.error(f"Error getting leverage for {symbol}: {str(e)}")
            raise
    
    def set_leverage(
        self,
        symbol: str,
        leverage: int,
        product_type: str = USDT_FUTURES,
        margin_mode: str = CROSS
    ) -> Dict:
        """Set leverage for a symbol."""
        try:
            return self.client.set_leverage(
                symbol=symbol,
                marginMode=margin_mode,
                leverage=leverage,
                productType=product_type
            )
        except BitgetAPIException as e:
            logger.error(f"Error setting leverage for {symbol}: {str(e)}")
            raise
    
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        size: Union[int, float],
        price: Optional[Union[int, float]] = None,
        product_type: str = USDT_FUTURES,
        reduce_only: bool = False
    ) -> Dict:
        """Place an order."""
        try:
            params = {
                'symbol': symbol,
                'side': side,
                'orderType': order_type,
                'size': str(size),
                'productType': product_type,
                'reduceOnly': reduce_only
            }
            
            if order_type == LIMIT and price is not None:
                params['price'] = str(price)
            
            return self.client.place_order(**params)
        except BitgetAPIException as e:
            logger.error(f"Error placing order for {symbol}: {str(e)}")
            raise
    
    def cancel_order(
        self,
        symbol: str,
        order_id: str,
        product_type: str = USDT_FUTURES
    ) -> Dict:
        """Cancel an order."""
        try:
            return self.client.cancel_order(
                symbol=symbol,
                orderId=order_id,
                productType=product_type
            )
        except BitgetAPIException as e:
            logger.error(f"Error canceling order {order_id}: {str(e)}")
            raise
    
    def get_open_orders(
        self,
        symbol: str,
        product_type: str = USDT_FUTURES
    ) -> List[Dict]:
        """Get all open orders for a symbol."""
        try:
            return self.client.get_open_orders(
                symbol=symbol,
                productType=product_type
            )
        except BitgetAPIException as e:
            logger.error(f"Error getting open orders for {symbol}: {str(e)}")
            raise
    
    def get_order_history(
        self,
        symbol: str,
        product_type: str = USDT_FUTURES,
        limit: int = 100
    ) -> List[Dict]:
        """Get order history for a symbol."""
        try:
            return self.client.get_order_history(
                symbol=symbol,
                productType=product_type,
                limit=limit
            )
        except BitgetAPIException as e:
            logger.error(f"Error getting order history for {symbol}: {str(e)}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """Get current funding rate for a symbol."""
        try:
            return self.client.get_funding_rate(symbol=symbol)
        except BitgetAPIException as e:
            logger.error(f"Error getting funding rate for {symbol}: {str(e)}")
            raise
    
    def get_mark_price(self, symbol: str) -> Decimal:
        """Get current mark price for a symbol."""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return Decimal(ticker['markPrice'])
        except BitgetAPIException as e:
            logger.error(f"Error getting mark price for {symbol}: {str(e)}")
            raise
    
    def get_available_symbols(
        self,
        product_type: str = USDT_FUTURES
    ) -> List[Dict]:
        """Get all available trading symbols."""
        try:
            return self.client.get_contracts_info(productType=product_type)
        except BitgetAPIException as e:
            logger.error(f"Error getting available symbols: {str(e)}")
            raise 