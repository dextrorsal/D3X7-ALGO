#!/usr/bin/env python3
"""
Devnet Adapter for Testing
Combines Drift and Jupiter testing functionality for devnet environment
"""

import asyncio
import logging
import os
import json
import time
import sys
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate
from decimal import Decimal

from anchorpy.provider import Provider, Wallet
from solders.keypair import Keypair as SoldersKeypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from driftpy.types import TxParams

from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_rpc import get_solana_client
from src.trading.security.security_manager import SecurityManager

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

# Create a shim for solana.keypair
import sys
from solders.keypair import Keypair as SoldersKeypair

# Create a mock module for solana.keypair
class MockKeypairModule:
    def __init__(self):
        self.Keypair = SoldersKeypair

# Install the mock module
sys.modules['solana.keypair'] = MockKeypairModule()

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
        self.security_manager = SecurityManager()
        
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
            # Extract the version string from the RpcVersionInfo inside GetVersionResp
            logger.info(f"Connected to devnet RPC (version {str(version)})")
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
                    keypair = SoldersKeypair.from_bytes(wallet.keypair)
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
            
    async def request_airdrop(self, wallet, amount: float = 0.1) -> Dict[str, Any]:
        """
        Request a SOL airdrop for a wallet on devnet
        
        Args:
            wallet: SolanaWallet instance to receive the airdrop
            amount: Amount of SOL to request (default: 0.1)
            
        Returns:
            Dict with signature and result information
        """
        client = None
        try:
            # Create a fresh client for this operation to avoid event loop issues
            client = await get_solana_client("devnet")
                
            # Make sure wallet is a SolanaWallet instance
            if not hasattr(wallet, 'pubkey'):
                raise ValueError("Invalid wallet provided")
                
            # Request airdrop
            logger.info(f"Requesting {amount} SOL airdrop for {wallet.pubkey}")
            
            # Convert SOL to lamports
            lamports = int(amount * 1e9)
            
            # Request the airdrop
            result = await client.request_airdrop(
                wallet.pubkey,
                lamports
            )
            
            if result.value:
                signature = result.value
                logger.info(f"Airdrop requested successfully: {signature}")
                
                # Wait for confirmation
                confirmation = await client.confirm_transaction(signature)
                
                return {
                    "signature": signature,
                    "confirmed": confirmation.value,
                    "amount": amount
                }
            else:
                logger.error("Airdrop request failed: No signature returned")
                return {
                    "signature": None,
                    "confirmed": False,
                    "amount": amount,
                    "error": "Request failed"
                }
                
        except Exception as e:
            error_str = str(e)
            if "429 Too Many Requests" in error_str or "rate limit" in error_str.lower():
                logger.warning(f"Rate limited by the devnet faucet: {error_str}")
                return {
                    "signature": None,
                    "confirmed": False,
                    "amount": amount,
                    "error": "Rate limited"
                }
            else:
                logger.error(f"Error requesting airdrop: {error_str}")
                return {
                    "signature": None,
                    "confirmed": False,
                    "amount": amount,
                    "error": error_str
                }
        finally:
            # Always close the client to prevent resource leaks
            if client:
                try:
                    await client.close()
                except Exception as e:
                    logger.debug(f"Error closing client: {str(e)}")
            
    async def create_test_token(self, name: str, symbol: str, decimals: int, wallet) -> Dict[str, Any]:
        """
        Create a new test token on devnet
        
        Args:
            name: Token name
            symbol: Token symbol
            decimals: Token decimals (usually 9)
            wallet: Wallet to create token with (must have devnet SOL)
            
        Returns:
            Dict with mint address and transaction information
        """
        client = None
        try:
            # Create a fresh client for this operation
            client = await get_solana_client("devnet")
            
            # Ensure wallet has a keypair
            if not hasattr(wallet, 'keypair'):
                raise ValueError("Wallet must have a keypair")
                
            # Import needed token program functionality using solders
            from solders.keypair import Keypair
            from solders.pubkey import Pubkey
            from solders.system_program import create_account, CreateAccountParams
            from solders.instruction import Instruction
            from solana.transaction import Transaction as LegacyTransaction
            from solana.rpc.types import TxOpts
            from solana.rpc.commitment import Confirmed
            from spl.token.constants import TOKEN_PROGRAM_ID
            from spl.token.instructions import initialize_mint, InitializeMintParams
            
            # Generate new keypair for the mint
            mint_keypair = Keypair()
            mint_pubkey = mint_keypair.pubkey()
            
            # Get min rent for the mint
            rent_response = await client.get_minimum_balance_for_rent_exemption(82)  # Token mint size
            lamports = rent_response.value
            
            logger.info(f"Creating token {symbol} with mint {mint_pubkey}")
            
            # Create system program instruction to create the token account
            create_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=wallet.pubkey,
                    to_pubkey=mint_pubkey,
                    lamports=lamports,
                    space=82,
                    owner=TOKEN_PROGRAM_ID
                )
            )
            
            # Create SPL token program instruction to initialize the mint
            init_mint_params = InitializeMintParams(
                program_id=TOKEN_PROGRAM_ID,
                mint=mint_pubkey,
                decimals=decimals,
                mint_authority=wallet.pubkey,
                freeze_authority=None
            )
            init_mint_ix = initialize_mint(init_mint_params)
            
            # Ensure we have proper Keypair objects
            wallet_keypair = wallet.keypair
            if isinstance(wallet_keypair, bytes):
                wallet_keypair = Keypair.from_bytes(wallet_keypair)
            
            # Create a Legacy Transaction
            transaction = LegacyTransaction()
            transaction.add(create_account_ix)
            transaction.add(init_mint_ix)
            
            # Get recent blockhash for transaction
            blockhash_resp = await client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash
            
            # Set the fee payer
            transaction.recent_blockhash = blockhash
            transaction.fee_payer = wallet.pubkey
            
            # Sign transaction with mint keypair
            transaction.sign(wallet_keypair, mint_keypair)
            
            # Send the signed transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            tx_sig = await client.send_raw_transaction(transaction.serialize(), opts=opts)
            
            # Wait for confirmation
            await client.confirm_transaction(tx_sig.value)
            
            logger.info(f"Token created successfully: {mint_pubkey}")
            
            # Return result with mint address and transaction signature
            result = {
                "mint_address": str(mint_pubkey),
                "signature": tx_sig.value,
                "tx_link": f"https://explorer.solana.com/tx/{tx_sig.value}?cluster=devnet",
                "metadata": {
                    "name": name,
                    "symbol": symbol,
                    "decimals": decimals
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating test token: {str(e)}")
            raise
        finally:
            if client:
                await client.close()
    
    async def mint_test_tokens(self, token: str, amount: float, to_wallet, authority_wallet) -> Dict[str, Any]:
        """
        Mint test tokens to a wallet on devnet
        
        Args:
            token: Token mint address or symbol
            amount: Amount to mint
            to_wallet: Recipient wallet
            authority_wallet: Mint authority wallet
            
        Returns:
            Dict with transaction information
        """
        # Import needed modules
        from solders.pubkey import Pubkey
        from solders.instruction import Instruction
        from solana.transaction import Transaction as LegacyTransaction
        from solana.rpc.types import TxOpts
        from solana.rpc.commitment import Confirmed
        from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
        from spl.token.instructions import mint_to, MintToParams, create_associated_token_account, get_associated_token_address
        
        client = None
        try:
            # Create a fresh client for this operation
            client = await get_solana_client("devnet")
            
            # Determine token mint address
            if token in TOKEN_INFO:
                mint_address = TOKEN_INFO[token]["mint"]
                decimals = TOKEN_INFO[token]["decimals"]
            else:
                # Assume token is a mint address
                mint_address = token
                # Get token info to determine decimals
                token_info = await client.get_token_supply(
                    Pubkey.from_string(mint_address)
                )
                decimals = token_info.value.decimals
            
            mint_pubkey = Pubkey.from_string(mint_address)
            
            # Calculate amount in smallest units
            amount_in_smallest_units = int(amount * (10 ** decimals))
            
            # Get associated token account
            associated_token_pubkey = get_associated_token_address(
                to_wallet.pubkey,
                mint_pubkey
            )
            
            # Check if account exists
            account_info = await client.get_account_info(associated_token_pubkey)
            
            # Instructions to include in transaction
            instructions = []
            
            # Create associated token account if it doesn't exist
            if account_info.value is None:
                instructions.append(
                    create_associated_token_account(
                        payer=to_wallet.pubkey,
                        owner=to_wallet.pubkey,
                        mint=mint_pubkey
                    )
                )
            
            # Add mint instruction
            mint_params = MintToParams(
                program_id=TOKEN_PROGRAM_ID,
                mint=mint_pubkey,
                dest=associated_token_pubkey,
                mint_authority=authority_wallet.pubkey,
                amount=amount_in_smallest_units,
                signers=[authority_wallet.pubkey]
            )
            
            instructions.append(mint_to(mint_params))
            
            # Create and sign transaction
            transaction = LegacyTransaction()
            transaction.add(*instructions)
            
            # Get recent blockhash
            blockhash_resp = await client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash
            
            # Set the fee payer
            transaction.recent_blockhash = blockhash
            transaction.fee_payer = authority_wallet.pubkey
            
            # Sign transaction
            authority_keypair = authority_wallet.keypair
            if isinstance(authority_keypair, bytes):
                authority_keypair = Keypair.from_bytes(authority_keypair)
            
            transaction.sign(authority_keypair)
            
            # Send transaction
            tx_opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            tx_sig = await client.send_raw_transaction(transaction.serialize(), opts=tx_opts)
            
            # Wait for confirmation
            await client.confirm_transaction(tx_sig.value)
            
            logger.info(f"Minted {amount} tokens to {to_wallet.pubkey}")
            
            # Return result
            return {
                "token": mint_address,
                "amount": amount,
                "recipient": str(to_wallet.pubkey),
                "signature": tx_sig.value,
                "tx_link": f"https://explorer.solana.com/tx/{tx_sig.value}?cluster=devnet"
            }
            
        except Exception as e:
            logger.error(f"Error minting test tokens: {str(e)}")
            raise
        finally:
            if client:
                await client.close()
    
    async def create_test_market(self, base_token: str, quote_token: str, wallet) -> Dict[str, Any]:
        """
        Create a test market on devnet (serum/openbook DEX)
        
        Args:
            base_token: Base token mint address or symbol
            quote_token: Quote token mint address or symbol
            wallet: Wallet to create market with
            
        Returns:
            Dict with market address and transaction information
        """
        client = None
        try:
            # Create a fresh client for this operation
            client = await get_solana_client("devnet")
            
            # Get token mint addresses
            if base_token in TOKEN_INFO:
                base_mint = TOKEN_INFO[base_token]["mint"]
            else:
                base_mint = base_token
                
            if quote_token in TOKEN_INFO:
                quote_mint = TOKEN_INFO[quote_token]["mint"]
            else:
                quote_mint = quote_token
            
            # Convert to Pubkey objects
            base_mint_pubkey = Pubkey.from_string(base_mint)
            quote_mint_pubkey = Pubkey.from_string(quote_mint)
            
            # Import OpenBook/Serum DEX functionality
            from pyserum.market import Market
            from pyserum.open_orders import make_create_account_instruction
            from pyserum.instructions import (
                create_market_instruction,
                create_market_meta_data_instruction,
            )
            from pyserum.connection import get_live_markets, get_token_mints
            from pyserum.enums import Fees, AccountFlags
            from solana.transaction import Transaction
            from solana.system_program import create_account, CreateAccountParams
            
            # Serum program ID for devnet
            from pyserum.definitions import DEX_ID_DEVNET
            program_id = DEX_ID_DEVNET
            
            # Generate keypair for the new market
            market_keypair = Keypair()
            market_pubkey = market_keypair.pubkey()
            
            # Generate keypair for the request queue
            req_q_keypair = Keypair()
            req_q_pubkey = req_q_keypair.pubkey()
            
            # Generate keypair for the event queue
            event_q_keypair = Keypair()
            event_q_pubkey = event_q_keypair.pubkey()
            
            # Generate keypair for the bids
            bids_keypair = Keypair()
            bids_pubkey = bids_keypair.pubkey()
            
            # Generate keypair for the asks
            asks_keypair = Keypair()
            asks_pubkey = asks_keypair.pubkey()
            
            # Generate vault keypairs
            base_vault_keypair = Keypair()
            base_vault_pubkey = base_vault_keypair.pubkey()
            
            quote_vault_keypair = Keypair()
            quote_vault_pubkey = quote_vault_keypair.pubkey()
            
            # Get min rent for accounts
            market_space = Market.get_layout_for_market(program_id).sizeof()
            market_rent = await client.get_minimum_balance_for_rent_exemption(market_space)
            vault_rent = await client.get_minimum_balance_for_rent_exemption(165)
            req_q_space = 5120 + 12
            req_q_rent = await client.get_minimum_balance_for_rent_exemption(req_q_space)
            event_q_space = 262144 + 12
            event_q_rent = await client.get_minimum_balance_for_rent_exemption(event_q_space)
            bids_space = 65536 + 12
            bids_rent = await client.get_minimum_balance_for_rent_exemption(bids_space)
            asks_space = 65536 + 12
            asks_rent = await client.get_minimum_balance_for_rent_exemption(asks_space)
            
            # Create transaction
            transaction = Transaction()
            
            # Add create account instructions
            transaction.add(
                create_account(
                    CreateAccountParams(
                        from_pubkey=wallet.pubkey,
                        to_pubkey=market_pubkey,
                        lamports=market_rent.value,
                        space=market_space,
                        owner=program_id
                    )
                )
            )
            
            transaction.add(
                create_account(
                    CreateAccountParams(
                        from_pubkey=wallet.pubkey,
                        to_pubkey=req_q_pubkey,
                        lamports=req_q_rent.value,
                        space=req_q_space,
                        owner=program_id
                    )
                )
            )
            
            transaction.add(
                create_account(
                    CreateAccountParams(
                        from_pubkey=wallet.pubkey,
                        to_pubkey=event_q_pubkey,
                        lamports=event_q_rent.value,
                        space=event_q_space,
                        owner=program_id
                    )
                )
            )
            
            transaction.add(
                create_account(
                    CreateAccountParams(
                        from_pubkey=wallet.pubkey,
                        to_pubkey=bids_pubkey,
                        lamports=bids_rent.value,
                        space=bids_space,
                        owner=program_id
                    )
                )
            )
            
            transaction.add(
                create_account(
                    CreateAccountParams(
                        from_pubkey=wallet.pubkey,
                        to_pubkey=asks_pubkey,
                        lamports=asks_rent.value,
                        space=asks_space,
                        owner=program_id
                    )
                )
            )
            
            # Add create market instruction
            transaction.add(
                create_market_instruction(
                    program_id=program_id,
                    payer_key=wallet.pubkey,
                    market_key=market_pubkey,
                    request_queue_key=req_q_pubkey,
                    event_queue_key=event_q_pubkey,
                    bids_key=bids_pubkey,
                    asks_key=asks_pubkey,
                    base_vault_key=base_vault_pubkey,
                    quote_vault_key=quote_vault_pubkey,
                    base_mint_key=base_mint_pubkey,
                    quote_mint_key=quote_mint_pubkey,
                    base_lot_size=100000,  # 0.0001 BASE
                    quote_lot_size=100,    # 0.0001 QUOTE
                    fees=Fees.from_number(0.0022)  # 0.22%
                )
            )
            
            # Sign and send transaction
            signers = [
                wallet.keypair,
                market_keypair,
                req_q_keypair,
                event_q_keypair,
                bids_keypair,
                asks_keypair
            ]
            tx_sig = await client.send_transaction(transaction, *signers)
            
            # Wait for confirmation
            await client.confirm_transaction(tx_sig.value)
            
            logger.info(f"Market created successfully: {market_pubkey}")
            
            return {
                "market_address": str(market_pubkey),
                "signature": tx_sig.value,
                "base_token": base_token if base_token in TOKEN_INFO else base_mint,
                "quote_token": quote_token if quote_token in TOKEN_INFO else quote_mint
            }
            
        except Exception as e:
            logger.error(f"Error creating test market: {str(e)}")
            raise
        finally:
            if client:
                await client.close()
    
    async def execute_test_trade(self, market: str, side: str, amount: float, wallet) -> Dict[str, Any]:
        """
        Execute a test trade on a devnet market
        
        Args:
            market: Market address or symbol pair (e.g. "SOL/USDC")
            side: Trade side ("buy" or "sell")
            amount: Amount to trade in base token
            wallet: Trading wallet
            
        Returns:
            Dict with trade details and transaction information
        """
        client = None
        try:
            # Create a fresh client for this operation
            client = await get_solana_client("devnet")
            
            # Import OpenBook/Serum DEX functionality
            from pyserum.market import Market
            from pyserum.enums import Side as SerumSide
            from pyserum.enums import Fees, OrderType
            from pyserum.open_orders import OpenOrders
            from solana.transaction import Transaction
            
            # Serum program ID for devnet
            from pyserum.definitions import DEX_ID_DEVNET
            program_id = DEX_ID_DEVNET
            
            # Determine market address
            market_address = None
            if "/" in market:
                # Symbol pair provided (e.g. "SOL/USDC")
                base_symbol, quote_symbol = market.split("/")
                
                # Get supported markets
                markets = await get_live_markets(client, program_id)
                
                # Find matching market
                for m in markets:
                    base_mint, quote_mint = await get_token_mints(client, m.market_address)
                    
                    # Check if mint addresses match known tokens
                    base_match = False
                    quote_match = False
                    
                    for token, info in TOKEN_INFO.items():
                        if token == base_symbol and info["mint"] == str(base_mint):
                            base_match = True
                        if token == quote_symbol and info["mint"] == str(quote_mint):
                            quote_match = True
                    
                    if base_match and quote_match:
                        market_address = m.market_address
                        break
                
                if not market_address:
                    raise ValueError(f"Market {market} not found")
            else:
                # Market address provided
                market_address = Pubkey.from_string(market)
            
            # Load the market
            loaded_market = await Market.load(client, market_address, program_id=program_id)
            
            # Get current price
            orderbook = await loaded_market.load_orderbook(side="buy" if side.lower() == "sell" else "sell")
            if len(orderbook) > 0:
                price = orderbook[0].price
            else:
                # Use a default price for testing
                price = 10.0
            
            # Prepare the transaction
            transaction = Transaction()
            
            # Get open orders account for this market
            open_orders_accounts = await OpenOrders.find_for_market_and_owner(
                client,
                loaded_market.state.public_key(),
                wallet.pubkey,
                program_id
            )
            
            open_orders_address = None
            if open_orders_accounts:
                open_orders_address = open_orders_accounts[0].address
            else:
                # Create a new open orders account
                open_orders_keypair = Keypair()
                open_orders_address = open_orders_keypair.pubkey()
                
                # Add create open orders instruction
                transaction.add(
                    make_create_account_instruction(
                        client,
                        wallet.pubkey,
                        open_orders_address,
                        loaded_market.state.public_key(),
                        program_id
                    )
                )
            
            # Determine order side
            order_side = SerumSide.BUY if side.lower() == "buy" else SerumSide.SELL
            
            # Add place order instruction
            transaction.add(
                loaded_market.make_place_order_instruction(
                    payer=wallet.pubkey,
                    owner=wallet.pubkey,
                    order_type=OrderType.LIMIT,
                    side=order_side,
                    price=price,
                    amount=amount,
                    open_orders_address=open_orders_address
                )
            )
            
            # Sign and send transaction
            tx_sig = await client.send_transaction(transaction, wallet.keypair)
            
            # Wait for confirmation
            await client.confirm_transaction(tx_sig.value)
            
            logger.info(f"Trade executed successfully: {side} {amount} @ {price}")
            
            return {
                "signature": tx_sig.value,
                "side": side.upper(),
                "amount": amount,
                "price": price,
                "market": str(market_address),
                "open_orders": str(open_orders_address)
            }
            
        except Exception as e:
            logger.error(f"Error executing test trade: {str(e)}")
            raise
        finally:
            if client:
                await client.close()
    
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

    def perform_security_audit(self) -> Dict[str, Any]:
        """
        Perform a security audit of the system configuration
        Returns audit results
        """
        return self.security_manager.perform_security_audit()
        
    async def place_order(self, order_params, market_name=None, value=0.0) -> Dict[str, Any]:
        """
        Place an order on the Drift exchange
        
        Args:
            order_params: The OrderParams object
            market_name: Name of the market
            value: Value of the order
            
        Returns:
            Dict with transaction information
        """
        if not self.drift_client:
            raise Exception("Drift client not initialized. Call initialize_drift() first")
            
        try:
            # Confirm transaction if needed
            tx_details = {
                'type': 'place_order',
                'market': market_name,
                'size': order_params.base_asset_amount,
                'price': order_params.price,
                'value': value
            }
            
            # Update last activity
            self.security_manager.update_activity()
            
            # Check for session timeout
            if time.time() - self.security_manager.last_activity_time > self.security_manager.session_timeout:
                raise Exception("Session timed out. Please reconnect.")
                
            # Request confirmation if needed
            if not await self.security_manager.confirm_transaction(tx_details):
                logger.warning("Transaction rejected by user")
                return None
                
            logger.info(f"Placing order on {market_name}...")
            
            # This is a mock implementation for testing
            # In a real implementation, we would call the drift_client.place_order method
            
            return {
                "success": True,
                "txid": "mock_tx_id_" + str(int(time.time())),
                "market": market_name,
                "size": order_params.base_asset_amount,
                "price": order_params.price,
                "value": value
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise

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