#!/usr/bin/env python3
"""
Devnet Adapter for Testing
Combines Drift and Jupiter testing functionality for devnet environment
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate

from anchorpy.provider import Provider, Wallet
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.types import TxParams

from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_solana_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token configuration for Devnet
TOKEN_INFO = {
    "SOL": {
        "mint": "So11111111111111111111111111111111111111112",
        "decimals": 9,
        "symbol": "SOL"
    },
    "USDC": {
        "mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # Devnet USDC
        "decimals": 6,
        "symbol": "USDC"
    },
    "TEST": {
        "mint": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Devnet test token
        "decimals": 9,
        "symbol": "TEST"
    }
}

class DevnetAdapter:
    """
    Unified adapter for devnet testing of Drift and Jupiter functionality
    """
    
    def __init__(self):
        # Load and validate environment variables
        self.rpc_endpoint = os.getenv('DEVNET_RPC_ENDPOINT')
        if not self.rpc_endpoint:
            raise EnvironmentError("DEVNET_RPC_ENDPOINT environment variable not set")
            
        # Initialize components
        self.wallet_manager = WalletManager()
        self.solana_client = None
        self.drift_client = None
        
        # Default transaction parameters
        self.tx_params = TxParams(
            compute_units_price=85_000,
            compute_units=1_400_000
        )
        
        logger.info("DevnetAdapter initialized")
        
    async def connect(self) -> None:
        """Initialize Solana client connection"""
        try:
            self.solana_client = await get_solana_client("devnet")
            version = await self.solana_client.get_version()
            logger.info(f"Connected to devnet RPC (version {version.version})")
        except Exception as e:
            logger.error(f"Failed to connect to devnet: {str(e)}")
            raise
            
    async def initialize_drift(self, tx_params: Optional[TxParams] = None) -> None:
        """
        Initialize Drift client with devnet configuration
        
        Args:
            tx_params: Optional transaction parameters override
        """
        try:
            # Load wallet using WalletManager
            wallet = self.wallet_manager.get_wallet("MAIN")
            if not wallet:
                raise Exception("Failed to load MAIN wallet")
                
            # Get keypair from wallet
            if hasattr(wallet, 'keypair') and wallet.keypair:
                if isinstance(wallet.keypair, bytes):
                    keypair = Keypair.from_bytes(wallet.keypair)
                else:
                    keypair = wallet.keypair
            else:
                raise Exception("No keypair available in wallet")
                
            logger.info(f"Loaded wallet: {keypair.pubkey()}")
            
            # Ensure Solana client is connected
            if not self.solana_client:
                await self.connect()
                
            # Use provided tx_params or default
            tx_params = tx_params or self.tx_params
                
            logger.info("Initializing Drift client on devnet...")
            self.drift_client = DriftClient(
                self.solana_client,
                Wallet(keypair),
                env="devnet",
                tx_params=tx_params,
                account_subscription=AccountSubscriptionConfig("websocket")
            )
            
            # Add users after client initialization
            for subaccount_id in range(5):
                try:
                    await self.drift_client.add_user(subaccount_id)
                    logger.info(f"Added subaccount {subaccount_id} to client")
                except Exception as e:
                    logger.warning(f"Could not add subaccount {subaccount_id}: {str(e)}")
            
            logger.info("Drift client initialized successfully on devnet")
            
        except Exception as e:
            logger.error(f"Error initializing Drift client: {str(e)}")
            raise
            
    async def get_drift_user_info(self) -> Dict[str, Any]:
        """
        Get comprehensive Drift user account information
        
        Returns:
            Dictionary containing user account details
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized. Call initialize_drift() first")
            
        try:
            drift_user = self.drift_client.get_user()
            user = drift_user.get_user_account()
            
            # Get collateral info
            spot_collateral = drift_user.get_spot_market_asset_value(
                None,
                include_open_orders=True,
            )
            
            # Get PnL and collateral info
            unrealized_pnl = drift_user.get_unrealized_pnl(False)
            total_collateral = drift_user.get_total_collateral()
            
            info = {
                "spot_collateral": spot_collateral / QUOTE_PRECISION,
                "unrealized_pnl": unrealized_pnl / QUOTE_PRECISION,
                "total_collateral": total_collateral / QUOTE_PRECISION,
                "authority": str(user.authority),
                "subaccount_id": user.sub_account_id,
                "is_margin_trading_enabled": user.is_margin_trading_enabled,
                "next_order_id": user.next_order_id
            }
            
            # Display info in a nice format
            print("\n=== Drift User Account Info ===")
            print(tabulate([
                ["Spot Collateral", f"${info['spot_collateral']:,.2f}"],
                ["Unrealized PnL", f"${info['unrealized_pnl']:,.2f}"],
                ["Total Collateral", f"${info['total_collateral']:,.2f}"],
                ["Subaccount ID", info['subaccount_id']],
                ["Margin Trading", "✓" if info['is_margin_trading_enabled'] else "✗"]
            ], tablefmt="simple"))
            
            return info
            
        except Exception as e:
            logger.error(f"Error fetching Drift user info: {str(e)}")
            raise
            
    async def check_token_balances(self, wallet_address: Optional[str] = None) -> None:
        """
        Check token balances for a wallet on devnet
        
        Args:
            wallet_address: Optional wallet address to check. If not provided,
                          uses the default wallet from WalletManager
        """
        try:
            if not self.solana_client:
                await self.connect()
                
            # Get wallet address
            if wallet_address:
                wallet_pubkey = Pubkey.from_string(wallet_address)
            else:
                wallet = self.wallet_manager.get_wallet("MAIN")
                if not wallet:
                    raise Exception("No wallet available")
                wallet_pubkey = wallet.pubkey
                
            print("\nToken Balances (DEVNET)")
            print("=======================")
            print(f"Wallet Address: {wallet_pubkey}")
            
            # Get SOL balance
            sol_response = await self.solana_client.get_balance(wallet_pubkey, commitment=Confirmed)
            sol_balance = sol_response.value / 10**TOKEN_INFO['SOL']['decimals']
            
            # Get all token balances
            balances = []
            for token, info in TOKEN_INFO.items():
                if token == "SOL":
                    balance = sol_balance
                else:
                    balance = await self.get_token_balance(wallet_pubkey, info)
                    
                if balance > 0:
                    balances.append([
                        token,
                        f"{balance:.6f}",
                        info['symbol'],
                        info['mint'][:8] + "..." + info['mint'][-8:]
                    ])
                    
            # Display balances in a table
            print("\nToken Balances:")
            print(tabulate(
                balances,
                headers=['Token', 'Amount', 'Symbol', 'Mint Address'],
                tablefmt='simple'
            ))
            
            print(f"\nNote: This is checking balances on devnet!")
            print("Use 'solana airdrop 1' to get some devnet SOL if needed.")
            
        except Exception as e:
            logger.error(f"Error checking token balances: {str(e)}")
            raise
            
    async def get_token_balance(self, wallet_pubkey: Pubkey, token_info: Dict) -> float:
        """
        Get balance for a specific token
        
        Args:
            wallet_pubkey: Wallet public key
            token_info: Token information dictionary
            
        Returns:
            Token balance as float
        """
        try:
            response = await self.solana_client.get_token_accounts_by_owner_json_parsed(
                wallet_pubkey,
                {'mint': token_info['mint']}
            )
            
            total_balance = 0
            if response.value:
                for account in response.value:
                    try:
                        parsed_info = account.account.data.parsed['info']
                        if 'tokenAmount' in parsed_info:
                            amount = float(parsed_info['tokenAmount']['uiAmount'] or 0)
                            total_balance += amount
                    except (KeyError, TypeError, ValueError) as e:
                        logger.debug(f"Error parsing token amount: {str(e)}")
                        continue
                        
            return total_balance
            
        except Exception as e:
            logger.debug(f"Error getting token balance: {str(e)}")
            return 0
            
    async def close(self) -> None:
        """Clean up resources"""
        if self.drift_client:
            try:
                await self.drift_client.unsubscribe()
                logger.info("Drift client closed")
            except Exception as e:
                logger.error(f"Error closing Drift client: {str(e)}")
                
        if self.solana_client:
            try:
                await self.solana_client.close()
                logger.info("Solana client closed")
            except Exception as e:
                logger.error(f"Error closing Solana client: {str(e)}")

async def main():
    """Example usage of DevnetAdapter"""
    adapter = DevnetAdapter()
    
    try:
        # Initialize and check token balances
        await adapter.check_token_balances()
        
        # Initialize Drift and check user info
        await adapter.initialize_drift()
        await adapter.get_drift_user_info()
        
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main()) 