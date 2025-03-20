"""
Live trading implementation for DEX exchanges (Drift/Jupiter)
Uses Jupiter Ultra API for optimal swaps
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from src.utils.wallet.sol_rpc import get_solana_client

from src.core.config import Config
from src.core.models import TimeRange, StandardizedCandle
from src.core.exceptions import ExchangeError, ValidationError
from src.exchanges.base import BaseExchangeHandler
from src.storage.live import LiveDataStorage
from src.utils.strategy.base import BaseStrategy
from src.trading.jup.jup_adapter import JupiterAdapter

logger = logging.getLogger(__name__)

class LiveTrader:
    """
    Live trading implementation for DEX exchanges
    Handles real-time data streaming and trade execution
    """
    
    def __init__(self, config: Config, strategy: BaseStrategy, exchange_name: str = "jupiter"):
        """
        Initialize live trader
        
        Args:
            config: Trading configuration
            strategy: Trading strategy instance
            exchange_name: Name of exchange to use
        """
        self.config = config
        self.strategy = strategy
        self.exchange_name = exchange_name.lower()
        self.client = None

        # Initialize Jupiter adapter for Ultra API
        if self.exchange_name == "jupiter":
            self.jupiter = JupiterAdapter(
                config_path=config.get("jupiter", {}).get("config_path"),
                network=config.get("jupiter", {}).get("network", "mainnet")
            )
        else:
            from src.exchanges import get_exchange_handler
            exchange_config = config.get("data_sources", {}).get(self.exchange_name)
            if not exchange_config:
                raise ValueError(f"Exchange {exchange_name} not configured")

            # Inject the exchange name into the dictionary
            exchange_config["name"] = self.exchange_name

            # Wrap the dictionary into an object that supports attribute access
            exchange_config_obj = SimpleNamespace(**exchange_config)
            self.exchange_handler = get_exchange_handler(exchange_config_obj)
        
        # Initialize storage for live data
        self.live_storage = LiveDataStorage(config.storage)
        
        # Trading parameters (load from config or use defaults)
        trading_config = config.get('trading', {})
        self.position_size_pct = trading_config.get('position_size_pct', 5.0)
        self.max_positions = trading_config.get('max_positions', 1)
        self.stop_loss_pct = trading_config.get('stop_loss_pct', 5.0)
        self.take_profit_pct = trading_config.get('take_profit_pct', 10.0)
        self.cooldown_minutes = trading_config.get('cooldown_minutes', 60)
        
        # Trading state
        self.active_positions = {}
        self.last_trade_time = {}
        self.pending_orders = {}
        
        # Path for trade log
        self.log_dir = Path("data/trade_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trade_log_file = self.log_dir / f"trade_log_{datetime.now().strftime('%Y%m%d')}.json"
        
        logger.info(f"Initialized LiveTrader with {exchange_name}")
            
    async def connect(self) -> bool:
        """
        Connect to the exchange and initialize required components
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize Solana client
            self.client = await get_solana_client()
            version_info = await self.client.get_version()
            logger.info(f"Connected to Solana node version: {version_info}")
            
            # Initialize Jupiter adapter for Ultra API
            if self.exchange_name == "jupiter":
                self.jupiter = JupiterAdapter(
                    config_path=self.config.get("jupiter", {}).get("config_path"),
                    network=self.config.get("jupiter", {}).get("network", "mainnet")
                )
                await self.jupiter.connect()
            else:
                from src.exchanges import get_exchange_handler
                exchange_config = self.config.get("data_sources", {}).get(self.exchange_name)
                if not exchange_config:
                    raise ValueError(f"Exchange {self.exchange_name} not configured")

                # Inject the exchange name into the dictionary
                exchange_config["name"] = self.exchange_name

                # Wrap the dictionary into an object that supports attribute access
                exchange_config_obj = SimpleNamespace(**exchange_config)
                self.exchange_handler = get_exchange_handler(exchange_config_obj)
                await self.exchange_handler.connect()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
            
    async def get_account_balances(self) -> Dict[str, float]:
        """
        Get account balances using Ultra API
        
        Returns:
            Dictionary mapping asset symbols to amounts
        """
        if self.exchange_name == "jupiter":
            return await self.jupiter.get_account_balances()
        else:
            return await self.exchange_handler.get_account_balances()
            
    async def execute_trade(self, market: str, side: str, amount: float) -> Dict:
        """
        Execute a trade using Jupiter Ultra API
        
        Args:
            market: Market symbol (e.g., "SOL-USDC")
            side: Trade side ("buy" or "sell")
            amount: Amount to trade
            
        Returns:
            Trade execution details
        """
        try:
            if self.exchange_name != "jupiter":
                raise ValueError("Trade execution only supported for Jupiter")
                
            # Use Ultra API for optimal swap execution
            if side.lower() == "buy":
                result = await self.jupiter.execute_swap(
                    market=market,
                    input_amount=amount,
                    slippage_bps=self.config.get("jupiter", {}).get("slippage_bps", 50)
                )
            else:
                # For sells, we need to reverse the market
                base, quote = market.split("-")
                reversed_market = f"{quote}-{base}"
                result = await self.jupiter.execute_swap(
                    market=reversed_market,
                    input_amount=amount,
                    slippage_bps=self.config.get("jupiter", {}).get("slippage_bps", 50)
                )
                
            # Log the trade
            trade_log = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market": market,
                "side": side,
                "amount": amount,
                "execution": result
            }
            
            with open(self.trade_log_file, "a") as f:
                f.write(json.dumps(trade_log) + "\n")
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            raise
            
    async def close(self):
        """Close connections and cleanup"""
        if hasattr(self, 'jupiter'):
            await self.jupiter.close()
        elif hasattr(self, 'exchange_handler'):
            await self.exchange_handler.close()