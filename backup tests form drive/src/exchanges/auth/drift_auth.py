"""
Drift-specific authentication implementation.
Handles authentication for the Drift exchange using Solana wallet integration.
"""

import logging
import time
import json
import os
from typing import Dict, Optional, Any, Union
import base58
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.types import TxParams
from anchorpy import Provider, Wallet
from solana.rpc.commitment import Confirmed
from solana.rpc.websocket_api import connect

from src.core.models import ExchangeCredentials
from src.core.exceptions import AuthError
from .base_auth import BaseAuth

logger = logging.getLogger(__name__)


class DriftAuth(BaseAuth):
    """
    Authentication handler for Drift exchange.
    
    This class implements the BaseAuth interface for Drift exchange,
    providing authentication using Solana wallet integration.
    """
    
    def __init__(self, credentials: Optional[ExchangeCredentials] = None, rpc_url=None, program_id=None):
        """
        Initialize the Drift authentication handler.
        
        Args:
            credentials: Drift API credentials
            rpc_url: Solana RPC URL
            program_id: Drift program ID
        """
        super().__init__(credentials)
        self._client = None
        self._wallet = None
        self._provider = None
        self._connection = None
        self._program_id = program_id or os.getenv('DRIFT_PROGRAM_ID')
        
        # Set RPC URL based on environment
        if "devnet" in (self._program_id or "").lower():
            self._rpc_url = os.getenv("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
        else:
            self._rpc_url = rpc_url or os.getenv('MAINNET_RPC_ENDPOINT') or os.getenv('DRIFT_RPC_URL') or 'https://api.devnet.solana.com'
        
        logger.info(f"Using RPC URL: {self._rpc_url}")
        
        # Initialize if credentials are provided
        if self.credentials:
            self._init_from_credentials()
    
    def _init_from_credentials(self) -> None:
        """Initialize wallet and connection from credentials."""
        if not self.credentials:
            return
            
        # Extract additional parameters if available
        if hasattr(self.credentials, 'additional_params') and self.credentials.additional_params:
            additional_params = self.credentials.additional_params
            
            # Get program ID and RPC URL if provided
            self._program_id = additional_params.get("program_id", self._program_id)
            
            # Use devnet RPC URL if program ID indicates devnet
            if "devnet" in (self._program_id or "").lower():
                self._rpc_url = os.getenv("DEVNET_RPC_ENDPOINT", "https://api.devnet.solana.com")
            else:
                self._rpc_url = additional_params.get("rpc_url", self._rpc_url)
            
            # Initialize wallet from private key if provided
            if "private_key" in additional_params:
                try:
                    private_key = additional_params["private_key"]
                    # Handle different private key formats
                    if isinstance(private_key, str):
                        if private_key.startswith("["):  # JSON array format
                            private_key = json.loads(private_key)
                        else:  # Base58 encoded format
                            private_key = base58.b58decode(private_key)
                            
                    # Create keypair from private key
                    self._wallet = Keypair.from_bytes(bytes(private_key))
                    logger.info("Successfully initialized wallet from private key")
                except Exception as e:
                    logger.error(f"Failed to initialize wallet from private key: {e}")
                    raise AuthError(f"Invalid private key format: {e}")
    
    async def initialize_wallet(self, private_key_path=None):
        """Initialize wallet from private key file."""
        try:
            if private_key_path is None:
                private_key_path = os.getenv('DRIFT_PRIVATE_KEY_PATH')
            
            if not private_key_path:
                raise ValueError("Private key path not provided")

            with open(private_key_path, 'r') as f:
                private_key = json.load(f)
                self._wallet = Keypair.from_secret_key(bytes(private_key))
                logger.info("Wallet initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize wallet: {str(e)}")
            return False

    async def initialize_client(self) -> DriftClient:
        """
        Initialize the Drift client with the configured wallet.
        
        Returns:
            Initialized DriftClient instance
        
        Raises:
            AuthError: If client initialization fails
        """
        if not self.is_authenticated():
            raise AuthError("Cannot initialize client without valid credentials")
            
        try:
            # Initialize connection if not already done
            if not self._connection:
                self._connection = AsyncClient(
                    self._rpc_url,
                    commitment=Confirmed
                )
                
            # Create provider with wallet
            self._provider = Provider(
                connection=self._connection,
                wallet=Wallet(self._wallet),
                opts={"commitment": "processed"}
            )

            # Set transaction parameters
            tx_params = TxParams(
                compute_units_price=None,  # Let Solana determine price
                compute_units=None,  # Let Solana determine units
            )

            # Initialize Drift client with configs
            self._client = DriftClient(
                connection=self._connection,
                wallet=Wallet(self._wallet),
                env="devnet" if "devnet" in self._rpc_url else "mainnet"
            )
            
            # Initialize markets and user account
            await self._client.subscribe()
            await self._client.add_user(0)  # Add user with subaccount 0
            
            logger.info("Successfully initialized Drift client")
            return self._client
            
        except Exception as e:
            logger.error(f"Failed to initialize Drift client: {e}")
            raise AuthError(f"Failed to initialize Drift client: {e}")
    
    def get_auth_headers(self, method: str, endpoint: str, 
                         params: Optional[Dict] = None, 
                         data: Optional[Dict] = None) -> Dict[str, str]:
        """
        Generate authentication headers for a Drift API request.
        
        Note: Drift uses wallet-based authentication through the SDK rather than
        traditional API key/secret authentication with headers. This method
        returns an empty dictionary as headers are not used for authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            Empty dictionary (Drift uses wallet-based auth)
        """
        # Drift uses wallet-based authentication through the SDK
        # rather than traditional API key/secret authentication with headers
        return {}
    
    def is_authenticated(self) -> bool:
        """
        Check if the authentication handler has valid credentials.
        
        Returns:
            True if authenticated with a valid wallet, False otherwise
        """
        return self._wallet is not None
    
    def get_wallet(self) -> Optional[Keypair]:
        """
        Get the Solana wallet keypair.
        
        Returns:
            Solana wallet keypair or None if not initialized
        """
        return self._wallet
    
    def get_program_id(self) -> str:
        """
        Get the Drift program ID.
        
        Returns:
            Drift program ID
        """
        return self._program_id
    
    def get_rpc_url(self) -> str:
        """
        Get the Solana RPC URL.
        
        Returns:
            Solana RPC URL
        """
        return self._rpc_url
    
    async def close(self) -> None:
        """Close any open connections."""
        if self._client:
            try:
                await self._client.unsubscribe()
                logger.info("Drift client closed successfully")
            except Exception as e:
                logger.error(f"Error closing Drift client: {e}")
                
        if self._connection:
            await self._connection.close()
            self._connection = None