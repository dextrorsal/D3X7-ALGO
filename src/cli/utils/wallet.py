#!/usr/bin/env python3
"""
Wallet Management CLI Component

Handles all wallet operations including:
- Wallet listing and creation
- Balance checking
- Key management
"""

from typing import Optional, Dict, Any
from argparse import _SubParsersAction

from ..base import BaseCLI
from ...core.config import Config
from ...utils.wallet.wallet_manager import WalletManager

class WalletCLI(BaseCLI):
    """CLI component for wallet management"""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.manager: Optional[WalletManager] = None
    
    async def setup(self) -> None:
        """Initialize wallet manager"""
        self.manager = WalletManager(self.config)
        await self.manager.initialize()
    
    async def cleanup(self) -> None:
        """Cleanup wallet manager"""
        if self.manager:
            await self.manager.cleanup()
    
    def add_arguments(self, parser: _SubParsersAction) -> None:
        """Add wallet management arguments"""
        wallet_parser = parser.add_parser("wallet", help="Wallet management")
        subparsers = wallet_parser.add_subparsers(dest="wallet_command")
        
        # List wallets
        subparsers.add_parser("list", help="List all wallets")
        
        # Create wallet
        create_parser = subparsers.add_parser("create", help="Create new wallet")
        create_parser.add_argument(
            "name",
            help="Wallet name"
        )
        create_parser.add_argument(
            "--keypair",
            help="Path to keypair file"
        )
        
        # Check balance
        balance_parser = subparsers.add_parser("balance", help="Check wallet balance")
        balance_parser.add_argument(
            "name",
            help="Wallet name"
        )
        balance_parser.add_argument(
            "--tokens",
            action="store_true",
            help="Include token balances"
        )
        
        # Export keys
        export_parser = subparsers.add_parser("export", help="Export wallet keys")
        export_parser.add_argument(
            "name",
            help="Wallet name"
        )
        export_parser.add_argument(
            "--output",
            help="Output file path"
        )
    
    async def handle_command(self, args: Any) -> None:
        """Handle wallet commands"""
        if args.wallet_command == "list":
            await self._handle_list()
        elif args.wallet_command == "create":
            await self._handle_create(args)
        elif args.wallet_command == "balance":
            await self._handle_balance(args)
        elif args.wallet_command == "export":
            await self._handle_export(args)
    
    async def _handle_list(self) -> None:
        """Handle wallet listing"""
        try:
            wallets = await self.manager.list_wallets()
            
            if not wallets:
                print("\nNo wallets found")
                return
            
            print("\nAvailable Wallets:")
            for wallet in wallets:
                print(self.format_output({
                    "Name": wallet["name"],
                    "Address": wallet["address"],
                    "Type": wallet["type"]
                }))
        
        except Exception as e:
            self.logger.error(f"Error listing wallets: {str(e)}")
            raise
    
    async def _handle_create(self, args: Any) -> None:
        """Handle wallet creation"""
        try:
            wallet = await self.manager.create_wallet(
                name=args.name,
                keypair_path=args.keypair
            )
            
            print("\nWallet Created:")
            print(self.format_output({
                "Name": wallet.name,
                "Address": wallet.address,
                "Type": wallet.type
            }))
            
            if not args.keypair:
                print("\nIMPORTANT: Please backup your keypair file!")
        
        except Exception as e:
            self.logger.error(f"Error creating wallet: {str(e)}")
            raise
    
    async def _handle_balance(self, args: Any) -> None:
        """Handle balance check"""
        try:
            balance = await self.manager.get_balance(args.name)
            
            print(f"\nWallet: {args.name}")
            print(self.format_output({
                "SOL Balance": f"{balance.sol_balance:.6f} SOL",
                "USD Value": f"${balance.usd_value:.2f}"
            }))
            
            if args.tokens:
                print("\nToken Balances:")
                for token in balance.tokens:
                    print(self.format_output({
                        "Token": token.symbol,
                        "Amount": f"{token.amount:.6f}",
                        "USD Value": f"${token.usd_value:.2f}"
                    }))
        
        except Exception as e:
            self.logger.error(f"Error checking balance: {str(e)}")
            raise
    
    async def _handle_export(self, args: Any) -> None:
        """Handle key export"""
        try:
            output_path = await self.manager.export_keys(
                name=args.name,
                output_path=args.output
            )
            
            print(f"\nKeys exported to: {output_path}")
            print("IMPORTANT: Store this file securely!")
        
        except Exception as e:
            self.logger.error(f"Error exporting keys: {str(e)}")
            raise 