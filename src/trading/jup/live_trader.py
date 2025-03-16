"""
Live trading implementation for DEX exchanges (Drift/Jupiter)
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
from src.utils.solana.sol_rpc import get_solana_client

client = get_solana_client()
version_info = client.get_version()
print("Connected Solana node version:", version_info)


from src.core.config import Config
from src.core.models import TimeRange, StandardizedCandle
from src.core.exceptions import ExchangeError, ValidationError
from src.exchanges.base import BaseExchangeHandler
from src.storage.live import LiveDataStorage
from src.utils.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)

class LiveTrader:
    """
    Live trading implementation for executing trades based on strategy signals
    Supports Drift and Jupiter DEX platforms
    """

    def __init__(self, config: Config, strategy: BaseStrategy, exchange_name: str = "drift"):
        """
        Initialize live trader with configuration
        
        Args:
            config: Configuration object
            strategy: Trading strategy to generate signals
            exchange_name: Name of exchange to use (drift or jupiter)
        """
        self.config = config
        self.strategy = strategy
        self.exchange_name = exchange_name.lower()

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
        
        # Connect wallet (This would be platform-specific)
        self._connect_wallet()
        
    def _connect_wallet(self):
        """Connect to wallet for DEX trading"""
        # In a real implementation, this would handle connection to 
        # Solana wallet for Drift/Jupiter integration
        # 
        # For demonstration purposes, we'll just log this
        logger.info(f"Connecting wallet for {self.exchange_name} trading")
        
        # Example wallet connection (pseudo-code)
        if self.exchange_name == "drift":
            # Drift connection would go here
            # from solana.keypair import Keypair
            # from drift.client import DriftClient
            # keypath = self.config.get('wallet', {}).get('keypath')
            # keypair = Keypair.from_json(keypath) 
            # self.drift_client = DriftClient(keypair)
            pass
        elif self.exchange_name == "jupiter":
            # Jupiter connection would go here
            # from jupiter.client import JupiterClient
            # self.jupiter_client = JupiterClient(wallet_address)
            pass
        else:
            raise ValueError(f"Unsupported DEX: {self.exchange_name}")
            
        logger.info(f"Wallet connected successfully for {self.exchange_name}")
            
    async def get_account_balances(self) -> Dict[str, float]:
        """
        Get account balances
        
        Returns:
            Dictionary mapping asset symbols to amounts
        """
        # This would be platform-specific implementation
        # For demo, we'll return mock balances
        mock_balances = {
            "SOL": 10.0,
            "USDC": 1000.0,
            "BTC": 0.01,
            "ETH": 0.25
        }
        
        logger.info(f"Retrieved balances: {mock_balances}")
        return mock_balances
        
    async def get_market_price(self, market: str) -> float:
        """
        Get current market price for a symbol
        
        Args:
            market: Market symbol
            
        Returns:
            Current price
        """
        try:
            # Use the exchange handler to fetch the latest data
            candle = await self.exchange_handler.fetch_live_candles(
                market=market,
                resolution="1"  # 1-minute resolution for recent price
            )
            return candle.close
        except Exception as e:
            logger.error(f"Error fetching price for {market}: {e}")
            raise
        
    async def execute_buy(self, market: str, amount: float) -> Dict:
        """
        Execute a buy order
        
        Args:
            market: Market symbol
            amount: Amount to buy in quote currency (e.g., USDC)
            
        Returns:
            Order details
        """
        try:
            # Get current price
            current_price = await self.get_market_price(market)
            
            # Calculate quantity based on amount
            quantity = amount / current_price
            
            # In real implementation, this would call the DEX API
            # For demo purposes, we'll create a simulated order
            order_id = f"buy_{market}_{int(time.time())}"
            order_details = {
                "order_id": order_id,
                "market": market,
                "side": "buy",
                "price": current_price,
                "amount": amount,
                "quantity": quantity,
                "status": "executed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Log the order
            self._log_trade(order_details)
            
            # Update active positions
            self.active_positions[market] = {
                "entry_price": current_price,
                "quantity": quantity,
                "entry_time": datetime.now(timezone.utc),
                "stop_loss": current_price * (1 - self.stop_loss_pct/100),
                "take_profit": current_price * (1 + self.take_profit_pct/100)
            }
            
            # Update last trade time
            self.last_trade_time[market] = datetime.now(timezone.utc)
            
            logger.info(f"Executed buy order for {market}: {order_details}")
            return order_details
            
        except Exception as e:
            logger.error(f"Error executing buy for {market}: {e}")
            raise
            
    async def execute_sell(self, market: str, quantity: Optional[float] = None) -> Dict:
        """
        Execute a sell order
        
        Args:
            market: Market symbol
            quantity: Quantity to sell (None for full position)
            
        Returns:
            Order details
        """
        try:
            # Check if we have an active position
            if market not in self.active_positions:
                logger.warning(f"No active position for {market}")
                return {"status": "error", "message": "No active position"}
                
            position = self.active_positions[market]
            
            # Get current price
            current_price = await self.get_market_price(market)
            
            # If quantity not specified, sell entire position
            if quantity is None:
                quantity = position["quantity"]
                
            # Calculate amount
            amount = quantity * current_price
            
            # In real implementation, this would call the DEX API
            # For demo purposes, we'll create a simulated order
            order_id = f"sell_{market}_{int(time.time())}"
            order_details = {
                "order_id": order_id,
                "market": market,
                "side": "sell",
                "price": current_price,
                "amount": amount,
                "quantity": quantity,
                "status": "executed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "profit_loss": (current_price - position["entry_price"]) * quantity,
                "profit_loss_pct": (current_price / position["entry_price"] - 1) * 100
            }
            
            # Log the order
            self._log_trade(order_details)
            
            # Update active positions
            if quantity >= position["quantity"] * 0.99:  # Allow for small rounding errors
                # If selling entire position, remove it
                del self.active_positions[market]
            else:
                # Otherwise, update the position
                position["quantity"] -= quantity
                
            # Update last trade time
            self.last_trade_time[market] = datetime.now(timezone.utc)
            
            logger.info(f"Executed sell order for {market}: {order_details}")
            return order_details
            
        except Exception as e:
            logger.error(f"Error executing sell for {market}: {e}")
            raise
            
    def _log_trade(self, trade_details: Dict):
        """
        Log trade to file
        
        Args:
            trade_details: Trade details dictionary
        """
        try:
            # Load existing trades
            trades = []
            if self.trade_log_file.exists():
                with open(self.trade_log_file, 'r') as f:
                    trades = json.load(f)
                    
            # Add new trade
            trades.append(trade_details)
            
            # Write back to file
            with open(self.trade_log_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            
    async def check_stop_loss_take_profit(self, market: str) -> Optional[str]:
        """
        Check if stop loss or take profit has been triggered
        
        Args:
            market: Market symbol
            
        Returns:
            "stop_loss", "take_profit", or None
        """
        if market not in self.active_positions:
            return None
            
        position = self.active_positions[market]
        current_price = await self.get_market_price(market)
        
        # Check stop loss
        if current_price <= position["stop_loss"]:
            return "stop_loss"
            
        # Check take profit
        if current_price >= position["take_profit"]:
            return "take_profit"
            
        return None
            
    async def process_market_data(self, market: str, resolution: str = "15") -> Dict:
        """
        Process market data and generate signals
        
        Args:
            market: Market symbol
            resolution: Data resolution
            
        Returns:
            Dictionary with signal, prices, and analysis
        """
        try:
            # Get recent data (last 100 candles)
            now = datetime.now(timezone.utc)
            lookback_days = 7  # Adjust based on resolution and needed history
            
            time_range = TimeRange(
                start=now.replace(hour=0, minute=0, second=0, microsecond=0) - \
                      pd.Timedelta(days=lookback_days),
                end=now
            )
            
            # Get data from storage if available, otherwise fetch it
            from src.storage.processed import ProcessedDataStorage
            processed_storage = ProcessedDataStorage(self.config.storage)
            
            df = await processed_storage.load_candles(
                exchange=self.exchange_name,
                market=market,
                resolution=resolution,
                start_time=time_range.start,
                end_time=time_range.end
            )
            
            if df.empty:
                # If no data in storage, fetch it directly
                candles = await self.exchange_handler.fetch_historical_candles(
                    market=market,
                    time_range=time_range,
                    resolution=resolution
                )
                
                if not candles:
                    raise ValueError(f"No data available for {market}")
                    
                # Convert to DataFrame
                df = pd.DataFrame([{
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume
                } for c in candles])
                
                df.set_index("timestamp", inplace=True)
                df.sort_index(inplace=True)
                
            # Generate signals using the strategy
            signals = self.strategy.generate_signals(df)
            current_signal = signals.iloc[-1] if len(signals) > 0 else 0
            previous_signal = signals.iloc[-2] if len(signals) > 1 else 0
            
            return {
                "market": market,
                "resolution": resolution,
                "current_price": df["close"].iloc[-1],
                "current_signal": current_signal,
                "previous_signal": previous_signal,
                "signal_changed": current_signal != previous_signal,
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing data for {market}: {e}")
            return {
                "market": market,
                "resolution": resolution,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    async def run_trading_cycle(self, markets: List[str], resolution: str = "15"):
        """
        Run a complete trading cycle for specified markets
        
        Args:
            markets: List of market symbols
            resolution: Data resolution
        """
        logger.info(f"Starting trading cycle for markets: {markets}")
        
        # Get account balances
        try:
            balances = await self.get_account_balances()
            logger.info(f"Account balances: {balances}")
            
            # Available capital for trading (e.g., USDC balance)
            available_capital = balances.get("USDC", 0)
            
            if available_capital <= 0:
                logger.warning("No capital available for trading")
                return
                
            # Calculate maximum position size
            max_position_size = available_capital * (self.position_size_pct / 100)
            logger.info(f"Maximum position size: ${max_position_size:.2f}")
            
            # Process each market
            for market in markets:
                # Check existing positions for SL/TP
                if market in self.active_positions:
                    exit_reason = await self.check_stop_loss_take_profit(market)
                    
                    if exit_reason:
                        logger.info(f"Exit triggered for {market}: {exit_reason}")
                        await self.execute_sell(market)
                        continue
                    
                # Process market data
                analysis = await self.process_market_data(market, resolution)
                
                if "error" in analysis:
                    logger.error(f"Error analyzing {market}: {analysis['error']}")
                    continue
                    
                current_signal = analysis["current_signal"]
                signal_changed = analysis["signal_changed"]
                
                # Check cooldown period
                last_trade = self.last_trade_time.get(market, datetime.fromtimestamp(0, tz=timezone.utc))
                cooldown_period = pd.Timedelta(minutes=self.cooldown_minutes)
                
                if datetime.now(timezone.utc) - last_trade < cooldown_period:
                    logger.info(f"Skipping {market}: still in cooldown period")
                    continue
                
                # Handle signals
                if market in self.active_positions:
                    # We have an active position, check exit signals
                    if current_signal in (0, -1):  # Exit or reverse signal
                        logger.info(f"Exit signal for {market}: {current_signal}")
                        await self.execute_sell(market)
                elif current_signal == 1 and signal_changed:
                    # We don't have a position, check entry signals
                    if len(self.active_positions) < self.max_positions:
                        logger.info(f"Entry signal for {market}: {current_signal}")
                        # Calculate position size
                        position_size = min(max_position_size, available_capital)
                        await self.execute_buy(market, position_size)
                    else:
                        logger.info(f"Max positions reached, skipping entry for {market}")
                        
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            
    async def run_continuous(self, markets: List[str], resolution: str = "15", interval_seconds: int = 60):
        """
        Run continuous trading
        
        Args:
            markets: List of market symbols to trade
            resolution: Data resolution
            interval_seconds: Seconds between each trading cycle
        """
        logger.info(f"Starting continuous trading for {markets} at {interval_seconds}s intervals")
        
        try:
            # Start the exchange handler
            await self.exchange_handler.start()
            
            while True:
                start_time = time.time()
                
                try:
                    await self.run_trading_cycle(markets, resolution)
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    
                # Calculate elapsed time and sleep for the remaining interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval_seconds - elapsed)
                
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.2f}s until next cycle")
                    await asyncio.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Trading stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous trading: {e}")
        finally:
            # Stop the exchange handler
            await self.exchange_handler.stop()
            
    async def stop(self):
        """Stop trading and clean up resources"""
        # Close any active positions
        logger.info("Stopping trading and closing positions")
        
        for market in list(self.active_positions.keys()):
            try:
                logger.info(f"Closing position for {market}")
                await self.execute_sell(market)
            except Exception as e:
                logger.error(f"Error closing position for {market}: {e}")
                
        # Stop exchange handler
        await self.exchange_handler.stop()
        
        logger.info("Trading stopped")