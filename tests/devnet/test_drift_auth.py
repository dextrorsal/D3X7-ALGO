#!/usr/bin/env python3
"""
Test script for Drift authentication.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from src.core.models import ExchangeCredentials
import sys

sys.path.append("/home/dex/ultimate_data_fetcher")

from src.exchanges.drift.auth import DriftAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def test_drift_auth():
    """
    Test the Drift authentication module.
    """
    # Get credentials from environment variables
    private_key = os.getenv("DRIFT_PRIVATE_KEY")
    program_id = os.getenv(
        "DRIFT_PROGRAM_ID", "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
    )
    rpc_url = os.getenv("DRIFT_RPC_URL", "https://api.mainnet-beta.solana.com")

    if not private_key:
        logger.error("DRIFT_PRIVATE_KEY not found in environment variables")
        return

    logger.info(f"Using RPC URL: {rpc_url}")
    logger.info(f"Using program ID: {program_id}")

    # Create credentials with additional parameters
    credentials = ExchangeCredentials(
        additional_params={
            "private_key": private_key,
            "program_id": program_id,
            "rpc_url": rpc_url,
        }
    )

    # Initialize the authentication handler
    auth_handler = DriftAuth(credentials)

    # Check if authentication is valid
    if auth_handler.is_authenticated():
        logger.info("Successfully authenticated with Drift")

        try:
            # Initialize the Drift client
            logger.info("Initializing Drift client...")
            client = await auth_handler.initialize_client()
            logger.info("Drift client initialized successfully")

            # Get public key
            public_key = auth_handler.get_wallet().pubkey()
            logger.info(f"Wallet public key: {public_key}")

            # Close the client
            await auth_handler.close()
            logger.info("Drift client closed successfully")
        except Exception as e:
            logger.error(f"Error initializing Drift client: {e}")
    else:
        logger.error("Failed to authenticate with Drift")


if __name__ == "__main__":
    asyncio.run(test_drift_auth())
