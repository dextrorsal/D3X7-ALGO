#!/usr/bin/env python3
"""
Simple script to deposit SOL on Drift devnet.
This is a minimal implementation following the DriftPy documentation.
"""

import asyncio
import logging
import os
import traceback
import sys
import json
from anchorpy import Wallet
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.keypair import load_keypair
from driftpy.types import TxParams
from solders.keypair import Keypair

# Configure logging - simpler format with only essential info
logging.basicConfig(
    level=logging.INFO,  # Set to INFO to reduce verbosity
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Make sure we're using devnet
os.environ["DEVNET_RPC_ENDPOINT"] = "https://api.devnet.solana.com"

async def check_sol_balance(connection, pubkey):
    """Check SOL balance of the wallet"""
    try:
        balance_resp = await connection.get_balance(pubkey)
        balance = balance_resp.value  # Extract the actual balance value
        logger.info(f"SOL Balance: {balance / 1e9} SOL ({balance} lamports)")
        return balance
    except Exception as e:
        logger.error(f"Failed to get SOL balance: {e}")
        return None

async def deposit_sol():
    """Simple function to deposit SOL on Drift devnet with minimal logging"""
    drift_client = None
    
    try:
        logger.info("=== STEP 1: Loading wallet ===")
        # Try to load from environment variable
        private_key = os.environ.get("PRIVATE_KEY")
        if private_key:
            logger.info("Using wallet from PRIVATE_KEY environment variable")
            keypair = load_keypair(private_key)
        else:
            logger.info("No PRIVATE_KEY found, using default wallet from ~/.config/solana/id.json")
            # Load keypair from default location
            keypair_path = os.path.expanduser("~/.config/solana/id.json")
            if not os.path.exists(keypair_path):
                raise FileNotFoundError(f"Keypair not found at {keypair_path}")
                
            with open(keypair_path, 'r') as f:
                keypair_bytes = bytes(json.load(f))
                
            keypair = Keypair.from_bytes(keypair_bytes)
            
        wallet = Wallet(keypair)
        logger.info(f"Wallet loaded successfully: {wallet.public_key}")
        
        logger.info("\n=== STEP 2: Connecting to Solana ===")
        rpc_url = os.environ.get("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
        connection = AsyncClient(rpc_url)
        
        # Check connection
        try:
            version = await connection.get_version()
            logger.info(f"Connected to Solana node version: {version}")
        except Exception as e:
            logger.error(f"Failed to connect to Solana: {e}")
            return
        
        # Check SOL balance
        balance = await check_sol_balance(connection, wallet.public_key)
        if balance is None or balance < 10000000:  # Less than 0.01 SOL
            logger.error(f"Insufficient SOL balance for deposit and fees")
            return
        
        logger.info("\n=== STEP 3: Creating Drift client ===")
        drift_client = DriftClient(
            connection,
            wallet,
            env="devnet",
            account_subscription=AccountSubscriptionConfig("websocket"),
            tx_params=TxParams(compute_units_price=85_000, compute_units=1_400_000)
        )
        logger.info("Drift client created successfully")
        
        logger.info("\n=== STEP 4: Subscribing to Drift ===")
        await drift_client.subscribe()
        logger.info("Successfully subscribed to Drift")
        
        # Check SOL price from Drift's oracle
        logger.info("\n=== CHECKING ORACLE PRICES ===")
        spot_markets = drift_client.get_spot_market_accounts()
        for market in spot_markets:
            market_name = bytes(market.name).decode('utf-8').strip()
            if market_name.upper() == "SOL":
                try:
                    # Get the oracle price directly from the market
                    oracle_price = market.historical_oracle_data.last_oracle_price / (10 ** 6)  # Usually in 6 decimals
                    logger.info(f"SOL Oracle Price on Drift Devnet: ${oracle_price:.2f}")
                    logger.info(f"This is a test price on devnet and doesn't match the real market price of ~$136")
                    
                    # Calculate the value of our deposit based on this price
                    logger.info(f"Value of 0.4 SOL at devnet price: ${0.4 * oracle_price:.2f}")
                    logger.info(f"Value of 0.4 SOL at real price (~$136): ${0.4 * 136:.2f}")
                except Exception as e:
                    logger.warning(f"Could not get oracle price for {market_name}: {e}")
        
        logger.info("\n=== STEP 5: Initializing user account ===")
        try:
            # Check if user account already exists
            user_exists = False
            try:
                user_account = drift_client.get_user_account_public_key(0)
                account_info = await connection.get_account_info(user_account)
                user_exists = account_info is not None and account_info.data is not None
                logger.info(f"User account check: {user_account} exists: {user_exists}")
            except Exception as e:
                logger.warning(f"Error checking if user account exists: {e}")
            
            if not user_exists:
                logger.info("Initializing new user account...")
                init_tx = await drift_client.initialize_user(0)
                logger.info(f"User account initialized successfully: {init_tx}")
            else:
                logger.info("User account already exists, skipping initialization")
        except Exception as e:
            logger.warning(f"User account initialization error (may already exist): {str(e)}")
        
        logger.info("\n=== STEP 6: Adding user to client ===")
        await drift_client.add_user(0)
        logger.info("User added to client successfully")
        
        logger.info("\n=== STEP 7: Getting SOL market info ===")
        # List all spot markets for debugging
        spot_markets = drift_client.get_spot_market_accounts()
        logger.info("Available spot markets:")
        for market in spot_markets:
            market_name = bytes(market.name).decode('utf-8').strip()
            if market_name.upper() == "SOL":
                logger.info(f"  Index: {market.market_index}, Name: {market_name}, Decimals: {market.decimals}")
        
        # Get SOL market
        spot_market_index = 1  # SOL is index 1 on devnet
        spot_market = drift_client.get_spot_market_account(spot_market_index)
        if not spot_market:
            logger.error(f"Spot market with index {spot_market_index} not found")
            # Try to find SOL market by name
            for market in spot_markets:
                market_name = bytes(market.name).decode('utf-8').strip()
                if market_name.upper() == "SOL":
                    spot_market = market
                    spot_market_index = market.market_index
                    logger.info(f"Found SOL market at index {spot_market_index}")
                    break
            
            if not spot_market:
                raise ValueError(f"SOL spot market not found")
        
        market_name = bytes(spot_market.name).decode('utf-8').strip()
        logger.info(f"Using spot market: Index {spot_market_index}, Name: {market_name}, Decimals: {spot_market.decimals}")
        
        logger.info("\n=== STEP 8: Preparing deposit amount ===")
        amount = 1.0  # 1 SOL
        amount_in_precision = int(amount * (10 ** spot_market.decimals))
        logger.info(f"Depositing {amount} SOL (precision: {amount_in_precision})")
        
        # Check if we have enough SOL for the deposit
        if balance < amount_in_precision + 10000000:  # deposit + ~0.01 SOL for fees
            logger.error(f"Insufficient SOL balance for deposit: {balance/1e9} SOL, need {(amount_in_precision + 10000000)/1e9} SOL")
            # Try with a smaller amount if we don't have enough for 1 SOL
            amount = 0.4  # Fallback to 0.4 SOL
            amount_in_precision = int(amount * (10 ** spot_market.decimals))
            logger.info(f"Trying with smaller amount: {amount} SOL (precision: {amount_in_precision})")
            
            if balance < amount_in_precision + 10000000:
                logger.error(f"Still insufficient SOL balance for smaller deposit: {balance/1e9} SOL, need {(amount_in_precision + 10000000)/1e9} SOL")
                return
        
        logger.info("\n=== STEP 9: Executing deposit ===")
        # Get the token account for SOL
        try:
            token_account = drift_client.get_associated_token_account_public_key(spot_market_index)
            logger.info(f"Using token account: {token_account}")
        except Exception as e:
            logger.warning(f"Error getting token account: {e}")
            token_account = None
        
        # Simple deposit using the direct method
        try:
            logger.info("Sending deposit transaction...")
            tx_sig = await drift_client.deposit(
                amount=amount_in_precision,
                spot_market_index=spot_market_index,
                user_token_account=token_account
            )
            
            logger.info(f"Deposit transaction sent! Signature: {tx_sig}")
            
            # Wait for confirmation
            logger.info("Waiting for transaction confirmation...")
            await connection.confirm_transaction(tx_sig.tx_sig)
            logger.info(f"Deposit confirmed! Transaction signature: {tx_sig}")
        except Exception as e:
            logger.error(f"Deposit failed: {str(e)}")
            
            # Try alternative method with wrapped SOL
            logger.info("\n=== STEP 9b: Trying alternative deposit method with wrapped SOL ===")
            try:
                logger.info("Creating wrapped SOL account...")
                wsol_ixs, wsol_account = await drift_client.get_wrapped_sol_account_creation_ixs(
                    amount=amount_in_precision,
                    include_rent=True
                )
                
                logger.info(f"Created wrapped SOL account: {wsol_account}")
                logger.info("Getting deposit instruction...")
                
                deposit_ix = await drift_client.get_deposit_collateral_ix(
                    amount=amount_in_precision,
                    spot_market_index=spot_market_index,
                    user_token_account=wsol_account,
                    sub_account_id=0
                )
                
                logger.info("Sending wrapped SOL deposit transaction...")
                all_ixs = []
                for ix in wsol_ixs:
                    all_ixs.append(ix)
                all_ixs.append(deposit_ix)
                
                tx_sig = await drift_client.send_ixs(all_ixs)
                logger.info(f"Wrapped SOL deposit transaction sent! Signature: {tx_sig}")
                
                # Wait for confirmation
                logger.info("Waiting for transaction confirmation...")
                await connection.confirm_transaction(tx_sig.tx_sig)
                logger.info(f"Wrapped SOL deposit confirmed! Transaction signature: {tx_sig}")
            except Exception as e2:
                logger.error(f"Wrapped SOL deposit also failed: {str(e2)}")
                raise
        
        logger.info("\n=== STEP 10: Checking balances ===")
        # Show balances
        drift_user = drift_client.get_user()
        if drift_user:
            collateral = drift_user.get_total_collateral()
            logger.info(f"Total collateral: ${collateral / 1e6:.2f}")
            
            # Show spot positions
            user_account = drift_user.get_user_account()
            logger.info("Spot positions:")
            for position in user_account.spot_positions:
                if position.scaled_balance != 0:
                    market = drift_client.get_spot_market_account(position.market_index)
                    if market:
                        market_name = bytes(market.name).decode('utf-8').strip()
                        token_amount = position.scaled_balance / (10 ** market.decimals)
                        logger.info(f"  {market_name} (Index {position.market_index}): {token_amount:.6f}")
        else:
            logger.warning("Could not get user data to check balances")
        
    except Exception as e:
        logger.error(f"Error in deposit_sol: {str(e)}")
    finally:
        logger.info("\n=== STEP 11: Cleanup ===")
        # Clean up
        if drift_client:
            try:
                await drift_client.unsubscribe()
                logger.info("Unsubscribed from Drift client")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(deposit_sol())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}") 