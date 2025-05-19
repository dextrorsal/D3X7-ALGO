#!/usr/bin/env python3
"""
Direct test for Drift connection without using the wallet manager.
"""

import os
import json
import logging
import asyncio
import time
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.constants.config import configs
from httpx import HTTPStatusError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def retry_async(func, retries=3, delay=1):
    """Retry an async function with exponential backoff."""
    last_error = None
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt < retries - 1:  # Don't sleep on the last attempt
                sleep_time = delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s: {str(e)}")
                await asyncio.sleep(sleep_time)
    raise last_error

async def main():
    """Test loading keypair and connecting to Drift directly."""
    connection = None
    drift_client = None
    
    try:
        # Step 1: Load keypair from JSON file
        keypair_path = "/home/dex/.config/solana/keys/id.json"
        logger.info(f"Keypair path: {keypair_path}")
        logger.info(f"File exists: {os.path.exists(keypair_path)}")
        
        # Load keypair
        with open(keypair_path, 'r') as f:
            keypair_data = json.load(f)
            keypair = Keypair.from_bytes(bytes(keypair_data))
            logger.info(f"Successfully loaded keypair!")
            logger.info(f"Public key: {keypair.pubkey()}")
        
        # Step 2: Connect to Solana (using devnet)
        config = configs["devnet"]
        rpc_url = "https://api.devnet.solana.com"  # Use devnet
        logger.info(f"Using RPC URL: {rpc_url}")
        
        connection = AsyncClient(rpc_url)
        
        # Get balance to verify connection with retry
        async def check_balance():
            resp = await connection.get_balance(keypair.pubkey())
            return resp.value / 1_000_000_000  # Convert lamports to SOL
        
        balance = await retry_async(check_balance)
        logger.info(f"Wallet balance: {balance} SOL")
        
        # Print config details to verify
        logger.info(f"Config market_lookup_table: {config.market_lookup_table}")
        
        # Step 3: Connect to Drift
        logger.info("Initializing Drift client...")
        
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="devnet",
            market_lookup_table=config.market_lookup_table,
            perp_market_indexes=[0, 1],  # Start with just a couple markets for testing
            spot_market_indexes=[0]
        )
        
        # Initialize client with retry
        async def init_drift():
            logger.info("Subscribing to Drift client...")
            await drift_client.subscribe()
            logger.info("Successfully connected to Drift!")
        
        await retry_async(init_drift)
        
        # Step 4: Get some basic market data to verify
        async def get_markets():
            # Get market states
            market_states = drift_client.get_perp_market_accounts()
            logger.info(f"Found {len(market_states)} perpetual markets:")
            
            # Get market info for each market
            for market_state in market_states:
                try:
                    market_name = bytes(market_state.name).decode("utf-8").strip()
                    market_index = market_state.market_index
                    logger.info(f"- Market {market_index}: {market_name}")
                    
                    # Get additional market info
                    oracle_price = drift_client.get_oracle_price_data_for_perp_market(market_index)
                    logger.info(f"  Oracle price: ${oracle_price.price:.2f}")
                    
                except Exception as e:
                    logger.warning(f"Error getting details for market {market_index}: {e}")
            
            return market_states
        
        await retry_async(get_markets)
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up
        if drift_client:
            try:
                await drift_client.unsubscribe()
                logger.info("Unsubscribed from Drift client")
            except Exception as e:
                logger.error(f"Error unsubscribing from Drift: {e}")
        
        if connection:
            try:
                await connection.close()
                logger.info("Closed Solana connection")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 