"""
Drift-specific authentication implementation.
Handles authentication for the Drift exchange using Solana wallet integration.
"""

import logging
import os
from typing import Optional, Dict, Any

from src.core.models import ExchangeCredentials
from src.core.exceptions import AuthError
from .client import DriftClient

logger = logging.getLogger(__name__)

class DriftAuth:
    """Authentication handler for Drift exchange."""
    
    def __init__(
        self,
        credentials: Optional[ExchangeCredentials] = None,
        network: str = "devnet",
        keypair_path: Optional[str] = None
    ):
        """Initialize Drift authentication.
        
        Args:
            credentials: Optional exchange credentials
            network: Network to connect to ("devnet" or "mainnet")
            keypair_path: Optional path to keypair file
        """
        self.credentials = credentials
        self.network = network
        self.keypair_path = keypair_path
        self.client: Optional[DriftClient] = None
        self.authenticated = False
        
        # Initialize if credentials provided
        if self.credentials:
            self._init_from_credentials()
    
    def _init_from_credentials(self) -> None:
        """Initialize from provided credentials."""
        if not self.credentials:
            return
            
        # Extract additional parameters if available
        if hasattr(self.credentials, 'additional_params') and self.credentials.additional_params:
            params = self.credentials.additional_params
            
            # Update network if provided
            if "network" in params:
                self.network = params["network"]
                
            # Update keypair path if provided
            if "keypair_path" in params:
                self.keypair_path = params["keypair_path"]
    
    async def authenticate(self) -> bool:
        """Authenticate with Drift.
        
        Returns:
            True if authentication successful
        """
        try:
            # Initialize client
            self.client = DriftClient(
                network=self.network,
                keypair_path=self.keypair_path
            )
            
            # Initialize connection
            await self.client.initialize()
            
            self.authenticated = True
            logger.info("Successfully authenticated with Drift")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            raise AuthError(f"Failed to authenticate: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if authenticated.
        
        Returns:
            True if authenticated
        """
        return self.authenticated and self.client is not None and self.client.initialized
    
    def get_client(self) -> Optional[DriftClient]:
        """Get the authenticated Drift client.
        
        Returns:
            Authenticated DriftClient instance or None
        """
        if not self.is_authenticated():
            return None
        return self.client
    
    async def cleanup(self) -> None:
        """Cleanup authentication resources."""
        if self.client:
            await self.client.cleanup()
            self.client = None
        self.authenticated = False