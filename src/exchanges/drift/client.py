"""
Core Drift client implementation.
"""

import os
import logging
import json
from typing import Optional, Dict, Any, Union, List
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from anchorpy import Wallet, Provider
from driftpy.drift_client import DriftClient as DriftPyClient
from driftpy.types import TxParams
from driftpy.constants.perp_markets import (
    mainnet_perp_market_configs,
    devnet_perp_market_configs,
)
from websockets.exceptions import InvalidStatusCode, WebSocketException

from src.core.exceptions import ExchangeError, NotInitializedError
from src.utils.wallet.sol_wallet import SolanaWallet

logger = logging.getLogger(__name__)


class DriftClient:
    """
    Core Drift client for interacting with the Drift protocol.
    Handles client initialization, connection management, and market lookups.
    """

    def __init__(
        self, wallet: Union[SolanaWallet, str], network: str = "mainnet", config=None
    ):
        """Initialize the Drift client.

        Args:
            wallet: Either a SolanaWallet instance or a keypair path string
            network: Network to connect to ("devnet" or "mainnet")
            config: Additional configuration for devnet/mainnet settings
        """
        load_dotenv()
        self.network = network.lower()
        self.config = config

        # Handle wallet input
        if isinstance(wallet, str):
            self.keypair_path = wallet
            self.wallet = None
        else:
            self.wallet = wallet
            self.keypair_path = None

        # Get RPC URL with fallback options
        self.rpc_url = self._get_rpc_url()

        self.client: Optional[DriftPyClient] = None
        self.connection: Optional[AsyncClient] = None
        self.keypair: Optional[Keypair] = None

        # Market lookup tables
        self.market_configs = (
            mainnet_perp_market_configs
            if network == "mainnet"
            else devnet_perp_market_configs
        )
        self.market_name_lookup: Dict[str, int] = {}
        self.market_index_lookup: Dict[int, str] = {}

        # Initialize market lookups
        for market in self.market_configs:
            # Store both with and without -PERP suffix for flexibility
            base_symbol = market.symbol.replace("-PERP", "")
            self.market_name_lookup[base_symbol] = market.market_index
            self.market_name_lookup[f"{base_symbol}-PERP"] = market.market_index
            self.market_index_lookup[market.market_index] = f"{base_symbol}-PERP"

        logger.info(
            f"Available markets in {network}: {list(self.market_name_lookup.keys())}"
        )

        self.initialized = False

    def _get_rpc_url(self) -> str:
        """Get RPC URL with fallbacks and logging."""
        if self.network == "mainnet":
            rpc_urls = [
                os.getenv("HELIUS_RPC_ENDPOINT"),
                os.getenv("MAINNET_RPC_ENDPOINT"),
                "https://api.mainnet-beta.solana.com",
            ]
        else:
            rpc_urls = [
                os.getenv("DEVNET_RPC_ENDPOINT"),
                "https://api.devnet.solana.com",
            ]
        for url in rpc_urls:
            if url:
                logger.info(f"Attempting Solana RPC endpoint: {url}")
                # Optionally, here you could add a test connection or rate-limit check
                return url
        logger.warning(
            "No valid Solana RPC endpoint found, using default public endpoint."
        )
        return (
            "https://api.mainnet-beta.solana.com"
            if self.network == "mainnet"
            else "https://api.devnet.solana.com"
        )

    async def _connect_with_retry(
        self, max_retries: int = 5, initial_delay: float = 1.0
    ) -> None:
        """Connect to the RPC endpoint with exponential backoff."""
        delay = initial_delay
        last_error = None

        for attempt in range(max_retries):
            try:
                # Initialize Solana connection
                self.connection = AsyncClient(self.rpc_url)
                logger.info(f"Connected to Solana RPC at {self.rpc_url}")

                # Initialize Drift client with transaction parameters
                tx_params = TxParams(
                    compute_units_price=85_000,  # Default from example
                    compute_units=1_400_000,  # Default from example
                )

                # Use config if provided (for devnet)
                if self.config and self.network == "devnet":
                    self.client = DriftPyClient(
                        self.connection,
                        Wallet(self.keypair),
                        self.network,
                        tx_params=tx_params,
                        market_lookup_table=self.config.market_lookup_table,
                        perp_market_indexes=[0, 1],  # Start with SOL and BTC markets
                        spot_market_indexes=[0],  # Start with SOL spot market
                    )
                else:
                    self.client = DriftPyClient(
                        self.connection,
                        Wallet(self.keypair),
                        self.network,
                        tx_params=tx_params,
                    )

                # Subscribe to market accounts
                await self.client.subscribe()

                # Initialize user account if needed
                try:
                    await self.client.initialize_user()
                    logger.info("Initialized new Drift user account")
                except Exception as e:
                    if "already in use" in str(e):
                        logger.info("User account already exists")
                    else:
                        raise e

                return  # Success

            except (InvalidStatusCode, WebSocketException) as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Connection attempt {attempt + 1} failed with {str(e)}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    raise ExchangeError(
                        f"Failed to connect to Drift: {str(last_error)}"
                    )

    async def initialize(self) -> None:
        """Initialize the Drift client connection."""
        try:
            # Load keypair
            if self.wallet:
                # Create Keypair from wallet's bytes
                self.keypair = Keypair.from_bytes(self.wallet.keypair)
                logger.info(f"Using provided wallet with pubkey {self.wallet.pubkey}")
            else:
                if not self.keypair_path or not os.path.exists(self.keypair_path):
                    raise ExchangeError(f"Keypair not found at {self.keypair_path}")

                with open(self.keypair_path, "r") as f:
                    keypair_bytes = bytes(json.load(f))
                self.keypair = Keypair.from_bytes(keypair_bytes)
                logger.info(f"Loaded keypair from {self.keypair_path}")

            # Connect with retry
            await self._connect_with_retry()

            self.initialized = True
            logger.info("Drift client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Drift client: {e}")
            await self.cleanup()
            raise ExchangeError(f"Failed to initialize Drift client: {str(e)}")

    def get_market_index(self, market_name: str) -> Optional[int]:
        """Get market index from market name."""
        return self.market_name_lookup.get(market_name)

    def get_market_name(self, market_index: int) -> Optional[str]:
        """Get market name from market index."""
        return self.market_index_lookup.get(market_index)

    def get_markets(self) -> List[str]:
        """Get list of available markets."""
        return list(self.market_name_lookup.keys())

    async def get_position(self, market_name: str):
        try:
            market_index = self.get_market_index(market_name)
            if market_index is None:
                raise ValueError(f"Market not found: {market_name}")

            user = self.client.get_user()
            if user is None:
                raise ValueError("User account not initialized")

            position = user.get_perp_position(market_index)
            return position
        except Exception as e:
            logger.error(f"Error getting position: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Cleanup client resources."""
        if self.client:
            try:
                await self.client.unsubscribe()
            except Exception as e:
                logger.warning(f"Error unsubscribing from Drift client: {e}")

        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                logger.warning(f"Error closing Solana connection: {e}")
            self.connection = None

        self.client = None
        self.keypair = None
        self.initialized = False
