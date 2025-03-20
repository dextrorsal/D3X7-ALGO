#!/usr/bin/env python3
"""
CLI tool for managing Drift wallets and subaccounts.
"""

import click
import logging
import asyncio
import os
import sys
from dotenv import load_dotenv
from tabulate import tabulate  # Make sure to install this: pip install tabulate
import json
from pathlib import Path
from typing import Optional
from solders.keypair import Keypair
import argparse

from src.trading.drift.management.drift_wallet_manager import DriftWalletManager
from src.trading.drift.account_manager import DriftAccountManager
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_network, set_solana_network, NETWORK_URLS, get_solana_client
from solana.rpc.async_api import AsyncClient
from anchorpy.provider import Provider, Wallet
from driftpy.drift_client import DriftClient, TxOpts
from driftpy.drift_user import DriftUser
from driftpy.account_subscription_config import AccountSubscriptionConfig
from src.utils.wallet.encryption import WalletEncryption
from driftpy.accounts import get_perp_market_account, get_spot_market_account
from driftpy.types import TxParams

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize global managers
wallet_manager = WalletManager()

# Get config directory and RPC URL for DriftWalletManager
config_dir = os.path.expanduser("~/.config/solana/drift")
network = get_network()
rpc_url = NETWORK_URLS[network]

# Initialize DriftWalletManager with required parameters
drift_wallet_manager = DriftWalletManager(config_dir=config_dir, rpc_url=rpc_url)

# ANSI colors
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

@click.group()
def cli():
    """Drift CLI tool for managing wallets and subaccounts"""
    # Check encryption is enabled
    encryption_enabled = os.getenv('ENABLE_ENCRYPTION', 'false').lower() == 'true'
    wallet_password = os.getenv('WALLET_PASSWORD')
    
    print(f"\n{Colors.CYAN}=== Drift Configuration Status ==={Colors.RESET}")
    print(f"✓ Encryption enabled: {Colors.GREEN if encryption_enabled else Colors.RED}{encryption_enabled}{Colors.RESET}")
    print(f"✓ Wallet password configured: {Colors.GREEN if wallet_password else Colors.RED}{'Yes' if wallet_password else 'No'}{Colors.RESET}")
    
    # Check drift directory exists
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        print(f"✓ Drift directory: {Colors.YELLOW}Created{Colors.RESET}")
    else:
        print(f"✓ Drift directory: {Colors.GREEN}Exists{Colors.RESET}")
    print(f"{Colors.CYAN}================================{Colors.RESET}\n")

@cli.group()
def wallet():
    """Manage Drift wallets"""
    pass

@wallet.command()
def list():
    """List available wallets"""
    wallets = wallet_manager.list_wallets()
    
    if not wallets:
        print(f"{Colors.YELLOW}No wallets configured{Colors.RESET}")
        return
        
    print(f"\n{Colors.CYAN}=== AVAILABLE WALLETS ==={Colors.RESET}")
    
    # Create a table of wallet information
    wallet_data = []
    for wallet_name in wallets:
        wallet = wallet_manager.get_wallet(wallet_name)
        if wallet:
            wallet_data.append([
                wallet_name,
                str(wallet.get_public_key())[:10] + "..." + str(wallet.get_public_key())[-6:],
                "Active" if wallet_manager.current_wallet and wallet_manager.current_wallet.name == wallet_name else ""
            ])
    
    # Print table
    print(tabulate(wallet_data, headers=["Name", "Public Key", "Status"], tablefmt="simple"))

@wallet.command(name="balance")
@click.argument('wallet_name', required=True)
def check_native_balance(wallet_name):
    """Check native SOL balance for a wallet"""
    wallet_name = wallet_name.upper()
    
    # Get wallet
    wallet = wallet_manager.get_wallet(wallet_name)
    if not wallet:
        print(f"{Colors.RED}Wallet '{wallet_name}' not found{Colors.RESET}")
        return
        
    async def run_balance_check():
        # Get network and RPC URL from sol_rpc
        network = get_network()
        rpc_url = NETWORK_URLS[network]
        logger.info(f"Using network: {network} with RPC URL: {rpc_url}")
        client = AsyncClient(rpc_url)
        
        try:
            # Convert bytes to Keypair if needed
            if isinstance(wallet.keypair, bytes):
                keypair = Keypair.from_bytes(wallet.keypair)
            else:
                keypair = wallet.keypair
            
            # Get balance
            balance = await client.get_balance(keypair.pubkey())
            sol_balance = balance.value / 1e9  # Convert lamports to SOL
            
            print(f"\n{Colors.CYAN}=== NATIVE SOL BALANCE ==={Colors.RESET}")
            print(f"Wallet: {wallet_name}")
            print(f"Public Key: {keypair.pubkey()}")
            print(f"Balance: {Colors.GREEN}{sol_balance:.9f} SOL{Colors.RESET}")
            
        finally:
            await client.close()
    
    asyncio.run(run_balance_check())

@cli.group()
def subaccount():
    """Manage Drift subaccounts"""
    pass

@subaccount.command()
@click.argument('wallet_name')
@click.argument('subaccount_id', type=int)
@click.option('--name', help='Name for the subaccount')
def create(wallet_name: str, subaccount_id: int, name: str = None):
    """Create a new Drift subaccount"""
    try:
        print("\n=== Drift Configuration Status ===")
        print(f"✓ Encryption enabled: {os.getenv('WALLET_PASSWORD') is not None}")
        print(f"✓ Wallet password configured: {'Yes' if os.getenv('WALLET_PASSWORD') else 'No'}")
        print(f"✓ Drift directory: {'Exists' if os.path.exists(config_dir) else 'Missing'}")
        print("================================\n")

        logger.info(f"Creating subaccount {subaccount_id} for wallet {wallet_name}")
        drift_wallet_manager = DriftWalletManager()

        async def create_account():
            return await drift_wallet_manager.create_subaccount(
                wallet_name=wallet_name,
                subaccount_id=subaccount_id,
                name=name
            )
        
        success = asyncio.run(create_account())
        
        if success:
            logger.info(f"Successfully created subaccount {subaccount_id}")
        else:
            logger.error(f"Failed to create subaccount {subaccount_id}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error creating subaccount: {e}")
        traceback.print_exc()
        sys.exit(1)

@subaccount.command()
@click.argument('wallet_name', required=False)
def list(wallet_name: Optional[str] = None):
    """List all subaccounts for a wallet or all wallets"""
    try:
        # Initialize Drift account manager
        async def run_list():
            manager = DriftAccountManager(wallet_name)
            await manager.setup()  # This will initialize the client
            
            try:
                # List subaccounts
                await manager.list_subaccounts()
            finally:
                # Clean up
                if manager.drift_client:
                    await manager.drift_client.unsubscribe()
        
        asyncio.run(run_list())
            
    except Exception as e:
        logger.error(f"Error listing subaccounts: {e}")
        sys.exit(1)

@subaccount.command(name="info")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
def subaccount_info(wallet_name, subaccount_id):
    """Show detailed information for a subaccount"""
    wallet_name = wallet_name.upper()
    
    # Get subaccount config
    config = drift_wallet_manager.get_subaccount_config(wallet_name, subaccount_id)
    if not config:
        print(f"{Colors.RED}Subaccount {subaccount_id} not found for wallet {wallet_name}{Colors.RESET}")
        return
    
    # Print subaccount information
    print(f"\n{Colors.CYAN}=== SUBACCOUNT DETAILS ==={Colors.RESET}")
    print(f"{Colors.BOLD}Wallet:{Colors.RESET} {wallet_name}")
    print(f"{Colors.BOLD}Subaccount ID:{Colors.RESET} {subaccount_id}")
    print(f"{Colors.BOLD}Name:{Colors.RESET} {config.get('name', 'N/A')}")
    print(f"{Colors.BOLD}Network:{Colors.RESET} {config.get('network', 'devnet')}")
    print(f"{Colors.BOLD}Created:{Colors.RESET} {config.get('created_at', 'Unknown')}")
    print(f"{Colors.BOLD}Status:{Colors.RESET} {config.get('status', 'Unknown')}")
    print(f"{Colors.BOLD}Authority:{Colors.RESET} {config.get('authority', 'Unknown')}")
    
    # Get additional details if needed
    if 'last_updated' in config:
        print(f"{Colors.BOLD}Last Updated:{Colors.RESET} {config['last_updated']}")

