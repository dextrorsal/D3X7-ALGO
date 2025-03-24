#!/usr/bin/env python3
"""
Wallet Management CLI - Wrapper for wallet management functionality.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from argparse import _SubParsersAction
from rich.console import Console
from rich.table import Table
from rich import box

from ..base import BaseCLI
from ...core.config import Config
from ...utils.wallet.wallet_manager import WalletManager

console = Console()
logger = logging.getLogger(__name__)

class WalletCLI(BaseCLI):
    """CLI wrapper for wallet management operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize wallet CLI wrapper."""
        super().__init__(config)
        self.wallet_manager = None
    
    async def start(self) -> None:
        """Initialize the wallet manager."""
        self.wallet_manager = WalletManager()
        await self.wallet_manager.initialize()
    
    async def stop(self) -> None:
        """Cleanup wallet manager."""
        if self.wallet_manager:
            await self.wallet_manager.cleanup()
    
    def add_arguments(self, parser: _SubParsersAction) -> None:
        """Add wallet-specific arguments to the parser."""
        wallet_parser = parser.add_parser("wallet", help="Wallet management operations")
        subparsers = wallet_parser.add_subparsers(dest="wallet_command")
        
        # List wallets command
        list_parser = subparsers.add_parser("list", help="List available wallets")
        
        # Create wallet command
        create_parser = subparsers.add_parser("create", help="Create new wallet")
        create_parser.add_argument(
            "--name",
            required=True,
            help="Name for the new wallet"
        )
        create_parser.add_argument(
            "--password",
            required=True,
            help="Password for wallet encryption"
        )
        
        # Import wallet command
        import_parser = subparsers.add_parser("import", help="Import existing wallet")
        import_parser.add_argument(
            "--name",
            required=True,
            help="Name for the imported wallet"
        )
        import_parser.add_argument(
            "--private-key",
            required=True,
            help="Private key to import"
        )
        import_parser.add_argument(
            "--password",
            required=True,
            help="Password for wallet encryption"
        )
        
        # Balance command
        balance_parser = subparsers.add_parser("balance", help="Check wallet balance")
        balance_parser.add_argument(
            "--name",
            required=True,
            help="Wallet name"
        )
        balance_parser.add_argument(
            "--token",
            help="Optional token to check balance for (default: SOL)"
        )
        
        # Set active wallet command
        active_parser = subparsers.add_parser("use", help="Set active wallet")
        active_parser.add_argument(
            "--name",
            required=True,
            help="Wallet name to set as active"
        )
        
        # Delete wallet command
        delete_parser = subparsers.add_parser("delete", help="Delete wallet")
        delete_parser.add_argument(
            "--name",
            required=True,
            help="Wallet name to delete"
        )
        delete_parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion without confirmation"
        )
    
    async def handle_command(self, args: Any) -> None:
        """Handle wallet CLI commands."""
        if not hasattr(args, 'wallet_command'):
            logger.error("No wallet command specified")
            return

        try:
            if args.wallet_command == "list":
                await self._handle_list()
            elif args.wallet_command == "create":
                await self._handle_create(args)
            elif args.wallet_command == "import":
                await self._handle_import(args)
            elif args.wallet_command == "balance":
                await self._handle_balance(args)
            elif args.wallet_command == "use":
                await self._handle_use(args)
            elif args.wallet_command == "delete":
                await self._handle_delete(args)

        except Exception as e:
            logger.error(f"Error in wallet command: {str(e)}")
            raise
    
    async def _handle_list(self) -> None:
        """Handle wallet listing."""
        wallets = self.wallet_manager.list_wallets()
        
        if not wallets:
            console.print("[yellow]No wallets configured[/yellow]")
            return
            
        table = Table(title="Available Wallets", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Public Key", style="green")
        table.add_column("Status", style="magenta")
        
        for wallet in wallets:
            pubkey = str(wallet.public_key)
            table.add_row(
                wallet.name,
                f"{pubkey[:10]}...{pubkey[-6:]}",
                "Active" if wallet.is_active else ""
            )
        
        console.print(table)
    
    async def _handle_create(self, args: Any) -> None:
        """Handle wallet creation."""
        try:
            wallet = await self.wallet_manager.create_wallet(
                name=args.name,
                password=args.password
            )
            console.print(f"[green]Created new wallet:[/green] {wallet.name}")
            console.print(f"Public Key: {wallet.public_key}")
        except Exception as e:
            console.print(f"[red]Error creating wallet:[/red] {str(e)}")
            raise
    
    async def _handle_import(self, args: Any) -> None:
        """Handle wallet import."""
        try:
            wallet = await self.wallet_manager.import_wallet(
                name=args.name,
                private_key=args.private_key,
                password=args.password
            )
            console.print(f"[green]Imported wallet:[/green] {wallet.name}")
            console.print(f"Public Key: {wallet.public_key}")
        except Exception as e:
            console.print(f"[red]Error importing wallet:[/red] {str(e)}")
            raise
    
    async def _handle_balance(self, args: Any) -> None:
        """Handle balance check."""
        try:
            wallet = self.wallet_manager.get_wallet(args.name)
            if not wallet:
                console.print(f"[red]Wallet not found:[/red] {args.name}")
                return
            
            balance = await wallet.get_balance(args.token)
            token_name = args.token or "SOL"
            
            console.print(f"[green]Balance for {args.name}:[/green]")
            console.print(f"{balance} {token_name}")
        except Exception as e:
            console.print(f"[red]Error checking balance:[/red] {str(e)}")
            raise
    
    async def _handle_use(self, args: Any) -> None:
        """Handle setting active wallet."""
        try:
            await self.wallet_manager.set_active_wallet(args.name)
            console.print(f"[green]Set active wallet:[/green] {args.name}")
        except Exception as e:
            console.print(f"[red]Error setting active wallet:[/red] {str(e)}")
            raise
    
    async def _handle_delete(self, args: Any) -> None:
        """Handle wallet deletion."""
        try:
            if not args.force:
                confirm = input(f"Are you sure you want to delete wallet '{args.name}'? [y/N]: ")
                if confirm.lower() != 'y':
                    console.print("Deletion cancelled")
                    return
            
            await self.wallet_manager.delete_wallet(args.name)
            console.print(f"[green]Deleted wallet:[/green] {args.name}")
        except Exception as e:
            console.print(f"[red]Error deleting wallet:[/red] {str(e)}")
            raise 