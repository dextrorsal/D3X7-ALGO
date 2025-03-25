"""
Drift-specific authentication implementation.
Handles authentication for the Drift exchange using Solana wallet integration.
"""

import logging
from typing import Optional, Dict, Any

from src.core.models import ExchangeCredentials
from src.core.exceptions import AuthError
from src.utils.wallet.wallet_manager import WalletManager

logger = logging.getLogger(__name__)

class DriftAuth:
    """Authentication handler for Drift exchange."""
    
    def __init__(
        self,
        wallet_manager: WalletManager,
        network: str = "mainnet",
    ):
        """Initialize Drift authentication.
        
        Args:
            wallet_manager: Wallet manager instance for Solana wallet operations
            network: Network to connect to ("devnet" or "mainnet")
        """
        self.wallet_manager = wallet_manager
        self.network = network
        self.authenticated = False
        self.wallet = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Drift.
        
        Returns:
            True if authentication successful
        """
        try:
            # Get the main wallet
            self.wallet = self.wallet_manager.get_wallet("MAIN")
            if not self.wallet:
                raise AuthError("No MAIN wallet found in wallet manager")
            
            self.authenticated = True
            logger.info(f"Successfully authenticated with Drift using wallet {self.wallet.pubkey}")
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
        return self.authenticated and self.wallet is not None
    
    def get_wallet(self):
        """Get the authenticated wallet.
        
        Returns:
            Authenticated wallet instance or None
        """
        if not self.is_authenticated():
            return None
        return self.wallet
    
    async def cleanup(self) -> None:
        """Cleanup authentication resources."""
        self.wallet = None
        self.authenticated = False