@subaccount.command(name="delete")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def delete_subaccount(wallet_name, subaccount_id, force):
    """Delete a subaccount configuration (does not close on-chain)"""
    wallet_name = wallet_name.upper()
    
    # Get subaccount config
    config = drift_wallet_manager.get_subaccount_config(wallet_name, subaccount_id)
    if not config:
        print(f"{Colors.RED}Subaccount {subaccount_id} not found for wallet {wallet_name}{Colors.RESET}")
        return
    
    # Request confirmation
    if not force:
        print(f"\n{Colors.YELLOW}WARNING: This will delete the local configuration for subaccount {subaccount_id} of wallet {wallet_name}.{Colors.RESET}")
        print(f"{Colors.YELLOW}This operation does NOT close the subaccount on-chain.{Colors.RESET}")
        if not click.confirm("Are you sure you want to continue?"):
            print("Operation cancelled")
            return
    
    # Delete subaccount
    result = drift_wallet_manager.delete_subaccount_config(wallet_name, subaccount_id)
    
    if result:
        print(f"{Colors.GREEN}✓ Successfully deleted subaccount configuration{Colors.RESET}")
    else:
        print(f"{Colors.RED}Failed to delete subaccount configuration{Colors.RESET}")

@subaccount.command()
@click.argument('wallet_name')
@click.argument('subaccount_id', type=int)
def switch(wallet_name: str, subaccount_id: int):
    """Switch to an existing subaccount"""
    try:
        asyncio.run(_switch(wallet_name, subaccount_id))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

async def _switch(wallet_name: str, subaccount_id: int):
    manager = DriftWalletManager()
    success = await manager.switch_subaccount(wallet_name, subaccount_id)
    if success:
        click.echo(f"Successfully switched to subaccount {subaccount_id}")
    else:
        click.echo(f"Failed to switch to subaccount {subaccount_id}")

@cli.group()
def account():
    """Manage Drift account balances and operations"""
    pass

@account.command(name="balance")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
def check_balance(wallet_name, subaccount_id):
    """Check balance for a specific subaccount"""
    wallet_name = wallet_name.upper()
    
    # Check balance (async)
    async def run_balance_check():
        # Initialize Drift account manager
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        # Check balances
        try:
            await manager.show_balances()
        finally:
            # Clean up
            if manager.drift_client:
                await manager.drift_client.unsubscribe()
    
    asyncio.run(run_balance_check())

@account.command(name="deposit")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
@click.argument('amount', type=float, required=True)
@click.option('--token', '-t', default="SOL", help='Token to deposit (default: SOL)')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def deposit(wallet_name, subaccount_id, amount, token, force):
    """Deposit tokens into a Drift subaccount"""
    wallet_name = wallet_name.upper()
    
    # Get subaccount config
    config = drift_wallet_manager.get_subaccount_config(wallet_name, subaccount_id)
    if not config:
        print(f"{Colors.RED}Subaccount {subaccount_id} not found for wallet {wallet_name}{Colors.RESET}")
        return
    
    # Request confirmation
    if not force:
        print(f"\n{Colors.YELLOW}Depositing {amount} {token} into subaccount {subaccount_id} of wallet {wallet_name}{Colors.RESET}")
        if not click.confirm("Continue?"):
            print("Operation cancelled")
            return
    
    # Deposit tokens (async)
    async def run_deposit():
        # Initialize Drift account manager
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        try:
            # Show current balance
            await manager.show_balances()
            
            # Deposit tokens
            if token.upper() == "SOL":
                tx_sig = await manager.deposit_sol(amount)
                if tx_sig:
                    print(f"{Colors.GREEN}✓ Deposit successful! Transaction: {tx_sig}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Deposit failed{Colors.RESET}")
            else:
                print(f"{Colors.RED}Token {token} deposits not implemented yet{Colors.RESET}")
            
            # Show updated balance
            await manager.show_balances()
            
        finally:
            # Clean up
            if manager.drift_client:
                await manager.drift_client.unsubscribe()
    
    asyncio.run(run_deposit())

