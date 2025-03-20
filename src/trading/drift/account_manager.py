#!/usr/bin/env python3
"""
Drift account management module.
Handles deposits, withdrawals, balance checking, and PnL tracking.
"""

import asyncio
import logging
import argparse
from typing import Optional, Dict, List, Any
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
        
        # Initialize each subaccount
        for subaccount_id in range(5):  # 0,1,2,3,4
            try:
                # Initialize user account if needed
                tx_sig = await self.drift_client.initialize_user(
                    sub_account_id=subaccount_id,
                    name=f"Subaccount {subaccount_id}"
                )
                self.logger.info(f"Initialized subaccount {subaccount_id}")
            except Exception as e:
                if "already in use" in str(e):
                    self.logger.info(f"Subaccount {subaccount_id} already exists")
                else:
                    self.logger.error(f"Error initializing subaccount {subaccount_id}: {str(e)}")
                    continue
            
            # Add user to client
            try:
                await self.drift_client.add_user(subaccount_id)
                self.logger.info(f"Added subaccount {subaccount_id} to client")
            except Exception as e:
                self.logger.error(f"Error adding subaccount {subaccount_id} to client: {str(e)}")
                continue
        
        await self.drift_client.account_subscriber.fetch()
        self.logger.info("Account manager initialized and subscribed successfully")

    async def list_subaccounts(self) -> List[Dict[str, Any]]:
        """List all subaccounts for the current wallet."""
        if not self.drift_client:
            logging.error("DriftClient not initialized")
            return []

        try:
            found_accounts = []
            # Check subaccounts 0 through 4 since they're already created
            for subaccount_id in range(5):  # 0,1,2,3,4
                try:
                    logging.info(f"Checking subaccount {subaccount_id}...")
                    
                    # Get user for this subaccount ID
                    user = self.drift_client.get_user(sub_account_id=subaccount_id)
                    if not user:
                        logging.info(f"No user found for subaccount {subaccount_id}")
                        continue
                    
                    # Try to get user account data
                    user_account = user.get_user_account()
                    if not user_account:
                        logging.info(f"No user account data for subaccount {subaccount_id}")
                        continue

                    # Get spot positions and token amounts
                    token_amounts = {}
                    for market_index in range(5):  # Check first 5 markets
                        try:
                            token_amount = user.get_token_amount(market_index)
                            if token_amount != 0:
                                token_amounts[market_index] = {
                                    'amount': token_amount,
                                    'type': 'deposit' if token_amount > 0 else 'borrow'
                                }
                        except Exception as e:
                            logging.debug(f"Error getting token amount for market {market_index}: {str(e)}")
                            continue

                    found_account = {
                        "subaccount_id": subaccount_id,
                        "name": decode_name(user_account.name) if user_account.name else f"Subaccount {subaccount_id}",
                        "authority": str(user_account.authority),
                        "status": "active",
                        "token_amounts": token_amounts
                    }
                    logging.info(f"Found subaccount: {found_account}")
                    found_accounts.append(found_account)

                except Exception as e:
                    logging.info(f"Error checking subaccount {subaccount_id}: {str(e)}")
                    continue

            if not found_accounts:
                logging.info("No subaccounts found")
            else:
                logging.info(f"Found {len(found_accounts)} subaccounts")

            return found_accounts

        except Exception as e:
            logging.error(f"Error listing subaccounts: {str(e)}")
            return []

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
            
            # Show spot positions from user account
            logger.info("\n=== Spot Positions ===")
            for position in user.spot_positions:
                if position.scaled_balance != 0:
                    market = self.drift_client.get_spot_market_account(position.market_index)
                    token_amount = position.scaled_balance / (10 ** market.decimals)
                    logger.info(f"Market {position.market_index}: {token_amount:.6f}")
                    
        except Exception as e:
            logger.error(f"Error showing balances: {str(e)}")
            raise

async def main():
    """CLI interface for account management"""
    parser = argparse.ArgumentParser(description="Drift Account Manager CLI")
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')
    
    # Balance command
    balance_parser = subparsers.add_parser('balance', help='Show account balances')
    
    # List subaccounts command
    subparsers.add_parser('list-subaccounts', help='List all subaccounts')
    
    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        return
    
    manager = DriftAccountManager()
    try:
        await manager.setup()
        
        if args.action == 'balance':
            await manager.show_balances()
        elif args.action == 'list-subaccounts':
            await manager.list_subaccounts()
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in account manager: {str(e)}")
        raise
    finally:
        if manager.drift_client:
            await manager.drift_client.unsubscribe()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise 