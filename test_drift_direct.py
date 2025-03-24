#!/usr/bin/env python3
"""
Direct test for Drift connection without using the wallet manager.
"""

import os
import json
import logging
import asyncio
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.constants.config import configs

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Test loading keypair and connecting to Drift directly."""
    
    # Step 1: Load keypair from JSON file
    keypair_path = "/home/dex/.config/solana/keys/id.json"
    logger.info(f"Keypair path: {keypair_path}")
    logger.info(f"File exists: {os.path.exists(keypair_path)}")
    
    try:
        # Load keypair
        with open(keypair_path, 'r') as f:
            keypair_data = json.load(f)
            keypair = Keypair.from_bytes(bytes(keypair_data))
            logger.info(f"Successfully loaded keypair!")
            logger.info(f"Public key: {keypair.pubkey()}")
        
        # Step 2: Connect to Solana
        config = configs["mainnet"]
        rpc_url = os.environ.get("HELIUS_RPC_ENDPOINT", config.default_http)
        logger.info(f"Using RPC URL: {rpc_url}")
        
        connection = AsyncClient(rpc_url)
        
        # Get balance to verify connection
        resp = await connection.get_balance(keypair.pubkey())
        balance = resp.value / 1_000_000_000  # Convert lamports to SOL
        logger.info(f"Wallet balance: {balance} SOL")
        
        # Print config details to verify
        logger.info(f"Config market_lookup_table: {config.market_lookup_table}")
        
        # Step 3: Connect to Drift
        logger.info("Initializing Drift client...")
        
        drift_client = DriftClient(
            connection=connection,
            wallet=keypair,
            env="mainnet",
            market_lookup_table=config.market_lookup_table,
            perp_market_indexes=[0, 1, 2, 3, 4, 5],  # Start with just a few markets
            spot_market_indexes=[0, 1]
        )
        
        # Initialize client
        logger.info("Subscribing to Drift client...")
        await drift_client.subscribe()
        logger.info("Successfully connected to Drift!")
        
        # Step 4: Get some basic market data to verify
        markets = await drift_client.get_perp_market_accounts()
        logger.info(f"Found {len(markets)} perpetual markets:")
        for market in markets:
            market_name = bytes(market.account.name).decode("utf-8").strip()
            logger.info(f"- {market_name}")
        
        # Clean up
        await connection.close()
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 