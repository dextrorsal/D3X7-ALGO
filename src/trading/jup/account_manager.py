"""
Jupiter Account Manager
Handles account-related operations for Jupiter DEX integration
"""

import logging
import asyncio
from typing import Dict, Optional, List
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from src.utils.wallet.sol_rpc import get_solana_client
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from spl.token.constants import TOKEN_PROGRAM_ID
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class JupiterAccountManager:
    """
    Manages Jupiter account operations and token balances
    """
    
    # Token mint addresses (as per Jupiter docs)
    TOKEN_MINTS = {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "BTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
        "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"
    }
    
    # Token decimals
    TOKEN_DECIMALS = {
        "SOL": 9,
        "USDC": 6,
        "BTC": 8,
        "ETH": 8
    }

    def __init__(self, keypair_path: str = None):
        """
        Initialize Jupiter account manager
        
        Args:
            keypair_path: Path to Solana keypair file (optional, will use PRIVATE_KEY_PATH from env if not provided)
        """
        # Use provided keypair_path or fall back to environment variable
        self.keypair_path = keypair_path or os.getenv('PRIVATE_KEY_PATH')
        if not self.keypair_path:
            raise ValueError("No keypair path provided and PRIVATE_KEY_PATH not found in environment")
            
        self.wallet = None
        self.client = get_solana_client()
        
        # Transaction history storage
        self.history_path = Path("data/jup_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.transaction_history = self._load_transaction_history()
        
        logger.info("Initialized Jupiter Account Manager")

    def _load_transaction_history(self) -> List[Dict]:
        """Load transaction history from file"""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not load transaction history, starting fresh")
                return []
        return []

    def _save_transaction_history(self):
        """Save transaction history to file"""
        with open(self.history_path, 'w') as f:
            json.dump(self.transaction_history, f, indent=2)

    async def connect(self) -> bool:
        """
        Connect and load wallet
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.keypair_path):
                raise ValueError(f"Keypair file not found at: {self.keypair_path}")
                
            # Load keypair
            try:
                logger.info(f"Loading keypair from {self.keypair_path}")
                with open(self.keypair_path, 'r') as f:
                    keypair_json = json.load(f)
                    # Convert JSON array to bytes
                    keypair_bytes = bytes(keypair_json)
                    self.wallet = Keypair.from_bytes(keypair_bytes)
            except json.JSONDecodeError:
                logger.info("Keypair file is not in JSON format, trying raw bytes...")
                with open(self.keypair_path, 'rb') as f:
                    keypair_bytes = f.read()
                    self.wallet = Keypair.from_bytes(keypair_bytes)
                    
            logger.info(f"Connected with wallet: {self.wallet.pubkey}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def get_token_balance(self, token: str) -> float:
        """
        Get balance for a specific token
        
        Args:
            token: Token symbol (e.g., "SOL", "USDC")
            
        Returns:
            Token balance in human-readable format
        """
        if token not in self.TOKEN_MINTS:
            raise ValueError(f"Unsupported token: {token}")
            
        try:
            if token == "SOL":
                # Get native SOL balance
                response = await self.client.get_balance(str(self.wallet.public_key), commitment=Confirmed)
                balance = response['result']['value'] / 10**self.TOKEN_DECIMALS[token]
            else:
                # Get SPL token balance
                token_accounts = await self.client.get_token_accounts_by_owner(
                    str(self.wallet.public_key),
                    {'mint': self.TOKEN_MINTS[token]},
                    commitment=Confirmed
                )
                
                balance = 0
                for account in token_accounts['result']['value']:
                    data = account['account']['data']['parsed']['info']
                    balance += int(data['tokenAmount']['amount']) / 10**self.TOKEN_DECIMALS[token]
                    
            return balance
            
        except Exception as e:
            logger.error(f"Error getting {token} balance: {str(e)}")
            return 0.0

    async def get_all_balances(self) -> Dict[str, float]:
        """
        Get balances for all supported tokens
        
        Returns:
            Dictionary of token balances
        """
        if not self.wallet:
            await self.connect()
            
        balances = {}
        for token in self.TOKEN_MINTS.keys():
            balance = await self.get_token_balance(token)
            if balance > 0:
                balances[token] = balance
        return balances

    async def get_account_value_usdc(self) -> float:
        """
        Get total account value in USDC
        
        Returns:
            Total account value in USDC
        """
        from src.trading.jup.jup_adapter import JupiterAdapter
        
        if not self.wallet:
            await self.connect()
            
        balances = await self.get_all_balances()
        adapter = JupiterAdapter(keypair_path=self.keypair_path)
        await adapter.connect()
        
        total_value = 0.0
        
        for token, balance in balances.items():
            if token == "USDC":
                total_value += balance
            else:
                try:
                    price = await adapter.get_market_price(f"{token}-USDC")
                    value = balance * price
                    total_value += value
                except Exception as e:
                    logger.warning(f"Could not get price for {token}: {e}")
                    
        return total_value

    def record_transaction(self, transaction_data: Dict):
        """
        Record a transaction in history
        
        Args:
            transaction_data: Transaction details including signature, type, amounts, etc.
        """
        transaction_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.transaction_history.append(transaction_data)
        self._save_transaction_history()

    async def get_transaction_history(self, 
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Get transaction history with optional time filtering
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of transaction records
        """
        history = self.transaction_history
        
        if start_time:
            history = [tx for tx in history 
                      if datetime.fromisoformat(tx['timestamp']) >= start_time]
            
        if end_time:
            history = [tx for tx in history 
                      if datetime.fromisoformat(tx['timestamp']) <= end_time]
            
        return history

    async def print_account_summary(self):
        """Print a detailed account summary"""
        if not self.wallet:
            await self.connect()
            
        print("\nJupiter Account Summary")
        print("=======================")
        
        # Get wallet address
        print(f"Wallet Address: {self.wallet.public_key}")
        
        # Get token balances
        print("\nToken Balances:")
        balances = await self.get_all_balances()
        for token, balance in balances.items():
            print(f"{token}: {balance:.6f}")
            
        # Get total value
        total_value = await self.get_account_value_usdc()
        print(f"\nTotal Account Value: ${total_value:.2f} USDC")
        
        # Print recent transactions
        print("\nRecent Transactions:")
        recent_txs = await self.get_transaction_history()[-5:]  # Last 5 transactions
        for tx in recent_txs:
            print(f"- {tx['timestamp']}: {tx['type']} - {tx.get('status', 'unknown')}")
            print(f"  Signature: {tx.get('signature', 'N/A')}")