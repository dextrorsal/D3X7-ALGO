#!/usr/bin/env python3
"""
Simple script to check Drift devnet balances
"""

import asyncio
import logging
import os
import json
from anchorpy.provider import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Check balances on Drift devnet"""
    try:
        # Load keypair
        keypair_path = os.path.expanduser("~/.config/solana/id.json")
        if not os.path.exists(keypair_path):
            raise FileNotFoundError(f"Keypair not found at {keypair_path}")
            
        with open(keypair_path, 'r') as f:
            keypair_bytes = bytes(json.load(f))
            
        keypair = Keypair.from_bytes(keypair_bytes)
        logger.info(f"Loaded wallet: {keypair.pubkey()}")
        
        # Connect to devnet
        connection = AsyncClient("https://api.devnet.solana.com")
        provider = Provider(connection, Wallet(keypair))
        
        # Initialize Drift client
        drift_client = DriftClient(
            connection,
            Wallet(keypair),
            env="devnet"
        )
        
        # Subscribe and initialize
        await drift_client.subscribe()
        await drift_client.add_user(0)  # Main account
        await drift_client.account_subscriber.fetch()
        
        # Get user info
        drift_user = drift_client.get_user()
        if not drift_user:
            logger.error("Could not fetch user data")
            return
            
        user = drift_user.get_user_account()
        
        # Show balances
        logger.info("\n=== Account Info ===")
        
        # Get collateral info
        spot_collateral = drift_user.get_spot_market_asset_value(
            None,
            include_open_orders=True
        )
        unrealized_pnl = drift_user.get_unrealized_pnl(False)
        total_collateral = drift_user.get_total_collateral()
        
        logger.info(f"Spot Collateral: ${spot_collateral / QUOTE_PRECISION:,.2f}")
        logger.info(f"Unrealized PnL: ${unrealized_pnl / QUOTE_PRECISION:,.2f}")
        logger.info(f"Total Collateral: ${total_collateral / QUOTE_PRECISION:,.2f}")
        
        # Show positions
        logger.info("\n=== Positions ===")
        for position in user.spot_positions:
            if position.scaled_balance != 0:
                market = drift_client.get_spot_market_account(position.market_index)
                token_amount = position.scaled_balance / (10 ** market.decimals)
                logger.info(f"Market {position.market_index}: {token_amount:.6f}")
                
    except KeyboardInterrupt:
        logger.info("\nGracefully shutting down...")
    except Exception as e:
        logger.error(f"Error checking balances: {e}")
        raise
    finally:
        if 'drift_client' in locals():
            await drift_client.unsubscribe()
            logger.info("Successfully unsubscribed from Drift")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error: {e}")