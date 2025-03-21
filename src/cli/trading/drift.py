#!/usr/bin/env python3
"""
Drift Trading CLI Component

Handles all Drift trading operations including:
- Position management
- Order execution
- Account monitoring
- Balance checking
- Subaccount management
- GUI trading interface
"""

from typing import Optional, Dict, Any, List
from argparse import _SubParsersAction
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import asyncio

from ..base import BaseCLI
from ...core.config import Config
from ...trading.drift.drift_adapter import DriftAdapter
from ...trading.drift.drift_qt_gui import DriftGUI
from ...trading.mainnet.drift_position_monitor import DriftPositionMonitor
from ...trading.mainnet.security_limits import SecurityLimits
from ...utils.wallet.wallet_manager import WalletManager

# Initialize Rich console for pretty output
console = Console()

class DriftCLI(BaseCLI):
    """CLI component for Drift trading operations"""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.adapter: Optional[DriftAdapter] = None
        self.monitor: Optional[DriftPositionMonitor] = None
        self.security: Optional[SecurityLimits] = None
        self.gui: Optional[DriftGUI] = None
        self.wallet_manager = WalletManager()
    
    async def setup(self) -> None:
        """Initialize Drift components"""
        self.adapter = DriftAdapter(self.config)
        self.security = SecurityLimits(self.config)
        await self.adapter.initialize()
    
    async def cleanup(self) -> None:
        """Cleanup Drift components"""
        if self.monitor:
            await self.monitor.stop()
        if self.adapter:
            await self.adapter.cleanup()
        if self.gui:
            self.gui.close()
    
    def add_arguments(self, parser: _SubParsersAction) -> None:
        """Add Drift trading arguments"""
        drift_parser = parser.add_parser("drift", help="Drift trading operations")
        subparsers = drift_parser.add_subparsers(dest="drift_command")
        
        # GUI command
        gui_parser = subparsers.add_parser("gui", help="Launch GUI trading interface")
        gui_parser.add_argument(
            "--wallet",
            required=True,
            help="Wallet to use for trading"
        )
        gui_parser.add_argument(
            "--dark-mode",
            action="store_true",
            help="Use dark mode theme"
        )
        
        # List wallets command
        list_parser = subparsers.add_parser("list", help="List available wallets")
        
        # Balance command
        balance_parser = subparsers.add_parser("balance", help="Check wallet balance and positions")
        balance_parser.add_argument(
            "--wallet",
            required=True,
            help="Wallet name"
        )
        balance_parser.add_argument(
            "--subaccount",
            type=int,
            default=0,
            help="Subaccount ID to check"
        )
        
        # Subaccounts command
        subaccounts_parser = subparsers.add_parser("subaccounts", help="List subaccounts")
        subaccounts_parser.add_argument(
            "--wallet",
            help="Optional wallet name (lists all if not specified)"
        )
        
        # Position management
        position_parser = subparsers.add_parser("position", help="Manage positions")
        position_parser.add_argument(
            "--market",
            required=True,
            help="Market symbol (e.g., SOL-PERP)"
        )
        position_parser.add_argument(
            "--size",
            type=float,
            required=True,
            help="Position size"
        )
        position_parser.add_argument(
            "--side",
            choices=["long", "short"],
            required=True,
            help="Position side"
        )
        position_parser.add_argument(
            "--leverage",
            type=float,
            default=1.0,
            help="Position leverage"
        )
        position_parser.add_argument(
            "--reduce-only",
            action="store_true",
            help="Make this a reduce-only order"
        )
        
        # Close position command
        close_parser = subparsers.add_parser("close", help="Close positions")
        close_parser.add_argument(
            "--market",
            required=True,
            help="Market to close position for"
        )
        close_parser.add_argument(
            "--size",
            type=float,
            help="Size to close (optional, closes entire position if not specified)"
        )
        
        # Monitor positions
        monitor_parser = subparsers.add_parser("monitor", help="Monitor positions")
        monitor_parser.add_argument(
            "--markets",
            required=True,
            help="Comma-separated list of markets to monitor"
        )
        monitor_parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Update interval in seconds"
        )
        
        # Health check
        health_parser = subparsers.add_parser("health", help="Check position health")
        health_parser.add_argument(
            "--market",
            required=True,
            help="Market to check health for"
        )
    
    async def handle_command(self, args: Any) -> None:
        """Handle Drift trading commands"""
        if args.drift_command == "gui":
            await self._handle_gui(args)
        elif args.drift_command == "list":
            await self._handle_list()
        elif args.drift_command == "balance":
            await self._handle_balance(args)
        elif args.drift_command == "subaccounts":
            await self._handle_subaccounts(args)
        elif args.drift_command == "position":
            await self._handle_position(args)
        elif args.drift_command == "close":
            await self._handle_close(args)
        elif args.drift_command == "monitor":
            await self._handle_monitor(args)
        elif args.drift_command == "health":
            await self._handle_health(args)
            
    async def _handle_gui(self, args: Any) -> None:
        """Handle GUI launch"""
        try:
            # Get wallet
            wallet = self.wallet_manager.get_wallet(args.wallet)
            if not wallet:
                console.print(f"[red]Error: Wallet '{args.wallet}' not found[/red]")
                return

            console.print("[yellow]Launching Drift GUI trading interface...[/yellow]")
            
            # Initialize GUI
            self.gui = DriftGUI(
                wallet=wallet,
                config=self.config,
                dark_mode=args.dark_mode
            )
            
            # Start GUI
            self.gui.show()
            
            # Keep running until GUI is closed
            while self.gui and self.gui.isVisible():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            console.print(f"[red]Error launching GUI: {str(e)}[/red]")
            self.logger.error(f"Error launching GUI: {str(e)}")
            raise
    
    async def _handle_list(self) -> None:
        """Handle wallet listing"""
        wallets = self.wallet_manager.list_wallets()
        
        if not wallets:
            console.print("[yellow]No wallets configured[/yellow]")
            return
            
        table = Table(title="Available Wallets", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Public Key", style="green")
        table.add_column("Status", style="magenta")
        
        for wallet_name in wallets:
            wallet = self.wallet_manager.get_wallet(wallet_name)
            if wallet:
                pubkey = str(wallet.get_public_key())
                table.add_row(
                    wallet_name,
                    f"{pubkey[:10]}...{pubkey[-6:]}",
                    "Active" if self.wallet_manager.current_wallet and self.wallet_manager.current_wallet.name == wallet_name else ""
                )
        
        console.print(table)
    
    async def _handle_balance(self, args: Any) -> None:
        """Handle balance check"""
        try:
            # Get user account
            user = await self.adapter.get_user_account(args.wallet, args.subaccount)
            if not user:
                console.print("[red]No user account found[/red]")
                return
                
            # Display account overview
            wallet = self.wallet_manager.get_wallet(args.wallet)
            console.print(Panel(
                f"[bold cyan]Account Overview[/bold cyan]\n"
                f"Wallet: {args.wallet}\n"
                f"Public Key: {wallet.get_public_key()}\n"
                f"Subaccount: {args.subaccount}\n"
                f"Network: {self.adapter.network}",
                title="🏦 Account Info",
                box=box.ROUNDED
            ))
            
            # Display spot positions
            spot_table = Table(title="📈 Spot Positions", box=box.ROUNDED)
            spot_table.add_column("Market", style="cyan")
            spot_table.add_column("Amount", style="green", justify="right")
            spot_table.add_column("Price", justify="right")
            spot_table.add_column("Value", style="bold green", justify="right")
            
            for position in await self.adapter.get_spot_positions(user):
                spot_table.add_row(
                    position.market,
                    f"{position.amount:.6f}",
                    f"${position.price:.2f}",
                    f"${position.value:.2f}"
                )
            
            console.print(spot_table)
            
            # Display perp positions
            perp_table = Table(title="🔄 Perpetual Positions", box=box.ROUNDED)
            perp_table.add_column("Market", style="cyan")
            perp_table.add_column("Size", style="green", justify="right")
            perp_table.add_column("Entry", justify="right")
            perp_table.add_column("Current", justify="right")
            perp_table.add_column("Value", style="bold green", justify="right")
            perp_table.add_column("PnL", style="bold magenta", justify="right")
            
            for position in await self.adapter.get_perp_positions(user):
                perp_table.add_row(
                    position.market,
                    f"{position.size:.6f}",
                    f"${position.entry_price:.2f}",
                    f"${position.current_price:.2f}",
                    f"${position.value:.2f}",
                    f"${position.unrealized_pnl:.2f}"
                )
            
            console.print(perp_table)
            
            # Display risk metrics
            metrics = await self.adapter.get_risk_metrics(user)
            console.print(Panel(
                f"[bold cyan]Risk Metrics[/bold cyan]\n"
                f"Total Collateral: ${metrics.total_collateral:.2f}\n"
                f"Free Collateral: ${metrics.free_collateral:.2f}\n"
                f"Margin Requirement: ${metrics.margin_requirement:.2f}\n"
                f"Current Leverage: {metrics.leverage:.2f}x",
                title="💪 Account Health",
                box=box.ROUNDED
            ))
            
        except Exception as e:
            self.logger.error(f"Error checking balance: {str(e)}")
            raise
            
    async def _handle_subaccounts(self, args: Any) -> None:
        """Handle subaccount listing"""
        try:
            wallets_to_check = [args.wallet] if args.wallet else self.wallet_manager.list_wallets()
            
            for wallet_name in wallets_to_check:
                subaccounts = await self.adapter.get_subaccounts(wallet_name)
                
                if not subaccounts:
                    console.print(f"[yellow]No subaccounts found for wallet {wallet_name}[/yellow]")
                    continue
                
                table = Table(title=f"Subaccounts for {wallet_name}", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Status", style="magenta")
                
                for subaccount in subaccounts:
                    table.add_row(
                        str(subaccount.id),
                        subaccount.name or "Main" if subaccount.id == 0 else f"Subaccount {subaccount.id}",
                        "Active" if subaccount.is_active else ""
                    )
                
                console.print(table)
                
        except Exception as e:
            self.logger.error(f"Error listing subaccounts: {str(e)}")
            raise
    
    async def _handle_position(self, args: Any) -> None:
        """Handle position creation/modification"""
        try:
            # Validate through security limits first
            self.security.validate_trade(args.market, args.size, args.side)
            
            position = await self.adapter.open_position(
                market=args.market,
                size=args.size,
                side=args.side,
                leverage=args.leverage,
                reduce_only=args.reduce_only
            )
            
            console.print("[green]Position opened successfully![/green]")
            console.print(Panel(
                f"[bold cyan]Position Details[/bold cyan]\n"
                f"Market: {position.market}\n"
                f"Side: {position.side}\n"
                f"Size: {position.size}\n"
                f"Entry Price: ${position.entry_price:.2f}\n"
                f"Leverage: {position.leverage}x\n"
                f"Liquidation Price: ${position.liquidation_price:.2f}",
                title="📊 Position Info",
                box=box.ROUNDED
            ))
        
        except Exception as e:
            console.print(f"[red]Error opening position: {str(e)}[/red]")
            self.logger.error(f"Error managing position: {str(e)}")
            raise
    
    async def _handle_close(self, args: Any) -> None:
        """Handle position closing"""
        try:
            result = await self.adapter.close_position(
                market=args.market,
                size=args.size
            )
            
            console.print("[green]Position closed successfully![/green]")
            console.print(Panel(
                f"[bold cyan]Close Details[/bold cyan]\n"
                f"Market: {args.market}\n"
                f"Size: {args.size if args.size else 'Full position'}\n"
                f"Transaction: {result['signature']}",
                title="🔒 Close Info",
                box=box.ROUNDED
            ))
            
        except Exception as e:
            console.print(f"[red]Error closing position: {str(e)}[/red]")
            self.logger.error(f"Error closing position: {str(e)}")
            raise
    
    async def _handle_monitor(self, args: Any) -> None:
        """Handle position monitoring"""
        try:
            markets = [m.strip() for m in args.markets.split(",")]
            console.print("[yellow]Starting position monitor...[/yellow]")
            
            while True:
                positions = await self.adapter.get_positions(markets)
                
                table = Table(title="Position Monitor")
                table.add_column("Market", style="cyan")
                table.add_column("Size", style="magenta")
                table.add_column("Entry Price", style="green")
                table.add_column("Current Price", style="yellow")
                table.add_column("PnL", style="bold red")
                table.add_column("Health", style="bold blue")
                
                for pos in positions:
                    table.add_row(
                        pos.market,
                        str(pos.size),
                        f"${pos.entry_price:.2f}",
                        f"${pos.current_price:.2f}",
                        f"${pos.unrealized_pnl:.2f}",
                        f"{pos.health_ratio:.2f}%"
                    )
                
                console.clear()
                console.print(table)
                
                await asyncio.sleep(args.interval)
                
        except KeyboardInterrupt:
            console.print("[yellow]Stopping monitor...[/yellow]")
        except Exception as e:
            console.print(f"[red]Error in monitor: {str(e)}[/red]")
            self.logger.error(f"Error monitoring positions: {str(e)}")
            raise

    async def _handle_health(self, args: Any) -> None:
        """Handle position health check"""
        try:
            health = await self.adapter.get_position_health(args.market)
            
            console.print(Panel(
                f"[bold cyan]Position Health for {args.market}[/bold cyan]\n"
                f"Health Ratio: {health.health_ratio:.2f}%\n"
                f"Liquidation Price: ${health.liquidation_price:.2f}\n"
                f"Distance to Liquidation: {health.liquidation_distance:.2f}%\n"
                f"{'[red bold]WARNING: Low position health![/red bold]' if health.health_ratio < 15 else ''}",
                title="💪 Health Check",
                box=box.ROUNDED
            ))
            
        except Exception as e:
            console.print(f"[red]Error checking health: {str(e)}[/red]")
            self.logger.error(f"Error checking health: {str(e)}")
            raise 