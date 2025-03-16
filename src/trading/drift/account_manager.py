#!/usr/bin/env python3
"""
Drift account management module.
Handles deposits, withdrawals, balance checking, and PnL tracking.
"""

import asyncio
import logging
import argparse
from typing import Optional, Dict
from decimal import Decimal

from ..devnet.drift_auth import DriftHelper
from driftpy.constants.spot_markets import devnet_spot_market_configs
from driftpy.types import (
    OrderParams,
    OrderType,
    MarketType,
    PositionDirection,
    TxParams
)
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION, MARGIN_PRECISION
from driftpy.decode.utils import decode_name
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID, TransferParams, transfer
from solders.sysvar import RENT as SYSVAR_RENT_PUBKEY
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account, sync_native, SyncNativeParams
from solana.transaction import Transaction

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

class DriftAccountManager:
    def __init__(self):
        self.drift_helper = DriftHelper()
        self.drift_client = None
        self.logger = logging.getLogger(__name__)
        
    async def setup(self):
        """Initialize the Drift client"""
        # Initialize with specific transaction parameters like in the example
        self.drift_client = await self.drift_helper.initialize_drift(
            tx_params=TxParams(
                compute_units_price=85_000,  # From example
                compute_units=1_400_000      # From example
            )
        )
        
        # Add subscription verification
        await self.drift_client.subscribe()
        
        # Add user with subaccount 0 (Main Account)
        await self.drift_client.add_user(0)
        
        await self.drift_client.account_subscriber.fetch()
        self.logger.info("Account manager initialized and subscribed successfully")
        
    async def deposit_sol(self, amount, spot_market_index=1):  # SOL is index 1 on devnet
        """Deposit SOL into the Drift account."""
        self.logger.info(f"Attempting to deposit {amount} SOL...")
        
        # Initialize user account if needed
        try:
            self.logger.info("Initializing Drift user account...")
            await self.drift_client.initialize_user(0)  # 0 is the main subaccount
            self.logger.info("Drift user account initialized successfully")
        except Exception as e:
            # If initialization fails because account already exists, that's fine
            self.logger.info(f"User account already initialized or error: {e}")
        
        # Convert amount to proper precision
        spot_market = self.drift_client.get_spot_market_account(spot_market_index)
        if not spot_market:
            raise ValueError(f"Spot market with index {spot_market_index} not found")
        
        amount_in_precision = int(amount * (10 ** spot_market.decimals))
        self.logger.info(f"Amount in proper precision: {amount_in_precision}")

        # Try using the direct deposit method first
        try:
            self.logger.info("Attempting direct deposit...")
            tx_sig = await self.drift_client.deposit(
                amount=amount_in_precision,
                spot_market_index=spot_market_index,
                sub_account_id=0,  # Main account
                reduce_only=False
            )
            self.logger.info(f"Direct deposit successful! Transaction signature: {tx_sig}")
            return tx_sig
        except Exception as e:
            self.logger.info(f"Direct deposit failed, trying with wrapped SOL: {e}")
            
            # Create a temporary WSOL account and deposit in one transaction
            self.logger.info("Creating temporary WSOL account and deposit instructions...")
            wsol_ixs, wsol_account = await self.drift_client.get_wrapped_sol_account_creation_ixs(
                amount=amount_in_precision,
                include_rent=True
            )
            
            # Get deposit instruction
            deposit_ix = await self.drift_client.get_deposit_collateral_ix(
                amount=amount_in_precision,
                spot_market_index=spot_market_index,
                user_token_account=wsol_account,
                sub_account_id=0
            )
            
            # Combine instructions and send transaction
            self.logger.info("Sending combined transaction...")
            # Use the direct deposit method from the documentation
            try:
                tx_sig = await self.drift_client.send_ixs([deposit_ix])
                self.logger.info(f"Deposit successful! Transaction signature: {tx_sig}")
                return tx_sig
            except Exception as e:
                self.logger.error(f"Error depositing SOL: {e}")
                raise
            
    async def withdraw_sol(self, amount: float) -> str:
        """Withdraw SOL from Drift account"""
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            logger.info(f"Attempting to withdraw {amount} SOL...")
            amount_lamports = int(amount * 1e9)
            
            tx_sig = await self.drift_client.withdraw(
                amount=amount_lamports,
                spot_market_index=0,  # SOL market index
                user_token_account=None  # Use associated token account
            )
            
            logger.info(f"Withdrawal successful! Tx: {tx_sig}")
            await self.show_balances()
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error withdrawing SOL: {str(e)}")
            raise
            
    async def show_balances(self):
        """Display current account balances and PnL"""
        if not self.drift_client:
            raise Exception("Drift client not initialized")
            
        try:
            drift_user = self.drift_client.get_user()
            if not drift_user:
                logger.error("Could not fetch user data")
                return
                
            user = drift_user.get_user_account()
            logger.info("\n=== Account Info ===")
            logger.info(f"Subaccount name: {decode_name(user.name)}")
            
            # Get collateral and PnL info
            spot_collateral = drift_user.get_spot_market_asset_value(
                None,
                include_open_orders=True
            )
            unrealized_pnl = drift_user.get_unrealized_pnl(False)
            total_collateral = drift_user.get_total_collateral()
            
            logger.info("\n=== Collateral & PnL ===")
            logger.info(f"Spot Collateral: ${spot_collateral / QUOTE_PRECISION:,.2f}")
            logger.info(f"Unrealized PnL: ${unrealized_pnl / QUOTE_PRECISION:,.2f}")
            logger.info(f"Total Collateral: ${total_collateral / QUOTE_PRECISION:,.2f}")
            
            # Get liability info
            perp_liability = drift_user.get_total_perp_position_liability()
            spot_liability = drift_user.get_spot_market_liability_value()
            
            logger.info("\n=== Liabilities ===")
            logger.info(f"Perp Liability: ${perp_liability / QUOTE_PRECISION:,.2f}")
            logger.info(f"Spot Liability: ${spot_liability / QUOTE_PRECISION:,.2f}")
            
            # Risk metrics
            total_liability = drift_user.get_margin_requirement(None)
            leverage = drift_user.get_leverage()
            
            logger.info("\n=== Risk Metrics ===")
            logger.info(f"Total Liability: ${total_liability / QUOTE_PRECISION:,.2f}")
            logger.info(f"Current Leverage: {leverage / 10_000:.2f}x")
            
            # Show spot positions from user account
            logger.info("\n=== Spot Positions ===")
            for position in user.spot_positions:
                if position.scaled_balance != 0:
                    market = await self.drift_client.get_spot_market_account(position.market_index)
                    token_amount = position.scaled_balance / (10 ** market.decimals)
                    logger.info(f"Market {position.market_index}: {token_amount:.6f}")
                    
        except Exception as e:
            logger.error(f"Error showing balances: {str(e)}")
            raise

    async def deposit_usdc(self, amount: float):
        """
        Deposit USDC into the Drift account.
        
        Args:
            amount (float): Amount of USDC to deposit
        """
        self.logger.info(f"Attempting to deposit {amount} USDC into Main Account (subaccount 0)...")
        
        # Initialize user account if needed
        try:
            self.logger.info("Initializing Drift user account...")
            await self.drift_client.initialize_user(0)  # 0 is the main subaccount
            self.logger.info("Drift user account initialized successfully")
        except Exception as e:
            # If initialization fails because account already exists, that's fine
            self.logger.info(f"User account already initialized or error: {e}")
        
        # Get USDC market index and convert amount to proper precision
        spot_market_index = 1  # USDC market
        amount_in_precision = self.drift_client.convert_to_spot_precision(amount, spot_market_index)
        self.logger.info(f"Amount in proper precision: {amount_in_precision}")

        # Get the associated token account for USDC
        user_token_account = self.drift_client.get_associated_token_account_public_key(spot_market_index)
        self.logger.info(f"Using USDC token account: {user_token_account}")

        # Now deposit the USDC into Drift
        self.logger.info(f"Depositing {amount} USDC into Drift Main Account...")
        try:
            tx_sig = await self.drift_client.deposit(
                amount=amount_in_precision,
                spot_market_index=spot_market_index,
                user_token_account=user_token_account,
                sub_account_id=0,  # Main account
                reduce_only=False,
                user_initialized=True  # We already initialized the user
            )
            
            self.logger.info(f"Deposit successful! Transaction signature: {tx_sig}")
            return tx_sig
        except Exception as e:
            self.logger.error(f"Error depositing USDC: {e}")
            raise

async def main():
    """CLI interface for account management"""
    parser = argparse.ArgumentParser(description="Drift Account Manager CLI")
    parser.add_argument('action', choices=['deposit', 'withdraw', 'balance'],
                       help='Action to perform')
    parser.add_argument('--amount', type=float, help='Amount for deposit/withdraw')
    
    args = parser.parse_args()
    
    manager = DriftAccountManager()
    try:
        await manager.setup()
        
        if args.action == 'deposit':
            if not args.amount:
                raise ValueError("Amount required for deposit")
            await manager.deposit_sol(args.amount)
            
        elif args.action == 'withdraw':
            if not args.amount:
                raise ValueError("Amount required for withdrawal")
            await manager.withdraw_sol(args.amount)
            
        elif args.action == 'balance':
            await manager.show_balances()
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if manager.drift_client:
            await manager.drift_client.unsubscribe()
    except Exception as e:
        logger.error(f"Error in account manager: {str(e)}")
        if manager.drift_client:
            await manager.drift_client.unsubscribe()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}") 