#!/usr/bin/env python3
"""
Simple Drift CLI tool for managing wallets, subaccounts, and viewing positions
"""

import click
import logging
import asyncio
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Optional
from solders.keypair import Keypair
from anchorpy.provider import Wallet
from driftpy.drift_client import DriftClient
from driftpy.accounts import get_perp_market_account, get_spot_market_account
from driftpy.types import TxParams
from driftpy.account_subscription_config import AccountSubscriptionConfig
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_network, get_solana_client, NETWORK_URLS

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Rich console for pretty output
console = Console()

# Initialize wallet manager
wallet_manager = WalletManager()

@click.group()
def cli():
    """🚀 Drift Protocol CLI - Manage wallets, subaccounts, and view positions"""
    pass

@cli.command(name="list")
def list_wallets():
    """📋 List all available wallets"""
    wallets = wallet_manager.list_wallets()
    
    if not wallets:
        console.print("[yellow]No wallets configured[/yellow]")
        return
        
    table = Table(title="Available Wallets", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Public Key", style="green")
    table.add_column("Status", style="magenta")
    
    for wallet_name in wallets:
        wallet = wallet_manager.get_wallet(wallet_name)
        if wallet:
            pubkey = str(wallet.get_public_key())
            table.add_row(
                wallet_name,
                f"{pubkey[:10]}...{pubkey[-6:]}",
                "Active" if wallet_manager.current_wallet and wallet_manager.current_wallet.name == wallet_name else ""
            )
    
    console.print(table)

@cli.command(name="balance")
@click.argument("wallet_name")
@click.argument("subaccount_id", type=int)
async def check_balance(wallet_name: str, subaccount_id: int):
    """💰 Check wallet balance and positions
    
    Args:
        wallet_name: Name of the wallet
        subaccount_id: Subaccount ID to check
    """
    wallet_name = wallet_name.upper()
    
    try:
        # Get wallet
        wallet = wallet_manager.get_wallet(wallet_name)
        if not wallet:
            console.print(f"[red]Wallet '{wallet_name}' not found[/red]")
            return
            
        # Convert wallet for Drift
        if isinstance(wallet.keypair, bytes):
            keypair = Keypair.from_bytes(wallet.keypair)
        else:
            keypair = wallet.keypair
        anchor_wallet = Wallet(keypair)
        
        # Set up Drift client
        network = get_network()
        connection = await get_solana_client(network)
        
        drift_client = DriftClient(
            connection,
            anchor_wallet,
            network,
            tx_params=TxParams(compute_units=700_000, compute_units_price=10_000),
            account_subscription=AccountSubscriptionConfig("cached"),
            sub_account_ids=[subaccount_id]
        )
        
        await drift_client.subscribe()
        
        try:
            # Get user account
            drift_user = drift_client.get_user()
            if not drift_user:
                console.print("[red]No user account found[/red]")
                return
                
            user = drift_user.get_user_account()
            if not user:
                console.print("[red]No user account data found[/red]")
                return
            
            # Display account overview
            console.print(Panel(
                f"[bold cyan]Account Overview[/bold cyan]\n"
                f"Wallet: {wallet_name}\n"
                f"Public Key: {wallet.get_public_key()}\n"
                f"Subaccount: {subaccount_id}\n"
                f"Network: {network}",
                title="🏦 Account Info",
                box=box.ROUNDED
            ))
            
            # Display spot positions
            spot_table = Table(title="📈 Spot Positions", box=box.ROUNDED)
            spot_table.add_column("Market", style="cyan")
            spot_table.add_column("Amount", style="green", justify="right")
            spot_table.add_column("Price", justify="right")
            spot_table.add_column("Value", style="bold green", justify="right")
            
            for spot_position in user.spot_positions:
                if spot_position.scaled_balance != 0:
                    market = await get_spot_market_account(
                        drift_client.program,
                        spot_position.market_index
                    )
                    
                    token_amount = spot_position.scaled_balance / (10 ** market.decimals)
                    price = market.historical_oracle_data.last_oracle_price / 1e6
                    value = token_amount * price
                    
                    market_name = bytes(market.name).decode('utf-8').strip('\x00')
                    spot_table.add_row(
                        market_name,
                        f"{token_amount:.6f}",
                        f"${price:.2f}",
                        f"${value:.2f}"
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
            
            for perp_position in user.perp_positions:
                if perp_position.base_asset_amount != 0:
                    market = await get_perp_market_account(
                        drift_client.program,
                        perp_position.market_index
                    )
                    
                    position_size = perp_position.base_asset_amount / 1e9
                    entry_price = perp_position.get_entry_price() / 1e6
                    current_price = market.amm.historical_oracle_data.last_oracle_price / 1e6
                    position_value = position_size * current_price
                    unrealized_pnl = perp_position.get_unrealized_pnl(market) / 1e6
                    
                    market_name = bytes(market.name).decode('utf-8').strip('\x00')
                    perp_table.add_row(
                        market_name,
                        f"{position_size:.6f}",
                        f"${entry_price:.2f}",
                        f"${current_price:.2f}",
                        f"${position_value:.2f}",
                        f"${unrealized_pnl:.2f}"
                    )
            
            console.print(perp_table)
            
            # Display collateral info
            total_collateral = drift_user.get_total_collateral() / 1e6
            free_collateral = drift_user.get_free_collateral() / 1e6
            margin_requirement = drift_user.get_margin_requirement() / 1e6
            leverage = drift_user.get_leverage()
            
            console.print(Panel(
                f"[bold cyan]Risk Metrics[/bold cyan]\n"
                f"Total Collateral: ${total_collateral:.2f}\n"
                f"Free Collateral: ${free_collateral:.2f}\n"
                f"Margin Requirement: ${margin_requirement:.2f}\n"
                f"Current Leverage: {leverage:.2f}x",
                title="💪 Account Health",
                box=box.ROUNDED
            ))
            
        finally:
            await drift_client.unsubscribe()
            
    except Exception as e:
        console.print(f"[red]Error checking balance: {str(e)}[/red]")
        logger.exception("Balance check failed")

@cli.command(name="subaccounts")
@click.argument("wallet_name", required=False)
async def list_subaccounts(wallet_name: Optional[str] = None):
    """📊 List all subaccounts for a wallet"""
    try:
        if wallet_name:
            wallet_name = wallet_name.upper()
            wallet = wallet_manager.get_wallet(wallet_name)
            if not wallet:
                console.print(f"[red]Wallet '{wallet_name}' not found[/red]")
                return
        
        # Set up Drift client
        network = get_network()
        connection = await get_solana_client(network)
        
        # If no wallet specified, list for all wallets
        wallets_to_check = [wallet_name] if wallet_name else wallet_manager.list_wallets()
        
        for name in wallets_to_check:
            wallet = wallet_manager.get_wallet(name)
            if not wallet:
                continue
                
            # Convert wallet for Drift
            if isinstance(wallet.keypair, bytes):
                keypair = Keypair.from_bytes(wallet.keypair)
            else:
                keypair = wallet.keypair
            anchor_wallet = Wallet(keypair)
            
            drift_client = DriftClient(
                connection,
                anchor_wallet,
                network,
                tx_params=TxParams(compute_units=700_000, compute_units_price=10_000),
                account_subscription=AccountSubscriptionConfig("cached")
            )
            
            await drift_client.subscribe()
            
            try:
                # Get user account
                drift_user = drift_client.get_user()
                if not drift_user:
                    console.print(f"[yellow]No subaccounts found for wallet {name}[/yellow]")
                    continue
                    
                user = drift_user.get_user_account()
                if not user:
                    continue
                
                # Display subaccounts
                table = Table(title=f"Subaccounts for {name}", box=box.ROUNDED)
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Status", style="magenta")
                
                # Add subaccount rows (modify based on your needs)
                table.add_row(
                    "0",
                    "Main",
                    "Active" if user.sub_account_id == 0 else ""
                )
                
                console.print(table)
                
            finally:
                await drift_client.unsubscribe()
                
    except Exception as e:
        console.print(f"[red]Error listing subaccounts: {str(e)}[/red]")
        logger.exception("Subaccount listing failed")

def main():
    """Entry point for the CLI"""
    try:
        # Convert click commands to async
        loop = asyncio.get_event_loop()
        
        if "balance" in sys.argv:
            loop.run_until_complete(check_balance.callback(*sys.argv[2:]))
        elif "subaccounts" in sys.argv:
            loop.run_until_complete(list_subaccounts.callback(*sys.argv[2:]))
        else:
            cli()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting gracefully...[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()