@account.command(name="withdraw")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
@click.argument('amount', type=float, required=True)
@click.option('--token', '-t', default="SOL", help='Token to withdraw (default: SOL)')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def withdraw(wallet_name, subaccount_id, amount, token, force):
    """Withdraw tokens from a Drift subaccount"""
    wallet_name = wallet_name.upper()
    
    # Get subaccount config
    config = drift_wallet_manager.get_subaccount_config(wallet_name, subaccount_id)
    if not config:
        print(f"{Colors.RED}Subaccount {subaccount_id} not found for wallet {wallet_name}{Colors.RESET}")
        return
    
    # Request confirmation
    if not force:
        print(f"\n{Colors.YELLOW}Withdrawing {amount} {token} from subaccount {subaccount_id} of wallet {wallet_name}{Colors.RESET}")
        if not click.confirm("Continue?"):
            print("Operation cancelled")
            return
    
    # Withdraw tokens (async)
    async def run_withdraw():
        # Initialize Drift account manager
        manager = DriftAccountManager(wallet_name)
        await manager.setup(subaccount_id)
        
        try:
            # Show current balance
            await manager.show_balances()
            
            # Withdraw tokens
            if token.upper() == "SOL":
                tx_sig = await manager.withdraw_sol(amount)
                if tx_sig:
                    print(f"{Colors.GREEN}✓ Withdrawal successful! Transaction: {tx_sig}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Withdrawal failed{Colors.RESET}")
            else:
                print(f"{Colors.RED}Token {token} withdrawals not implemented yet{Colors.RESET}")
            
            # Show updated balance
            await manager.show_balances()
            
        finally:
            # Clean up
            if manager.drift_client:
                await manager.drift_client.unsubscribe()
    
    asyncio.run(run_withdraw())

