"""
Solana wallet interface for trading on Solana-based DEXs.
Handles keypair loading, transaction signing, etc.
"""

import os
import logging
from typing import Optional, Dict, List, Tuple
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from src.utils.wallet.sol_rpc import get_solana_client, get_network, NETWORK_URLS
from solana.rpc.async_api import AsyncClient
from dotenv import load_dotenv
from src.utils.wallet.encryption import WalletEncryption

logger = logging.getLogger(__name__)
load_dotenv()  # Load environment variables from .env

class SolanaWallet:
    """
    Represents a Solana wallet with keypair management and balance checking.
    """
    
    WALLET_ENV_VARS = [
        "PRIVATE_KEY_PATH",  # Default wallet
        "KP_PATH",          # KP_TRADE wallet
        "AG_PATH",          # AG_TRADE wallet
        "DRIFT_PRIVATE_KEY_PATH"  # DRIFT wallet
    ]

    def __init__(self, keypair_path: str, name: str = None, keypair: List[int] = None, is_main: bool = False):
        """
        Initialize a Solana wallet
        
        Args:
            keypair_path: Path to the keypair file
            name: Optional name for the wallet
            keypair: Optional keypair bytes if already loaded
            is_main: Whether this is the main wallet
        """
        self.keypair_path = keypair_path
        self.name = name or os.path.splitext(os.path.basename(keypair_path))[0].upper()
        self.is_main = is_main
        self.keypair = None
        self.pubkey = None
        self.client = None
        
        if keypair:
            self.keypair = bytes(keypair)
            self.pubkey = Keypair.from_bytes(self.keypair).pubkey()
        else:
            self.load_keypair()

    async def init_client(self):
        """Initialize the Solana client if not already initialized"""
        if not self.client:
            self.client = await get_solana_client()
            version = await self.client.get_version()
            logger.info(f"Connected Solana node version: {version}")

    def _resolve_keypair_path(self, keypair_path: Optional[str] = None) -> Optional[str]:
        """
        Resolve keypair path from input or environment variables
        
        Args:
            keypair_path: Explicitly provided keypair path
            
        Returns:
            Resolved keypair path or None if not found
        """
        # First try explicitly provided path
        if keypair_path and os.path.exists(keypair_path):
            return keypair_path
            
        # Then try environment variables in order
        for env_var in self.WALLET_ENV_VARS:
            path = os.getenv(env_var)
            if path and os.path.exists(path):
                logger.info(f"Using wallet path from {env_var}: {path}")
                return path
                
        logger.warning("No valid wallet path found in environment variables")
        return None

    @staticmethod
    def list_available_wallets() -> List[Dict[str, str]]:
        """
        List all available wallets from environment variables
        
        Returns:
            List of dicts with wallet info (env_var, path, exists)
        """
        wallets = []
        for env_var in SolanaWallet.WALLET_ENV_VARS:
            path = os.getenv(env_var)
            if path:
                exists = os.path.exists(path)
                wallets.append({
                    "env_var": env_var,
                    "path": path,
                    "exists": exists
                })
        return wallets

    def load_keypair(self):
        """Load keypair from file"""
        try:
            logger.info(f"Attempting to load keypair for {self.name} from {self.keypair_path}")
            if not os.path.exists(self.keypair_path):
                raise FileNotFoundError(f"Keypair file not found: {self.keypair_path}")
            
            # Get password from environment
            password = os.getenv("WALLET_PASSWORD")
            if not password:
                raise ValueError("WALLET_PASSWORD not set in environment")
            
            # Read and decrypt the keypair file
            encryption = WalletEncryption(password)
            with open(self.keypair_path, 'rb') as f:
                encrypted_data = f.read()
                logger.info(f"Read {len(encrypted_data)} bytes from {self.keypair_path}")
                keypair_data = encryption.decrypt_wallet_config(encrypted_data)
            
            # Handle both list and dict formats
            if isinstance(keypair_data, dict):
                logger.info(f"Keypair data is a dict with keys: {list(keypair_data.keys())}")
                keypair_data = keypair_data.get('keypair', [])
            else:
                logger.info(f"Keypair data is a {type(keypair_data)}")
            
            # Create keypair from decrypted data
            self.keypair = bytes(keypair_data)
            self.pubkey = Keypair.from_bytes(self.keypair).pubkey()
            logger.info(f"Successfully loaded keypair for {self.name} with pubkey {self.pubkey}")
            
        except Exception as e:
            logger.error(f"Failed to read keypair file {self.keypair_path}: {e}")
            raise

    def get_public_key(self) -> Optional[str]:
        """
        Get the wallet's public key
        
        Returns:
            str: Base58 encoded public key or None if not loaded
        """
        return str(self.pubkey) if self.pubkey else None

    async def get_balance(self) -> Optional[float]:
        """
        Get the wallet's SOL balance
        
        Returns:
            float: Balance in SOL or None if error
        """
        try:
            # Initialize client if needed
            await self.init_client()
            
            # Get balance
            rpc_url = NETWORK_URLS[get_network()]
            client = AsyncClient(rpc_url)
            balance = await client.get_balance(self.pubkey)
            return balance.value / 1e9  # Convert lamports to SOL
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return None

    def get_token_balance(self, token_address: str) -> Optional[int]:
        """
        Get balance of a specific token
        
        Args:
            token_address: Token mint address
            
        Returns:
            int: Token balance or None if error
        """
        try:
            # Get RPC endpoint from environment
            rpc_url = NETWORK_URLS[get_network()]
            client = AsyncClient(rpc_url)
            
            # Get token account
            response = client.get_token_accounts_by_owner(
                self.pubkey,
                TokenAccountOpts(mint=Pubkey.from_string(token_address))
            )
            
            if not response.value:
                return 0
                
            # Get balance of first account
            account = response.value[0]
            balance = int(account.account.data.parsed['info']['tokenAmount']['amount'])
            return balance
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return None

    def transfer(self, to_pubkey: str, amount: float) -> bool:
        """
        Transfer SOL to another address
        
        Args:
            to_pubkey: Destination public key
            amount: Amount of SOL to transfer
            
        Returns:
            bool: True if transfer was successful
        """
        try:
            # Get RPC endpoint from environment
            rpc_url = NETWORK_URLS[get_network()]
            client = AsyncClient(rpc_url)
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=self.pubkey,
                    to_pubkey=Pubkey.from_string(to_pubkey),
                    lamports=int(amount * 1e9)
                )
            )
            
            # Create and sign transaction
            keypair = Keypair.from_bytes(self.keypair)
            transaction = Transaction().add(transfer_ix)
            
            # Send transaction
            result = client.send_transaction(transaction, keypair)
            logger.info(f"Transfer successful: {result.value}")
            return True
            
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return False

    async def sign_transaction(self, transaction_data: Dict) -> Dict:
        """
        Sign a transaction
        
        Args:
            transaction_data: Transaction data as dictionary
            
        Returns:
            dict: Signed transaction data
        """
        # Convert transaction data to Transaction object
        transaction = Transaction.from_bytes(bytes(transaction_data))
        signed_tx = transaction.sign([Keypair.from_bytes(self.keypair)])
        
        return {
            'transaction': bytes(signed_tx),
            'signature': str(signed_tx.signatures[0])
        }
    
    def sign_message(self, message: str) -> str:
        """
        Sign a message
        
        Args:
            message: Message to sign
            
        Returns:
            str: Base64 encoded signature
        """
        if isinstance(message, str):
            message = message.encode('utf-8')
            
        signature = Keypair.from_bytes(self.keypair).sign_message(message)
        return base64.b64encode(bytes(signature)).decode('utf-8')
    
    @staticmethod
    def create_new_keypair(output_path: str) -> Tuple[str, str]:
        """
        Create a new Solana keypair and save to file
        
        Args:
            output_path: Path to save the keypair
            
        Returns:
            Tuple of (public_key, private_key)
        """
        # Generate new keypair
        keypair = Keypair()
        
        # Save keypair to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(list(bytes(keypair)), f)
            
        return (str(keypair.pubkey()), base58.b58encode(bytes(keypair)).decode('utf-8'))

async def get_wallet(keypair_path: Optional[str] = None) -> SolanaWallet:
    """
    Get a Solana wallet instance.
    
    Args:
        keypair_path: Optional path to keypair file. If not provided, will try env vars in order:
                     PRIVATE_KEY_PATH (default wallet)
                     KP_PATH (KP trading wallet)
                     AG_PATH (AG trading wallet)
        
    Returns:
        SolanaWallet instance
    """
    wallet = SolanaWallet(keypair_path)
    await wallet.init_client()
    return wallet