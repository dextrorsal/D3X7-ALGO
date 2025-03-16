"""
sol_rpc.py

This module establishes a connection to the Solana network using the Helius RPC endpoint.
It loads environment variables using python-dotenv, retrieves the HELIUS_RPC_ENDPOINT,
and creates a Solana Client object.

Located in: src.utils.solana
"""

import os
from solana.rpc.api import Client
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def get_solana_client() -> Client:
    """
    Loads the Helius RPC endpoint from the .env file and returns a Solana Client.
    
    Raises:
        ValueError: if the HELIUS_RPC_ENDPOINT is not set in the environment.
        
    Returns:
        Client: An instance of solana.rpc.api.Client connected to the Helius RPC.
    """
    load_dotenv()  # Load environment variables from .env file in the project root

    helius_rpc = os.getenv("HELIUS_RPC_ENDPOINT")
    if not helius_rpc:
        error_msg = "HELIUS_RPC_ENDPOINT is not set in the .env file"
        logger.error(error_msg)
        raise ValueError(error_msg)

    client = Client(helius_rpc)
    # Instead of using client.url, log the endpoint directly.
    logger.info(f"Connected to Solana via Helius RPC: {helius_rpc}")
    return client

if __name__ == "__main__":
    try:
        client = get_solana_client()
        version = client.get_version()
        print("Solana Node Version:", version)
    except Exception as e:
        print("Error establishing connection:", e)