@account.command(name="collateral")
@click.argument('wallet_name', required=True)
@click.argument('subaccount_id', type=int, required=True)
def check_collateral(wallet_name, subaccount_id):
    """Check detailed collateral information for a subaccount"""
    wallet_name = wallet_name.upper()
    
    # Check balance (async)
    async def run_collateral_check():
        try:
            # Use global wallet_manager
            wallet = wallet_manager.get_wallet(wallet_name)
            if not wallet:
                print(f"{Colors.RED}Wallet '{wallet_name}' not found{Colors.RESET}")
                return
                
            # Log public key
            print(f"Using wallet with public key: {wallet.get_public_key()}")
            
            # Get network and RPC client
            network = get_network()
            connection = await get_solana_client(network)
            print(f"Connected to {network}")
            
            # Convert SolanaWallet to anchorpy Wallet
            if isinstance(wallet.keypair, bytes):
                keypair = Keypair.from_bytes(wallet.keypair)
            else:
                keypair = wallet.keypair
            anchor_wallet = Wallet(keypair)
            
            # Initialize Drift client with compute units
            tx_params = TxParams(
                compute_units=700_000,
                compute_units_price=10_000
            )
            
            drift_client = DriftClient(
                connection,
                anchor_wallet,
                network,
                tx_params=tx_params,
                account_subscription=AccountSubscriptionConfig("cached"),
                sub_account_ids=[subaccount_id]  # Only check the specified subaccount
            )
            
            # Subscribe to get updates
            await drift_client.subscribe()
            print("Subscribed to Drift client")
            
            try:
                # Get user account
                drift_user = drift_client.get_user()
                if not drift_user:
                    print(f"{Colors.RED}No user account found{Colors.RESET}")
                    return
                    
                user = drift_user.get_user_account()
                if not user:
                    print(f"{Colors.RED}No user account data found{Colors.RESET}")
                    return
                    
                # Log spot positions
                print(f"\n{Colors.CYAN}=== SPOT POSITIONS ==={Colors.RESET}")
                for spot_position in user.spot_positions:
                    if spot_position.scaled_balance != 0:
                        # Get market info
                        market = await get_spot_market_account(
                            drift_client.program,
                            spot_position.market_index
                        )
                        
                        # Calculate token amount and value
                        token_amount = spot_position.scaled_balance / (10 ** market.decimals)
                        token_value = token_amount * market.historical_oracle_data.last_oracle_price / 1e6
                        
                        # Get market name
                        market_name = bytes(market.name).decode('utf-8').strip('\x00')
                        
                        print(f"\n{Colors.BOLD}Market:{Colors.RESET} {market_name}")
                        print(f"{Colors.BOLD}Token Amount:{Colors.RESET} {token_amount:.6f}")
                        print(f"{Colors.BOLD}Token Price:{Colors.RESET} ${market.historical_oracle_data.last_oracle_price / 1e6:.2f}")
                        print(f"{Colors.BOLD}Position Value:{Colors.RESET} ${token_value:.2f}")
                        
                # Log perp positions
                print(f"\n{Colors.CYAN}=== PERP POSITIONS ==={Colors.RESET}")
                for perp_position in user.perp_positions:
                    if perp_position.base_asset_amount != 0:
                        # Get market info
                        market = await get_perp_market_account(
                            drift_client.program,
                            perp_position.market_index
                        )
                        
                        # Calculate position size and value
                        position_size = perp_position.base_asset_amount / 1e9
                        position_value = position_size * market.amm.historical_oracle_data.last_oracle_price / 1e6
                        
                        # Get market name
                        market_name = bytes(market.name).decode('utf-8').strip('\x00')
                        
                        print(f"\n{Colors.BOLD}Market:{Colors.RESET} {market_name}")
                        print(f"{Colors.BOLD}Position Size:{Colors.RESET} {position_size:.6f}")
                        print(f"{Colors.BOLD}Entry Price:{Colors.RESET} ${perp_position.get_entry_price() / 1e6:.2f}")
                        print(f"{Colors.BOLD}Current Price:{Colors.RESET} ${market.amm.historical_oracle_data.last_oracle_price / 1e6:.2f}")
                        print(f"{Colors.BOLD}Position Value:{Colors.RESET} ${position_value:.2f}")
                        print(f"{Colors.BOLD}Unrealized PnL:{Colors.RESET} ${perp_position.get_unrealized_pnl(market) / 1e6:.2f}")
                        
                # Log collateral info
                print(f"\n{Colors.CYAN}=== COLLATERAL INFO ==={Colors.RESET}")
                total_collateral = drift_user.get_total_collateral()
                print(f"{Colors.BOLD}Total Collateral:{Colors.RESET} ${total_collateral / 1e6:.2f}")
                
                # Try to get additional risk metrics
                try:
                    free_collateral = drift_user.get_free_collateral()
                    print(f"{Colors.BOLD}Free Collateral:{Colors.RESET} ${free_collateral / 1e6:.2f}")
                    
                    margin_requirement = drift_user.get_margin_requirement()
                    print(f"{Colors.BOLD}Margin Requirement:{Colors.RESET} ${margin_requirement / 1e6:.2f}")
                    
                    leverage = drift_user.get_leverage()
                    print(f"{Colors.BOLD}Current Leverage:{Colors.RESET} {leverage}x")
                except Exception as e:
                    print(f"{Colors.RED}Error getting risk metrics: {e}{Colors.RESET}")
                    
            finally:
                # Clean up
                await drift_client.unsubscribe()
                
        except Exception as e:
            print(f"{Colors.RED}Error checking collateral: {e}{Colors.RESET}")
            import traceback
            print(f"{Colors.RED}Traceback: {traceback.format_exc()}{Colors.RESET}")
    
    asyncio.run(run_collateral_check())

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 