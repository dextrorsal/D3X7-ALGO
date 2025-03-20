#!/usr/bin/env python3
"""
Enhanced Drift client manager that integrates with existing infrastructure
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from anchorpy.provider import Wallet
from solders.keypair import Keypair
from driftpy.drift_client import DriftClient
from driftpy.accounts.get_accounts import get_protected_maker_mode_stats
from driftpy.math.user_status import is_user_protected_maker
from driftpy.types import TxParams
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION

from src.utils.wallet.sol_rpc import get_solana_client, get_network
from src.utils.wallet.wallet_cli import WalletCLI
from src.trading.security.security_manager import SecurityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DriftClientManager:
    """Enhanced Drift client manager with security and multi-wallet support"""
    
    def __init__(self):
        self.drift_client: Optional[DriftClient] = None
        self.wallet_cli = WalletCLI()
        self.security_manager = SecurityManager()
        self._network = get_network()
        
    async def initialize(self, 
                        wallet_name: str = "MAIN",
                        tx_params: Optional[TxParams] = None) -> DriftClient:
        """
        Initialize Drift client with enhanced security and wallet management
        
        Args:
            wallet_name: Name of the wallet to use (from wallet_cli)
            tx_params: Optional transaction parameters
            
        Returns:
            Initialized DriftClient instance
        """
        try:
            # Get wallet from WalletManager
            wallet = self.wallet_cli.wallet_manager.get_wallet(wallet_name)
            if not wallet:
                raise ValueError(f"Wallet '{wallet_name}' not found")
                
            # Load keypair
            if hasattr(wallet, 'keypair') and wallet.keypair:
                if isinstance(wallet.keypair, bytes):
                    keypair = Keypair.from_bytes(wallet.keypair)
                else:
                    keypair = wallet.keypair
            else:
                raise Exception(f"No keypair available in wallet {wallet_name}")
                    
            # Security audit
            audit_results = self.security_manager.perform_security_audit()
            for check in audit_results["checks"]:
                if check["status"] == "FAIL":
                    logger.error(f"Security check failed: {check['name']} - {check['details']}")
                    raise SecurityError(f"Security check failed: {check['name']}")
                    
            # Get RPC client for current network
            connection = await get_solana_client(self._network)
            
            # Set default tx_params if not provided
            if tx_params is None:
                tx_params = TxParams(
                    compute_units=700_000,
                    compute_units_price=10_000
                )
                
            # Initialize Drift client
            self.drift_client = DriftClient(
                connection=connection,
                wallet=Wallet(keypair),
                env=self._network,
                tx_params=tx_params
            )
            
            # Subscribe to updates
            await self.drift_client.subscribe()
            logger.info(f"Drift client initialized and subscribed on {self._network}")
            
            # Check protected maker status
            await self._check_protected_maker_status()
            
            # Update security manager activity
            self.security_manager.update_activity()
            
            return self.drift_client
            
        except Exception as e:
            logger.error(f"Error initializing Drift client: {str(e)}")
            raise
            
    async def _check_protected_maker_status(self):
        """Check and optionally enable protected maker status"""
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
            
        user = self.drift_client.get_user()
        is_protected = is_user_protected_maker(user.get_user_account())
        
        if not is_protected:
            logger.warning("User is not a protected maker")
            stats = await get_protected_maker_mode_stats(self.drift_client.program)
            
            if stats["current_users"] >= stats["max_users"]:
                logger.warning("No room for new protected makers")
                return
                
            try:
                result = await self.drift_client.update_user_protected_maker_orders(0, True)
                logger.info("Successfully enabled protected maker mode")
            except Exception as e:
                logger.error(f"Failed to enable protected maker mode: {str(e)}")
                
    async def get_user_info(self) -> Dict[str, Any]:
        """Get detailed user account information"""
        if not self.drift_client:
            raise RuntimeError("Drift client not initialized")
            
        try:
            drift_user = self.drift_client.get_user()
            user = drift_user.get_user_account()
            
            # Get collateral info
            spot_collateral = drift_user.get_spot_market_asset_value(
                None,
                include_open_orders=True
            )
            
            # Get PnL
            unrealized_pnl = drift_user.get_unrealized_pnl(False)
            
            # Get total collateral
            total_collateral = drift_user.get_total_collateral()
            
            return {
                "spot_collateral": spot_collateral / QUOTE_PRECISION,
                "unrealized_pnl": unrealized_pnl / QUOTE_PRECISION,
                "total_collateral": total_collateral / QUOTE_PRECISION,
                "account": user
            }
            
        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            raise
            
    async def cleanup(self):
        """Clean up resources and unsubscribe"""
        if self.drift_client:
            try:
                await self.drift_client.unsubscribe()
                logger.info("Successfully unsubscribed from Drift")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                
class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass 