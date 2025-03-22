"""
Example demonstrating how to use the Drift authentication module.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
import base58
from solders.keypair import Keypair

from src.core.models import ExchangeCredentials
from src.exchanges.auth import DriftAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def main():
    """
    Demonstrate how to use the Drift authentication module.
    """
    # Method 1: Using environment variables
    # Make sure to set these in your .env file:
    # DRIFT_PRIVATE_KEY=your_base58_encoded_private_key
    # DRIFT_PROGRAM_ID=dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH (or your custom program ID)
    # DRIFT_RPC_URL=https://api.mainnet-beta.solana.com (or your custom RPC URL)
    
    private_key = os.getenv("DRIFT_PRIVATE_KEY")
    program_id = os.getenv("DRIFT_PROGRAM_ID", "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")
    rpc_url = os.getenv("DRIFT_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    if private_key:
        logger.info("Using private key from environment variables")
        
        # Create credentials with additional parameters
        credentials = ExchangeCredentials(
            additional_params={
                "private_key": private_key,
                "program_id": program_id,
                "rpc_url": rpc_url
            }
        )
        
        # Initialize the authentication handler
        auth_handler = DriftAuth(credentials)
        
        # Check if authentication is valid
        if auth_handler.is_authenticated():
            logger.info("Successfully authenticated with Drift")
            
            # Initialize the Drift client
            client = await auth_handler.initialize_client()
            
            # Example: Get user account
            try:
                user_account = await client.get_user_account()
                logger.info(f"User account: {user_account.authority}")
            except Exception as e:
                logger.error(f"Error getting user account: {e}")
            
            # Close the client
            await auth_handler.close()
        else:
            logger.error("Failed to authenticate with Drift")
    else:
        logger.warning("No private key found in environment variables")
    
    # Method 2: Creating a keypair directly
    logger.info("\nDemonstrating direct keypair creation:")
    
    try:
        # Generate a new keypair for demonstration purposes
        # In a real application, you would use your actual keypair
        keypair = Keypair()
        
        # Convert keypair to bytes for storage
        keypair_bytes = keypair.secret()
        
        # Create credentials with the keypair
        credentials = ExchangeCredentials(
            additional_params={
                "private_key": list(keypair_bytes),  # Convert bytes to list for JSON serialization
                "program_id": program_id,
                "rpc_url": rpc_url
            }
        )
        
        # Initialize the authentication handler
        auth_handler = DriftAuth(credentials)
        
        # Check if authentication is valid
        if auth_handler.is_authenticated():
            logger.info("Successfully created authentication handler with new keypair")
            logger.info(f"Public key: {keypair.pubkey()}")
            
            # Note: This keypair won't have any funds or permissions on Drift
            # It's just for demonstration purposes
            
            # Close the client
            await auth_handler.close()
        else:
            logger.error("Failed to create authentication handler")
    except Exception as e:
        logger.error(f"Error creating keypair: {e}")


if __name__ == "__main__":
    asyncio.run(main())