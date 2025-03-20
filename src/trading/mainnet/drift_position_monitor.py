#!/usr/bin/env python3
"""
🔍 Drift Position Monitor
Real-time position monitoring system for Drift market making, with advanced analytics
and risk management features.
"""

import asyncio
import logging
import argparse
import os
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import json
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate

from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    PositionDirection,
    TxParams
)
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION, MARGIN_PRECISION, AMM_RESERVE_PRECISION
from driftpy.decode.utils import decode_name
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from anchorpy.provider import Provider, Wallet
from driftpy.drift_client import DriftClient
from driftpy.drift_user import DriftUser
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.accounts import get_perp_market_account, get_spot_market_account

# Import wallet management system
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.encryption import WalletEncryption
from src.trading.drift.account_manager import DriftAccountManager
from src.trading.drift.management.drift_wallet_manager import DriftWalletManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich import box

from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from anchorpy.provider import Provider, Wallet
from driftpy.drift_client import DriftClient
from driftpy.drift_user import DriftUser
from driftpy.accounts import get_perp_market_account, get_spot_market_account
from driftpy.constants.numeric_constants import AMM_RESERVE_PRECISION

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI colors for beautiful terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DriftPositionMonitor:
    """Real-time position monitoring for Drift market making."""
    
    def __init__(self, 
                 wallet_name: str,
                 subaccount_id: int = 0,
                 env: str = 'mainnet',
                 use_cache: bool = True,
                 update_interval: int = 5):
        """
        Initialize the position monitor.
        
        Args:
            wallet_name: Name of the wallet to monitor
            subaccount_id: Subaccount ID to monitor
            env: Environment ('mainnet' or 'devnet')
            use_cache: Whether to use caching for RPC calls
            update_interval: How often to update positions (seconds)
        """
        self.wallet_name = wallet_name.upper()
        self.subaccount_id = subaccount_id
        self.env = env
        self.use_cache = use_cache
        self.update_interval = update_interval
        
        # Initialize managers
        self.drift_wallet_manager = DriftWalletManager()
        self.wallet_manager = WalletManager()
        self.account_manager = None
        
        # State tracking
        self.positions: Dict = {}
        self.market_data: Dict = {}
        self.last_update: Optional[datetime] = None
        self.is_running: bool = False
        
        # Market Making Metrics
        self.mm_metrics = {
            'spread': {},           # Market -> Current spread
            'inventory_skew': {},   # Market -> Current inventory skew
            'order_imbalance': {},  # Market -> Order book imbalance
            'market_impact': {},    # Market -> Estimated market impact
            'funding_rates': {},    # Market -> Current funding rate
            'volume_24h': {},       # Market -> 24h volume
            'trades_24h': {},       # Market -> Number of trades in 24h
            'quote_depth': {},      # Market -> Quote depth at various levels
        }
        
        # Risk metrics
        self.max_position_size: Dict[int, float] = {}  # market_index -> size
        self.max_leverage: Dict[int, float] = {}       # market_index -> leverage
        self.position_alerts: List[str] = []
        self.risk_metrics = {
            'liquidation_prices': {},    # Market -> Liquidation price
            'margin_ratios': {},         # Market -> Current margin ratio
            'concentration_risk': {},     # Market -> Concentration score
            'correlation_risk': {},       # Market -> Correlation with other positions
            'volatility_exposure': {},    # Market -> Volatility exposure
        }
        
        # Performance tracking
        self.total_pnl: Decimal = Decimal('0')
        self.daily_volume: Dict[int, Decimal] = {}     # market_index -> volume
        self.funding_payments: Dict[int, Decimal] = {} # market_index -> funding
        self.performance_metrics = {
            'realized_pnl_24h': Decimal('0'),
            'unrealized_pnl_24h': Decimal('0'),
            'fees_24h': Decimal('0'),
            'roi_24h': Decimal('0'),
            'sharpe_ratio': Decimal('0'),
            'max_drawdown': Decimal('0'),
            'win_rate': Decimal('0'),
        }
        
        # Initialize metrics storage
        self.metrics_dir = Path(os.path.expanduser("~/.config/drift_monitor/metrics"))
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize Drift client and account manager."""
        print(f"\n{Colors.CYAN}=== Initializing Drift Position Monitor ==={Colors.RESET}")
        print(f"✓ Wallet: {Colors.GREEN}{self.wallet_name}{Colors.RESET}")
        print(f"✓ Subaccount: {Colors.GREEN}{self.subaccount_id}{Colors.RESET}")
        print(f"✓ Environment: {Colors.GREEN}{self.env}{Colors.RESET}")
        
        try:
            # Check if wallet exists
            wallet = self.wallet_manager.get_wallet(self.wallet_name)
            if not wallet:
                raise Exception(f"Wallet '{self.wallet_name}' not found")
            
            # Check if subaccount exists
            config = self.drift_wallet_manager.get_subaccount_config(self.wallet_name, self.subaccount_id)
            if not config:
                raise Exception(f"Subaccount {self.subaccount_id} not found for wallet {self.wallet_name}")
            
            # Initialize account manager
            self.account_manager = DriftAccountManager(self.wallet_name)
            await self.account_manager.setup(self.subaccount_id)
            
            print(f"{Colors.GREEN}✓ Successfully initialized monitor{Colors.RESET}\n")
            
        except Exception as e:
            print(f"{Colors.RED}Error initializing monitor: {e}{Colors.RESET}")
            raise
            
    async def update_market_data(self):
        """Update market state data and market making metrics."""
        try:
            # Get market data from account manager
            markets = await self.account_manager.drift_client.get_perp_market_accounts()
            for market in markets:
                market_index = market.market_index
                
                # Update market data
                self.market_data[market_index] = {
                    'sqrt_k': market.amm.sqrt_k,
                    'base_long': market.amm.base_asset_amount_long,
                    'base_short': market.amm.base_asset_amount_short,
                    'last_update': datetime.now()
                }
                
                # Calculate market making metrics
                self.mm_metrics['spread'][market_index] = self._calculate_spread(market)
                self.mm_metrics['inventory_skew'][market_index] = self._calculate_inventory_skew(market)
                self.mm_metrics['order_imbalance'][market_index] = self._calculate_order_imbalance(market)
                self.mm_metrics['market_impact'][market_index] = self._calculate_market_impact(market)
                self.mm_metrics['funding_rates'][market_index] = market.amm.last_funding_rate / 1e6
                self.mm_metrics['volume_24h'][market_index] = market.amm.volume24h / QUOTE_PRECISION
                self.mm_metrics['quote_depth'][market_index] = self._calculate_quote_depth(market)
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            
    def _calculate_spread(self, market) -> float:
        """Calculate current bid-ask spread."""
        try:
            mark_price = market.amm.historical_oracle_data.last_oracle_price / 1e6
            bid = mark_price * (1 - market.amm.base_spread / 1e6)
            ask = mark_price * (1 + market.amm.base_spread / 1e6)
            return (ask - bid) / mark_price * 100  # Return as percentage
        except:
            return 0.0
            
    def _calculate_inventory_skew(self, market) -> float:
        """Calculate inventory skew percentage."""
        try:
            net_position = (market.amm.base_asset_amount_long - market.amm.base_asset_amount_short) / BASE_PRECISION
            total_position = (market.amm.base_asset_amount_long + market.amm.base_asset_amount_short) / BASE_PRECISION
            return (net_position / total_position * 100) if total_position != 0 else 0
        except:
            return 0.0
            
    def _calculate_order_imbalance(self, market) -> float:
        """Calculate order book imbalance."""
        try:
            bids_value = market.amm.base_asset_amount_long * market.amm.historical_oracle_data.last_oracle_price / (BASE_PRECISION * QUOTE_PRECISION)
            asks_value = market.amm.base_asset_amount_short * market.amm.historical_oracle_data.last_oracle_price / (BASE_PRECISION * QUOTE_PRECISION)
            total_value = bids_value + asks_value
            return ((bids_value - asks_value) / total_value * 100) if total_value != 0 else 0
        except:
            return 0.0
            
    def _calculate_market_impact(self, market) -> float:
        """Calculate estimated market impact for standard size."""
        try:
            k = market.amm.sqrt_k ** 2
            standard_size = 100  # Example: 100 SOL
            price_impact = (standard_size * BASE_PRECISION) / k * 100
            return price_impact
        except:
            return 0.0
            
    def _calculate_quote_depth(self, market) -> Dict[str, float]:
        """Calculate quote depth at various levels."""
        try:
            mark_price = market.amm.historical_oracle_data.last_oracle_price / 1e6
            k = market.amm.sqrt_k ** 2 / (BASE_PRECISION * QUOTE_PRECISION)
            
            depths = {}
            for bps in [10, 20, 50]:  # 0.1%, 0.2%, 0.5%
                price_level = mark_price * (1 + bps/10000)
                depth = k * (price_level - mark_price)
                depths[f"{bps}bps"] = depth
            
            return depths
        except:
            return {"10bps": 0.0, "20bps": 0.0, "50bps": 0.0}
    
    async def update_positions(self):
        """Update position information and risk metrics."""
        try:
            # Update cache if enabled
            if self.use_cache:
                await self.account_manager.drift_user.set_cache()
            
            # Get current positions
            positions = await self.account_manager.drift_user.get_positions()
            
            # Get unrealized PnL
            upnl = await self.account_manager.drift_user.get_unrealized_pnl(with_funding=True)
            
            # Get leverage
            leverage = await self.account_manager.drift_user.get_leverage()
            current_leverage = leverage / 10_000  # Convert to human readable
            
            # Get free collateral
            free_collateral = await self.account_manager.drift_user.get_free_collateral()
            
            # Update state
            self.positions = {
                'positions': positions,
                'upnl': upnl,
                'leverage': current_leverage,
                'free_collateral': free_collateral,
                'last_update': datetime.now()
            }
            
            # Update risk metrics
            await self.update_risk_metrics()
            
            # Update performance metrics
            await self.update_performance_metrics()
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            
    async def update_risk_metrics(self):
        """Update detailed risk metrics."""
        try:
            for pos in self.positions['positions']:
                market_index = pos.market_index
                
                # Calculate liquidation price
                entry_price = pos.entry_price / 1e6
                size = pos.base_asset_amount / BASE_PRECISION
                collateral = self.positions['free_collateral']
                
                if size != 0:
                    # Simple liquidation price calculation (can be made more sophisticated)
                    margin_ratio = 0.0625  # Example: 6.25% maintenance margin
                    liquidation_price = entry_price * (1 - margin_ratio) if size > 0 else entry_price * (1 + margin_ratio)
                    self.risk_metrics['liquidation_prices'][market_index] = liquidation_price
                    
                    # Calculate margin ratio
                    current_margin = collateral / (abs(size) * entry_price)
                    self.risk_metrics['margin_ratios'][market_index] = current_margin
                    
                    # Calculate concentration risk (% of total position value)
                    total_position_value = sum(abs(p.base_asset_amount / BASE_PRECISION * p.entry_price / 1e6) 
                                            for p in self.positions['positions'])
                    position_value = abs(size * entry_price)
                    concentration = position_value / total_position_value if total_position_value > 0 else 0
                    self.risk_metrics['concentration_risk'][market_index] = concentration
                    
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
            
    async def update_performance_metrics(self):
        """Update detailed performance metrics."""
        try:
            # Get 24h PnL components
            self.performance_metrics['realized_pnl_24h'] = Decimal(str(self.positions.get('upnl', 0) / 1e6))
            
            # Calculate ROI
            initial_collateral = Decimal('1000')  # Example value
            current_collateral = Decimal(str(self.positions['free_collateral'] / 1e6))
            self.performance_metrics['roi_24h'] = (current_collateral - initial_collateral) / initial_collateral * 100
            
            # Update other metrics (simplified calculations for example)
            self.performance_metrics['sharpe_ratio'] = Decimal('1.5')  # Example value
            self.performance_metrics['max_drawdown'] = Decimal('5.0')  # Example value
            self.performance_metrics['win_rate'] = Decimal('60.0')     # Example value
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    def create_market_making_table(self) -> Table:
        """Create market making metrics table."""
        table = Table(title="📊 Market Making Metrics", box=box.ROUNDED)
        
        table.add_column("Market", justify="left", style="cyan")
        table.add_column("Spread %", justify="right")
        table.add_column("Inventory Skew", justify="right")
        table.add_column("Order Imbalance", justify="right")
        table.add_column("Funding Rate", justify="right")
        table.add_column("24h Volume", justify="right")
        
        for market_index in self.mm_metrics['spread'].keys():
            market_name = f"SOL-PERP" if market_index == 0 else f"Market-{market_index}"
            spread = f"{self.mm_metrics['spread'][market_index]:.3f}%"
            skew = f"{self.mm_metrics['inventory_skew'][market_index]:.1f}%"
            imbalance = f"{self.mm_metrics['order_imbalance'][market_index]:.1f}%"
            funding = f"{self.mm_metrics['funding_rates'][market_index]:.4f}%"
            volume = f"${self.mm_metrics['volume_24h'][market_index]:,.0f}"
            
            table.add_row(market_name, spread, skew, imbalance, funding, volume)
            
        return table
        
    def create_risk_table(self) -> Table:
        """Create risk metrics table."""
        table = Table(title="⚠️ Risk Metrics", box=box.ROUNDED)
        
        table.add_column("Market", justify="left", style="cyan")
        table.add_column("Position", justify="right")
        table.add_column("Leverage", justify="right")
        table.add_column("Margin Ratio", justify="right")
        table.add_column("Liq. Price", justify="right")
        table.add_column("Concentration", justify="right")
        
        for pos in self.positions.get('positions', []):
            market_index = pos.market_index
            market_name = f"SOL-PERP" if market_index == 0 else f"Market-{market_index}"
            
            size = pos.base_asset_amount / BASE_PRECISION
            position = f"{size:+.3f}"
            leverage = f"{self.positions['leverage']:.2f}x"
            margin = f"{self.risk_metrics['margin_ratios'].get(market_index, 0):.2%}"
            liq_price = f"${self.risk_metrics['liquidation_prices'].get(market_index, 0):.2f}"
            concentration = f"{self.risk_metrics['concentration_risk'].get(market_index, 0):.1%}"
            
            row_style = "red" if abs(size) > 0 else "default"
            table.add_row(market_name, position, leverage, margin, liq_price, concentration, style=row_style)
            
        return table
        
    def create_performance_table(self) -> Table:
        """Create performance metrics table."""
        table = Table(title="💰 Performance Metrics", box=box.ROUNDED)
        
        table.add_column("Metric", justify="left", style="cyan")
        table.add_column("Value", justify="right")
        
        metrics = [
            ("24h Realized PnL", f"${float(self.performance_metrics['realized_pnl_24h']):,.2f}"),
            ("24h ROI", f"{float(self.performance_metrics['roi_24h']):+.2f}%"),
            ("Sharpe Ratio", f"{float(self.performance_metrics['sharpe_ratio']):.2f}"),
            ("Max Drawdown", f"{float(self.performance_metrics['max_drawdown']):.1f}%"),
            ("Win Rate", f"{float(self.performance_metrics['win_rate']):.1f}%"),
        ]
        
        for metric, value in metrics:
            table.add_row(metric, value)
            
        return table
    
    def print_status(self):
        """Print current status to console with ANSI formatting."""
        # Clear screen
        print("\033[2J\033[H")  # ANSI clear screen and move cursor to home
        
        print(f"\n{Colors.CYAN}=== DRIFT POSITION MONITOR ==={Colors.RESET}")
        print(f"Last Update: {Colors.GREEN}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
        
        # Market Making Metrics Table
        print(f"{Colors.CYAN}📊 MARKET MAKING METRICS{Colors.RESET}")
        mm_data = []
        headers = ["Market", "Spread %", "Inventory Skew", "Order Imbalance", "Funding Rate", "24h Volume"]
        
        for market_index in sorted(self.mm_metrics['spread'].keys()):
            market_name = f"SOL-PERP" if market_index == 0 else f"Market-{market_index}"
            mm_data.append([
                market_name,
                f"{self.mm_metrics['spread'][market_index]:.3f}%",
                f"{self.mm_metrics['inventory_skew'][market_index]:.1f}%",
                f"{self.mm_metrics['order_imbalance'][market_index]:.1f}%",
                f"{self.mm_metrics['funding_rates'][market_index]:.4f}%",
                f"${self.mm_metrics['volume_24h'][market_index]:,.0f}"
            ])
        print(tabulate(mm_data, headers=headers, tablefmt="simple"))
        print()
        
        # Risk Metrics Table
        print(f"{Colors.CYAN}⚠️  RISK METRICS{Colors.RESET}")
        risk_data = []
        headers = ["Market", "Position", "Leverage", "Margin Ratio", "Liq. Price", "Concentration"]
        
        for pos in self.positions.get('positions', []):
            market_index = pos.market_index
            market_name = f"SOL-PERP" if market_index == 0 else f"Market-{market_index}"
            size = pos.base_asset_amount / BASE_PRECISION
            
            # Color code based on position size
            position_str = f"{size:+.3f}"
            if abs(size) > 0:
                position_str = f"{Colors.RED}{position_str}{Colors.RESET}"
            
            risk_data.append([
                market_name,
                position_str,
                f"{self.positions['leverage']:.2f}x",
                f"{self.risk_metrics['margin_ratios'].get(market_index, 0):.2%}",
                f"${self.risk_metrics['liquidation_prices'].get(market_index, 0):.2f}",
                f"{self.risk_metrics['concentration_risk'].get(market_index, 0):.1%}"
            ])
        print(tabulate(risk_data, headers=headers, tablefmt="simple"))
        print()
        
        # Performance Metrics Table
        print(f"{Colors.CYAN}💰 PERFORMANCE METRICS{Colors.RESET}")
        perf_data = []
        headers = ["Metric", "Value"]
        
        metrics = [
            ("24h Realized PnL", f"${float(self.performance_metrics['realized_pnl_24h']):,.2f}"),
            ("24h ROI", f"{float(self.performance_metrics['roi_24h']):+.2f}%"),
            ("Sharpe Ratio", f"{float(self.performance_metrics['sharpe_ratio']):.2f}"),
            ("Max Drawdown", f"{float(self.performance_metrics['max_drawdown']):.1f}%"),
            ("Win Rate", f"{float(self.performance_metrics['win_rate']):.1f}%")
        ]
        perf_data.extend(metrics)
        print(tabulate(perf_data, headers=headers, tablefmt="simple"))
        print()
        
        # Alerts
        if self.position_alerts:
            print(f"\n{Colors.CYAN}🚨 ALERTS{Colors.RESET}")
            for alert in self.position_alerts:
                print(f"{Colors.RED}• {alert}{Colors.RESET}")
        else:
            print(f"\n{Colors.GREEN}✓ No active alerts{Colors.RESET}")
            
    async def monitor_loop(self):
        """Main monitoring loop."""
        self.is_running = True
        
        while self.is_running:
            try:
                print(f"{Colors.CYAN}Updating market data...{Colors.RESET}")
                await self.update_market_data()
                
                print(f"{Colors.CYAN}Updating positions...{Colors.RESET}")
                await self.update_positions()
                
                print(f"{Colors.CYAN}Logging metrics...{Colors.RESET}")
                await self.log_metrics()
                
                self.print_status()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                print(f"{Colors.RED}Error in monitor loop: {e}{Colors.RESET}")
                await asyncio.sleep(1)  # Short sleep on error
    
    async def start(self):
        """Start the position monitor."""
        await self.initialize()
        logger.info("Starting position monitor...")
        await self.monitor_loop()
    
    def stop(self):
        """Stop the position monitor."""
        self.is_running = False
        logger.info("Stopping position monitor...")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Drift Position Monitor")
    parser.add_argument("--wallet", type=str, required=True, help="Wallet name")
    parser.add_argument("--subaccount", type=int, default=0, help="Subaccount ID")
    parser.add_argument("--env", type=str, default="mainnet", choices=["mainnet", "devnet"], help="Environment")
    parser.add_argument("--interval", type=int, default=5, help="Update interval in seconds")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    
    args = parser.parse_args()
    
    monitor = DriftPositionMonitor(
        wallet_name=args.wallet,
        subaccount_id=args.subaccount,
        env=args.env,
        use_cache=not args.no_cache,
        update_interval=args.interval
    )
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        logger.info("Monitor stopped by user")
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}")

if __name__ == "__main__":
    asyncio.run(main()) 