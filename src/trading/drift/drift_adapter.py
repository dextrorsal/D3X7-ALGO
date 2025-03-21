"""
Enhanced Drift DEX adapter for live trading
Implements comprehensive functionality for Drift protocol interaction
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json
import base64
import os
from pathlib import Path
import argparse
from tabulate import tabulate

from anchorpy.provider import Wallet
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from driftpy.drift_client import DriftClient
from driftpy.accounts.get_accounts import get_protected_maker_mode_stats
from driftpy.math.user_status import is_user_protected_maker
from driftpy.types import TxParams, OrderParams, OrderType, MarketType, PositionDirection
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION, MARGIN_PRECISION
from driftpy.decode.utils import decode_name
from driftpy.constants.spot_markets import devnet_spot_market_configs

from src.utils.wallet.sol_rpc import get_solana_client, get_network, NETWORK_URLS
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.encryption import WalletEncryption
from src.trading.security.security_manager import SecurityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
WSOL_MINT = Pubkey.from_string("So11111111111111111111111111111111111111112")
WSOL_ACCOUNT_RENT = 2039280  # lamports (≈0.00203928 SOL)
DRIFT_SUBACCOUNT_FEE = 35000000  # lamports (≈0.035 SOL)

class DriftAdapter:
    """
    Enhanced Drift DEX adapter
    Handles all Drift protocol interactions including trading, account management, and security
    """
    
    def __init__(self):
        # Load and validate environment variables
        self.rpc_endpoint = os.getenv('MAINNET_RPC_ENDPOINT')
        if not self.rpc_endpoint:
            raise EnvironmentError("MAINNET_RPC_ENDPOINT environment variable not set")
        
        # Initialize components
        self.wallet_manager = WalletManager()
        self.solana_client = None
        self.drift_client = None
        
        # Default transaction parameters for mainnet
        self.tx_params = TxParams(
            compute_units_price=85_000,
            compute_units=1_400_000
        )
        
        logger.info("DriftAdapter initialized for mainnet")
        
        # Market configurations
        self.markets = {
            "SOL-PERP": {
                "market_index": 0,
                "base_decimals": 9,
                "quote_decimals": 6
            },
            "BTC-PERP": {
                "market_index": 1,
                "base_decimals": 8,
                "quote_decimals": 6
            },
            "ETH-PERP": {
                "market_index": 2,
                "base_decimals": 8,
                "quote_decimals": 6
            }
        }
        
        self.spot_markets = {
            "SOL-USDC": {
                "market_index": 0,
                "base_decimals": 9,
                "quote_decimals": 6
            },
            "BTC-USDC": {
                "market_index": 1,
                "base_decimals": 8,
                "quote_decimals": 6
            },
            "ETH-USDC": {
                "market_index": 2,
                "base_decimals": 8,
                "quote_decimals": 6
            }
        }
    
    async def connect(self) -> None:
        """Initialize Solana client connection"""
        try:
            self.solana_client = await get_solana_client("mainnet")
            version = await self.solana_client.get_version()
            logger.info(f"Connected to mainnet RPC (version {version.version})")
        except Exception as e:
            logger.error(f"Failed to connect to mainnet: {str(e)}")
            raise
    
    async def initialize(self, 
                        wallet_name: str = "MAIN",
                        tx_params: Optional[TxParams] = None) -> bool:
        """
        Initialize Drift client with enhanced security and wallet management
        
        Args:
            wallet_name: Name of the wallet to use
            tx_params: Optional transaction parameters
            
        Returns:
            True if initialization successful
        """
        try:
            # Get network configuration
            network = get_network()
            logger.info(f"Using network: {network}")
            
            # Get wallet from WalletManager
            wallet = self.wallet_manager.get_wallet(wallet_name)
            if not wallet:
                raise ValueError(f"Wallet '{wallet_name}' not found")
            
            # Load keypair
            if hasattr(wallet, 'keypair') and wallet.keypair:
                if isinstance(wallet.keypair, bytes):
                    self.wallet = Keypair.from_bytes(wallet.keypair)
                else:
                    self.wallet = wallet.keypair
            else:
                raise Exception(f"No keypair available in wallet {wallet_name}")
            
            # Security audit
            audit_results = self.security_manager.perform_security_audit()
            for check in audit_results["checks"]:
                if check["status"] == "FAIL":
                    logger.error(f"Security check failed: {check['name']} - {check['details']}")
                    raise SecurityError(f"Security check failed: {check['name']}")
            
            # Initialize Solana client
            connection = await get_solana_client()
            
            # Set default tx_params if not provided
            if tx_params is None:
                tx_params = TxParams(
                    compute_units=700_000,
                    compute_units_price=10_000
                )
            
            # Initialize Drift client
            self.drift_client = DriftClient(
                connection=connection,
                wallet=Wallet(self.wallet),
                env=network,
                tx_params=tx_params
            )
            
            # Subscribe to updates
            await self.drift_client.subscribe()
            
            # Initialize subaccounts
            await self._initialize_subaccounts()
            
            # Check protected maker status
            await self._check_protected_maker_status()
            
            self.connected = True
            logger.info(f"Drift adapter initialized successfully on {network}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Drift adapter: {str(e)}")
            self.connected = False
            return False
    
    async def _initialize_subaccounts(self):
        """Initialize and verify subaccounts"""
        for subaccount_id in range(5):  # 0,1,2,3,4
            try:
                # Initialize user account if needed
                tx_sig = await self.drift_client.initialize_user(
                    sub_account_id=subaccount_id,
                    name=f"Subaccount {subaccount_id}"
                )
                logger.info(f"Initialized subaccount {subaccount_id}")
            except Exception as e:
                if "already in use" in str(e):
                    logger.info(f"Subaccount {subaccount_id} already exists")
                else:
                    logger.error(f"Error initializing subaccount {subaccount_id}: {str(e)}")
                    continue
            
            # Add user to client
            try:
                await self.drift_client.add_user(subaccount_id)
                logger.info(f"Added subaccount {subaccount_id} to client")
            except Exception as e:
                logger.error(f"Error adding subaccount {subaccount_id} to client: {str(e)}")
    
    async def _check_protected_maker_status(self):
        """Check and optionally enable protected maker status"""
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
        
        user = self.drift_client.get_user()
        is_protected = is_user_protected_maker(user.get_user_account())
        
        if not is_protected:
            logger.warning("User is not a protected maker")
            stats = await get_protected_maker_mode_stats(self.drift_client.program)
            
            if stats["current_users"] >= stats["max_users"]:
                logger.warning("No room for new protected makers")
                return
            
            try:
                result = await self.drift_client.update_user_protected_maker_orders(0, True)
                logger.info("Successfully enabled protected maker mode")
            except Exception as e:
                logger.error(f"Failed to enable protected maker mode: {str(e)}")
    
    async def list_subaccounts(self) -> List[Dict[str, Any]]:
        """List all subaccounts for the current wallet"""
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
        
        try:
            found_accounts = []
            for subaccount_id in range(5):
                try:
                    user = self.drift_client.get_user(sub_account_id=subaccount_id)
                    if not user:
                        continue
                    
                    user_account = user.get_user_account()
                    if not user_account:
                        continue
                    
                    # Get token amounts
                    token_amounts = {}
                    for market_index in range(5):
                        try:
                            token_amount = user.get_token_amount(market_index)
                            if token_amount != 0:
                                token_amounts[market_index] = {
                                    'amount': token_amount,
                                    'type': 'deposit' if token_amount > 0 else 'borrow'
                                }
                        except Exception as e:
                            logger.debug(f"Error getting token amount for market {market_index}: {str(e)}")
                            continue
                    
                    found_account = {
                        "subaccount_id": subaccount_id,
                        "name": decode_name(user_account.name) if user_account.name else f"Subaccount {subaccount_id}",
                        "authority": str(user_account.authority),
                        "status": "active",
                        "token_amounts": token_amounts
                    }
                    found_accounts.append(found_account)
                    
                except Exception as e:
                    logger.debug(f"Error checking subaccount {subaccount_id}: {str(e)}")
                    continue
            
            return found_accounts
            
        except Exception as e:
            logger.error(f"Error listing subaccounts: {str(e)}")
            return []
    
    async def get_account_info(self, subaccount_id: int = 0) -> Dict[str, Any]:
        """
        Get detailed account information including balances and PnL
        
        Args:
            subaccount_id: Subaccount ID to check
            
        Returns:
            Dictionary containing account details
        """
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
        
        try:
            drift_user = self.drift_client.get_user(sub_account_id=subaccount_id)
            user = drift_user.get_user_account()
            
            # Get collateral info
            spot_collateral = drift_user.get_spot_market_asset_value(
                None,
                include_open_orders=True
            )
            
            # Get PnL
            unrealized_pnl = drift_user.get_unrealized_pnl(False)
            
            # Get total collateral
            total_collateral = drift_user.get_total_collateral()
            
            # Get spot positions
            spot_positions = []
            for position in user.spot_positions:
                if position.scaled_balance != 0:
                    market = self.drift_client.get_spot_market_account(position.market_index)
                    token_amount = position.scaled_balance / (10 ** market.decimals)
                    spot_positions.append({
                        "market_index": position.market_index,
                        "balance": token_amount
                    })
            
            return {
                "name": decode_name(user.name),
                "authority": str(user.authority),
                "spot_collateral": spot_collateral / QUOTE_PRECISION,
                "unrealized_pnl": unrealized_pnl / QUOTE_PRECISION,
                "total_collateral": total_collateral / QUOTE_PRECISION,
                "spot_positions": spot_positions
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            raise
    
    async def get_market_price(self, market: str) -> float:
        """Get current market price"""
        if not self.connected:
            await self.initialize()
        
        try:
            market_config = None
            if market in self.markets:
                market_config = self.markets[market]
                market_type = "perp"
            elif market in self.spot_markets:
                market_config = self.spot_markets[market]
                market_type = "spot"
            else:
                raise ValueError(f"Unknown market: {market}")
            
            market_index = market_config["market_index"]
            
            if market_type == "perp":
                price_data = await self.drift_client.get_perp_market_price(market_index)
            else:
                price_data = await self.drift_client.get_spot_market_price(market_index)
            
            return float(price_data.price) / QUOTE_PRECISION
            
        except Exception as e:
            logger.error(f"Error getting price for {market}: {e}")
            raise
    
    async def place_order(self,
                         market: str,
                         side: str,
                         size: float,
                         price: Optional[float] = None,
                         order_type: str = "market",
                         reduce_only: bool = False,
                         post_only: bool = False,
                         subaccount_id: int = 0) -> Dict:
        """
        Place an order (spot or perp)
        
        Args:
            market: Market symbol
            side: "buy" or "sell"
            size: Order size
            price: Limit price (optional)
            order_type: "market" or "limit"
            reduce_only: Whether order should only reduce position
            post_only: Whether order must be maker
            subaccount_id: Subaccount to use
            
        Returns:
            Order details
        """
        if not self.connected:
            await self.initialize()
        
        try:
            # Determine market type and config
            market_config = None
            if market in self.markets:
                market_config = self.markets[market]
                market_type = MarketType.PERP
            elif market in self.spot_markets:
                market_config = self.spot_markets[market]
                market_type = MarketType.SPOT
            else:
                raise ValueError(f"Unknown market: {market}")
            
            # Create order parameters
            order_params = OrderParams(
                market_index=market_config["market_index"],
                market_type=market_type,
                direction=PositionDirection.LONG if side.lower() == "buy" else PositionDirection.SHORT,
                base_asset_amount=int(size * BASE_PRECISION),
                price=int(price * QUOTE_PRECISION) if price else None,
                order_type=OrderType.LIMIT if order_type.lower() == "limit" else OrderType.MARKET,
                reduce_only=reduce_only,
                post_only=post_only
            )
            
            # Place order
            tx_sig = await self.drift_client.place_order(
                order_params,
                sub_account_id=subaccount_id
            )
            
            return {
                "transaction": str(tx_sig),
                "market": market,
                "side": side,
                "size": size,
                "price": price,
                "type": order_type,
                "subaccount": subaccount_id
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise
    
    async def cleanup(self):
        """Clean up resources and unsubscribe"""
        if self.drift_client:
            try:
                await self.drift_client.unsubscribe()
                logger.info("Successfully unsubscribed from Drift")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
    
    async def get_risk_metrics(self, subaccount_id: int = 0) -> Dict[str, Any]:
        """
        Get comprehensive risk metrics including positions and collateral details
        
        Args:
            subaccount_id: Subaccount ID to check
            
        Returns:
            Dictionary containing detailed risk metrics
        """
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
            
        try:
            drift_user = self.drift_client.get_user(sub_account_id=subaccount_id)
            if not drift_user:
                raise ValueError(f"No user found for subaccount {subaccount_id}")
                
            user = drift_user.get_user_account()
            
            # Initialize results dictionary
            risk_metrics = {
                "spot_positions": [],
                "perp_positions": [],
                "collateral": {},
                "risk_metrics": {}
            }
            
            # Get spot positions
            for spot_position in user.spot_positions:
                if spot_position.scaled_balance != 0:
                    market = await get_spot_market_account(
                        self.drift_client.program,
                        spot_position.market_index
                    )
                    
                    token_amount = spot_position.scaled_balance / (10 ** market.decimals)
                    token_value = token_amount * market.historical_oracle_data.last_oracle_price / 1e6
                    
                    risk_metrics["spot_positions"].append({
                        "market": market.name,
                        "amount": token_amount,
                        "price": market.historical_oracle_data.last_oracle_price / 1e6,
                        "value": token_value
                    })
            
            # Get perp positions
            for perp_position in user.perp_positions:
                if perp_position.base_asset_amount != 0:
                    market = await get_perp_market_account(
                        self.drift_client.program,
                        perp_position.market_index
                    )
                    
                    position_size = perp_position.base_asset_amount / 1e9
                    position_value = position_size * market.amm.historical_oracle_data.last_oracle_price / 1e6
                    
                    risk_metrics["perp_positions"].append({
                        "market": market.name,
                        "size": position_size,
                        "entry_price": perp_position.get_entry_price() / 1e6,
                        "current_price": market.amm.historical_oracle_data.last_oracle_price / 1e6,
                        "value": position_value,
                        "unrealized_pnl": perp_position.get_unrealized_pnl(market) / 1e6
                    })
            
            # Get collateral info
            total_collateral = drift_user.get_total_collateral()
            risk_metrics["collateral"]["total"] = total_collateral / 1e6
            
            try:
                # Get additional risk metrics
                free_collateral = drift_user.get_free_collateral()
                margin_requirement = drift_user.get_margin_requirement()
                leverage = drift_user.get_leverage()
                
                risk_metrics["risk_metrics"].update({
                    "free_collateral": free_collateral / 1e6,
                    "margin_requirement": margin_requirement / 1e6,
                    "leverage": leverage,
                    "utilization": (margin_requirement / total_collateral) if total_collateral > 0 else 0
                })
            except Exception as e:
                logger.warning(f"Could not calculate some risk metrics: {str(e)}")
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {str(e)}")
            raise

    async def get_native_balance(self, wallet_name: str) -> float:
        """Get native SOL balance for a wallet"""
        wallet = self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            raise ValueError(f"Wallet '{wallet_name}' not found")
            
        try:
            client = await get_solana_client()
            balance = await client.get_balance(wallet.public_key)
            return balance.value / 1e9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Error getting native balance: {str(e)}")
            raise

    async def list_wallets(self) -> List[Dict[str, Any]]:
        """List all available wallets with their details"""
        try:
            wallets = self.wallet_manager.list_wallets()
            wallet_info = []
            
            for wallet_name in wallets:
                wallet = self.wallet_manager.get_wallet(wallet_name)
                if wallet:
                    info = {
                        "name": wallet_name,
                        "public_key": str(wallet.public_key),
                        "is_current": (self.wallet_manager.current_wallet and 
                                     self.wallet_manager.current_wallet.name == wallet_name)
                    }
                    wallet_info.append(info)
            
            return wallet_info
        except Exception as e:
            logger.error(f"Error listing wallets: {str(e)}")
            raise

    async def create_subaccount(self, wallet_name: str, subaccount_id: int, name: str = None) -> bool:
        """Create a new subaccount for the given wallet"""
        if not self.connected:
            await self.initialize(wallet_name)
            
        try:
            # Initialize user account
            tx_sig = await self.drift_client.initialize_user(
                sub_account_id=subaccount_id,
                name=name if name else f"Subaccount {subaccount_id}"
            )
            logger.info(f"Created subaccount {subaccount_id} for wallet {wallet_name}")
            
            # Add user to client
            await self.drift_client.add_user(subaccount_id)
            
            return True
        except Exception as e:
            if "already in use" in str(e):
                logger.info(f"Subaccount {subaccount_id} already exists")
                return True
            logger.error(f"Error creating subaccount: {str(e)}")
            return False

    async def delete_subaccount(self, wallet_name: str, subaccount_id: int) -> bool:
        """Delete a subaccount (closes positions and withdraws funds)"""
        if not self.connected:
            await self.initialize(wallet_name)
            
        try:
            # Get account info to check positions and balances
            info = await self.get_account_info(subaccount_id)
            
            # Close any open positions
            if info["spot_positions"]:
                logger.warning("Cannot delete subaccount with open spot positions")
                return False
                
            # Withdraw any remaining collateral
            if info["total_collateral"] > 0:
                logger.warning("Cannot delete subaccount with remaining collateral")
                return False
            
            # Close the subaccount
            tx_sig = await self.drift_client.close_user(subaccount_id)
            logger.info(f"Deleted subaccount {subaccount_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting subaccount: {str(e)}")
            return False

    async def deposit(self, wallet_name: str, subaccount_id: int, 
                     amount: float, token: str = "SOL") -> bool:
        """Deposit funds into a subaccount"""
        if not self.connected:
            await self.initialize(wallet_name)
            
        try:
            # Convert amount to native units
            if token == "SOL":
                native_amount = int(amount * 1e9)  # Convert to lamports
                market_index = 0  # SOL market index
            else:
                raise ValueError(f"Unsupported token: {token}")
            
            # Perform deposit
            tx_sig = await self.drift_client.deposit(
                amount=native_amount,
                spot_market_index=market_index,
                sub_account_id=subaccount_id
            )
            
            logger.info(f"Deposited {amount} {token} into subaccount {subaccount_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error depositing funds: {str(e)}")
            return False

    async def withdraw(self, wallet_name: str, subaccount_id: int,
                      amount: float, token: str = "SOL") -> bool:
        """Withdraw funds from a subaccount"""
        if not self.connected:
            await self.initialize(wallet_name)
            
        try:
            # Convert amount to native units
            if token == "SOL":
                native_amount = int(amount * 1e9)  # Convert to lamports
                market_index = 0  # SOL market index
            else:
                raise ValueError(f"Unsupported token: {token}")
            
            # Perform withdrawal
            tx_sig = await self.drift_client.withdraw(
                amount=native_amount,
                spot_market_index=market_index,
                sub_account_id=subaccount_id
            )
            
            logger.info(f"Withdrew {amount} {token} from subaccount {subaccount_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error withdrawing funds: {str(e)}")
            return False

class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass

async def main():
    """CLI interface for Drift adapter"""
    parser = argparse.ArgumentParser(description="Drift Adapter CLI")
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')
    
    # Wallet commands
    wallet_parser = subparsers.add_parser('wallet', help='Wallet management commands')
    wallet_subparsers = wallet_parser.add_subparsers(dest='wallet_action')
    
    # List wallets
    wallet_subparsers.add_parser('list', help='List all wallets')
    
    # Check wallet balance
    balance_parser = wallet_subparsers.add_parser('balance', help='Check wallet balance')
    balance_parser.add_argument('wallet_name', help='Name of the wallet')
    
    # Subaccount commands
    subaccount_parser = subparsers.add_parser('subaccount', help='Subaccount management commands')
    subaccount_subparsers = subaccount_parser.add_subparsers(dest='subaccount_action')
    
    # Create subaccount
    create_parser = subaccount_subparsers.add_parser('create', help='Create a new subaccount')
    create_parser.add_argument('wallet_name', help='Name of the wallet')
    create_parser.add_argument('subaccount_id', type=int, help='Subaccount ID (0-255)')
    create_parser.add_argument('--name', help='Name for the subaccount')
    
    # List subaccounts
    list_parser = subaccount_subparsers.add_parser('list', help='List all subaccounts')
    list_parser.add_argument('--wallet', help='Filter by wallet name')
    
    # Delete subaccount
    delete_parser = subaccount_subparsers.add_parser('delete', help='Delete a subaccount')
    delete_parser.add_argument('wallet_name', help='Name of the wallet')
    delete_parser.add_argument('subaccount_id', type=int, help='Subaccount ID to delete')
    delete_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    # Account operations
    account_parser = subparsers.add_parser('account', help='Account operations')
    account_subparsers = account_parser.add_subparsers(dest='account_action')
    
    # Deposit
    deposit_parser = account_subparsers.add_parser('deposit', help='Deposit funds')
    deposit_parser.add_argument('wallet_name', help='Name of the wallet')
    deposit_parser.add_argument('subaccount_id', type=int, help='Subaccount ID')
    deposit_parser.add_argument('amount', type=float, help='Amount to deposit')
    deposit_parser.add_argument('--token', '-t', default='SOL', help='Token to deposit (default: SOL)')
    
    # Withdraw
    withdraw_parser = account_subparsers.add_parser('withdraw', help='Withdraw funds')
    withdraw_parser.add_argument('wallet_name', help='Name of the wallet')
    withdraw_parser.add_argument('subaccount_id', type=int, help='Subaccount ID')
    withdraw_parser.add_argument('amount', type=float, help='Amount to withdraw')
    withdraw_parser.add_argument('--token', '-t', default='SOL', help='Token to withdraw (default: SOL)')
    
    # Existing commands
    list_all_parser = subparsers.add_parser('list-subaccounts', help='List all subaccounts')
    
    account_info_parser = subparsers.add_parser('account-info', help='Get account information')
    account_info_parser.add_argument('-s', '--subaccount', type=int, default=0, help='Subaccount ID')
    
    price_parser = subparsers.add_parser('price', help='Get market price')
    price_parser.add_argument('market', help='Market symbol (e.g., SOL-PERP)')
    
    risk_parser = subparsers.add_parser('risk', help='Get detailed risk metrics')
    risk_parser.add_argument('-s', '--subaccount', type=int, default=0, help='Subaccount ID')
    
    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        return
    
    adapter = DriftAdapter()
    try:
        # Handle wallet commands
        if args.action == 'wallet':
            if args.wallet_action == 'list':
                wallets = await adapter.list_wallets()
                print("\n=== AVAILABLE WALLETS ===")
                wallet_data = [[w['name'], w['public_key'], "Active" if w['is_current'] else ""] 
                             for w in wallets]
                print(tabulate(wallet_data, headers=['Name', 'Public Key', 'Status'], 
                             tablefmt='simple'))
                
            elif args.wallet_action == 'balance':
                balance = await adapter.get_native_balance(args.wallet_name)
                print(f"\n=== NATIVE SOL BALANCE ===")
                print(f"Wallet: {args.wallet_name}")
                print(f"Balance: {balance:.9f} SOL")
        
        # Handle subaccount commands
        elif args.action == 'subaccount':
            if args.subaccount_action == 'create':
                success = await adapter.create_subaccount(
                    args.wallet_name, 
                    args.subaccount_id,
                    args.name
                )
                if success:
                    print(f"Successfully created subaccount {args.subaccount_id}")
                else:
                    print("Failed to create subaccount")
                    
            elif args.subaccount_action == 'list':
                await adapter.initialize(args.wallet if args.wallet else "MAIN")
                accounts = await adapter.list_subaccounts()
                print("\n=== SUBACCOUNTS ===")
                for account in accounts:
                    print(f"\nSubaccount {account['subaccount_id']}")
                    print(f"Name: {account['name']}")
                    print(f"Authority: {account['authority']}")
                    if account['token_amounts']:
                        print("Token Amounts:")
                        for market_index, details in account['token_amounts'].items():
                            print(f"  Market {market_index}: {details['amount']} ({details['type']})")
                            
            elif args.subaccount_action == 'delete':
                if not args.force:
                    confirm = input(f"Are you sure you want to delete subaccount {args.subaccount_id}? [y/N] ")
                    if confirm.lower() != 'y':
                        print("Operation cancelled")
                        return
                
                success = await adapter.delete_subaccount(args.wallet_name, args.subaccount_id)
                if success:
                    print(f"Successfully deleted subaccount {args.subaccount_id}")
                else:
                    print("Failed to delete subaccount")
        
        # Handle account operations
        elif args.action == 'account':
            if args.account_action == 'deposit':
                success = await adapter.deposit(
                    args.wallet_name,
                    args.subaccount_id,
                    args.amount,
                    args.token
                )
                if success:
                    print(f"Successfully deposited {args.amount} {args.token}")
                else:
                    print("Failed to deposit funds")
                    
            elif args.account_action == 'withdraw':
                success = await adapter.withdraw(
                    args.wallet_name,
                    args.subaccount_id,
                    args.amount,
                    args.token
                )
                if success:
                    print(f"Successfully withdrew {args.amount} {args.token}")
                else:
                    print("Failed to withdraw funds")
        
        # Handle existing commands
        elif args.action == 'list-subaccounts':
            accounts = await adapter.list_subaccounts()
            print(json.dumps(accounts, indent=2))
            
        elif args.action == 'account-info':
            info = await adapter.get_account_info(args.subaccount)
            print(json.dumps(info, indent=2))
            
        elif args.action == 'price':
            price = await adapter.get_market_price(args.market)
            print(f"{args.market} price: ${price:,.2f}")
            
        elif args.action == 'risk':
            metrics = await adapter.get_risk_metrics(args.subaccount)
            
            print("\n=== SPOT POSITIONS ===")
            for pos in metrics["spot_positions"]:
                print(f"\nMarket: {pos['market']}")
                print(f"Amount: {pos['amount']:.6f}")
                print(f"Price: ${pos['price']:.2f}")
                print(f"Value: ${pos['value']:.2f}")
            
            print("\n=== PERP POSITIONS ===")
            for pos in metrics["perp_positions"]:
                print(f"\nMarket: {pos['market']}")
                print(f"Size: {pos['size']:.6f}")
                print(f"Entry Price: ${pos['entry_price']:.2f}")
                print(f"Current Price: ${pos['current_price']:.2f}")
                print(f"Position Value: ${pos['value']:.2f}")
                print(f"Unrealized PnL: ${pos['unrealized_pnl']:.2f}")
            
            print("\n=== COLLATERAL & RISK METRICS ===")
            print(f"Total Collateral: ${metrics['collateral']['total']:.2f}")
            if "risk_metrics" in metrics:
                print(f"Free Collateral: ${metrics['risk_metrics'].get('free_collateral', 'N/A')}")
                print(f"Margin Requirement: ${metrics['risk_metrics'].get('margin_requirement', 'N/A')}")
                print(f"Current Leverage: {metrics['risk_metrics'].get('leverage', 'N/A')}x")
                print(f"Collateral Utilization: {metrics['risk_metrics'].get('utilization', 'N/A')*100:.1f}%")
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in Drift adapter: {str(e)}")
        raise
    finally:
        await adapter.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise