#!/usr/bin/env python3
"""
Script to check Drift collateral calculation details.
"""

import asyncio
import logging
from typing import Optional
from solders.keypair import Keypair
from anchorpy.provider import Wallet
from driftpy.drift_client import DriftClient
from driftpy.accounts.get_accounts import get_perp_market_account, get_spot_market_account
from driftpy.types import TxParams
from driftpy.account_subscription_config import AccountSubscriptionConfig
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_solana_client, get_network

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def check_collateral():
    """Check collateral calculation details"""
    try:
        # Initialize wallet manager and get MAIN wallet
        wallet_manager = WalletManager()
        wallet = wallet_manager.get_wallet("MAIN")
        if not wallet:
            raise ValueError("Failed to load MAIN wallet")
            
        # Log public key
        logger.info(f"Using wallet with public key: {wallet.get_public_key()}")
        
        # Get network and RPC client
        network = get_network()
        connection = await get_solana_client(network)
        logger.info(f"Connected to {network}")
        
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
            sub_account_ids=[0, 1, 2, 3, 4]  # Check all possible subaccounts
        )
        
        # Subscribe to get updates
        await drift_client.subscribe()
        logger.info("Subscribed to Drift client")
        
        try:
            # Get user account
            drift_user = drift_client.get_user()
            if not drift_user:
                logger.info("No user account found")
                return
                
            user = drift_user.get_user_account()
            if not user:
                logger.info("No user account data found")
                return
                
            # Log spot positions
            logger.info("\n=== SPOT POSITIONS ===")
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
                    
                    logger.info(f"Market: {market.name}")
                    logger.info(f"Token Amount: {token_amount}")
                    logger.info(f"Token Price: ${market.historical_oracle_data.last_oracle_price / 1e6}")
                    logger.info(f"Position Value: ${token_value}")
                    logger.info("---")
                    
            # Log perp positions
            logger.info("\n=== PERP POSITIONS ===")
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
                    
                    logger.info(f"Market: {market.name}")
                    logger.info(f"Position Size: {position_size}")
                    logger.info(f"Entry Price: ${perp_position.get_entry_price() / 1e6}")
                    logger.info(f"Current Price: ${market.amm.historical_oracle_data.last_oracle_price / 1e6}")
                    logger.info(f"Position Value: ${position_value}")
                    logger.info(f"Unrealized PnL: ${perp_position.get_unrealized_pnl(market) / 1e6}")
                    logger.info("---")
                    
            # Log collateral info
            logger.info("\n=== COLLATERAL INFO ===")
            total_collateral = drift_user.get_total_collateral()
            logger.info(f"Total Collateral: ${total_collateral / 1e6}")
            
            # Try to get additional risk metrics
            try:
                free_collateral = drift_user.get_free_collateral()
                logger.info(f"Free Collateral: ${free_collateral / 1e6}")
                
                margin_requirement = drift_user.get_margin_requirement()
                logger.info(f"Margin Requirement: ${margin_requirement / 1e6}")
                
                leverage = drift_user.get_leverage()
                logger.info(f"Current Leverage: {leverage}x")
            except Exception as e:
                logger.error(f"Error getting risk metrics: {e}")
                
        finally:
            # Clean up
            await drift_client.unsubscribe()
            
    except Exception as e:
        logger.error(f"Error checking collateral: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(check_collateral()) 