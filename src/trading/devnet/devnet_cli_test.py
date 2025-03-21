#!/usr/bin/env python3
"""
Simple test script for DevnetAdapter functionality.
This script provides a command-line interface to test the DevnetAdapter functions.
"""

import asyncio
import sys
import argparse
import logging
import os
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Import solana shim for compatibility
from src.trading.devnet.solana_shim import *

# Imports from the project
from src.trading.devnet.devnet_adapter import DevnetAdapter
from src.utils.wallet.wallet_manager import WalletManager
from src.utils.wallet.sol_wallet import SolanaWallet
from src.utils.wallet.encryption import WalletEncryption

def load_wallet_from_json(wallet_name: str) -> Optional[Dict]:
    """
    Load a wallet from a JSON file path
    
    Args:
        wallet_name: Name of the wallet (MAIN, KP, AG)
        
    Returns:
        str: Path to the wallet JSON file
    """
    try:
        # Map wallet names to environment variable keys
        wallet_path_map = {
            "MAIN": "MAIN_KEY_PATH",
            "KP": "KP_KEY_PATH",
            "AG": "AG_KEY_PATH",
        }
        
        # Get wallet path from env
        env_key = wallet_path_map.get(wallet_name.upper())
        if not env_key:
            logger.warning(f"Unknown wallet name: {wallet_name}")
            return None
            
        wallet_path = os.getenv(env_key)
        if not wallet_path or not os.path.exists(wallet_path):
            logger.warning(f"Wallet file not found at {wallet_path}")
            return None
            
        logger.info(f"Using wallet file: {wallet_path}")
        return wallet_path
    except Exception as e:
        logger.error(f"Error loading wallet: {str(e)}")
        return None

async def handle_airdrop(adapter: DevnetAdapter, wallet_name: str, amount: float) -> Dict[str, Any]:
    """Request a SOL airdrop for the specified wallet."""
    wallet_manager = WalletManager()
    
    # Load wallet from JSON file
    wallet = None
    wallet_path = load_wallet_from_json(wallet_name)
    
    if wallet_path:
        wallet_manager.add_wallet(wallet_name.upper(), wallet_path, is_main=(wallet_name.upper() == "MAIN"))
        wallet = wallet_manager.get_wallet(wallet_name.upper())
    
    # Fallback to default wallet if needed
    if not wallet:
        wallet_path = os.path.expanduser("~/.config/solana/keys/id.json")
        wallet_manager.add_wallet("DEFAULT", wallet_path, is_main=True)
        wallet = wallet_manager.get_wallet("DEFAULT")
    
    if not wallet:
        logger.error(f"Could not load any wallet")
        return {"error": "Could not load any wallet"}
    
    try:
        logger.info(f"Requesting {amount} SOL airdrop for {wallet.pubkey}...")
        result = await adapter.request_airdrop(wallet, amount)
        logger.info(f"Airdrop successful! Transaction: {result['signature']}")
        return result
    except Exception as e:
        logger.error(f"Error requesting airdrop: {str(e)}")
        return {"error": str(e)}
    finally:
        await wallet_manager.close()

async def handle_create_token(adapter: DevnetAdapter, name: str, symbol: str, decimals: int, wallet_name: str) -> Dict[str, Any]:
    """Create a test token with the specified details."""
    wallet_manager = WalletManager()
    
    # Load wallet from JSON file
    wallet = None
    wallet_path = load_wallet_from_json(wallet_name)
    
    if wallet_path:
        wallet_manager.add_wallet(wallet_name.upper(), wallet_path, is_main=(wallet_name.upper() == "MAIN"))
        wallet = wallet_manager.get_wallet(wallet_name.upper())
    
    # Fallback to default wallet if needed
    if not wallet:
        wallet_path = os.path.expanduser("~/.config/solana/keys/id.json")
        wallet_manager.add_wallet("DEFAULT", wallet_path, is_main=True)
        wallet = wallet_manager.get_wallet("DEFAULT")
    
    if not wallet:
        logger.error("Could not load any wallet")
        return {"error": "Could not load any wallet"}
    
    try:
        logger.info(f"Creating test token {symbol}...")
        result = await adapter.create_test_token(name, symbol, decimals, wallet)
        logger.info(f"Token created successfully! Mint address: {result['mint_address']}")
        return result
    except Exception as e:
        logger.error(f"Error creating token: {str(e)}")
        return {"error": str(e)}
    finally:
        await wallet_manager.close()

async def handle_mint_tokens(adapter: DevnetAdapter, token: str, amount: float, to_wallet_name: str, authority_wallet_name: str) -> Dict[str, Any]:
    """Mint tokens to the specified wallet."""
    wallet_manager = WalletManager()
    
    # Initialize wallets dictionary
    wallets = {}
    
    # Load authority wallet
    authority_path = load_wallet_from_json(authority_wallet_name)
    if authority_path:
        wallet_manager.add_wallet(authority_wallet_name.upper(), authority_path, is_main=(authority_wallet_name.upper() == "MAIN"))
        wallets["authority"] = wallet_manager.get_wallet(authority_wallet_name.upper())
    
    # Load recipient wallet (if different from authority)
    if to_wallet_name.upper() != authority_wallet_name.upper():
        to_path = load_wallet_from_json(to_wallet_name)
        if to_path:
            wallet_manager.add_wallet(to_wallet_name.upper(), to_path, is_main=(to_wallet_name.upper() == "MAIN"))
            wallets["to"] = wallet_manager.get_wallet(to_wallet_name.upper())
    
    # Fallback to default wallet if needed
    default_wallet_path = os.path.expanduser("~/.config/solana/keys/id.json")
    if "authority" not in wallets:
        wallet_manager.add_wallet("DEFAULT", default_wallet_path, is_main=True)
        wallets["authority"] = wallet_manager.get_wallet("DEFAULT")
    
    if "to" not in wallets:
        if "authority" in wallets:
            wallets["to"] = wallets["authority"]
        else:
            wallet_manager.add_wallet("DEFAULT", default_wallet_path, is_main=True)
            wallets["to"] = wallet_manager.get_wallet("DEFAULT")
    
    if not wallets.get("authority") or not wallets.get("to"):
        logger.error("Could not load required wallets")
        return {"error": "Could not load required wallets"}
    
    try:
        logger.info(f"Minting {amount} {token} to {wallets['to'].pubkey}...")
        result = await adapter.mint_test_tokens(token, amount, wallets["to"], wallets["authority"])
        logger.info(f"Tokens minted successfully! Transaction: {result['signature']}")
        return result
    except Exception as e:
        logger.error(f"Error minting tokens: {str(e)}")
        return {"error": str(e)}
    finally:
        await wallet_manager.close()

async def handle_create_market(adapter: DevnetAdapter, base_token: str, quote_token: str, wallet_name: str) -> Dict[str, Any]:
    """Create a test market between two tokens."""
    wallet_manager = WalletManager()
    
    # Load wallet from JSON file
    wallet = None
    wallet_path = load_wallet_from_json(wallet_name)
    
    if wallet_path:
        wallet_manager.add_wallet(wallet_name.upper(), wallet_path, is_main=(wallet_name.upper() == "MAIN"))
        wallet = wallet_manager.get_wallet(wallet_name.upper())
    
    # Fallback to default wallet if needed
    if not wallet:
        wallet_path = os.path.expanduser("~/.config/solana/keys/id.json")
        wallet_manager.add_wallet("DEFAULT", wallet_path, is_main=True)
        wallet = wallet_manager.get_wallet("DEFAULT")
    
    if not wallet:
        logger.error("Could not load any wallet")
        return {"error": "Could not load any wallet"}
    
    try:
        logger.info(f"Creating market for {base_token}/{quote_token}...")
        result = await adapter.create_test_market(base_token, quote_token, wallet)
        logger.info(f"Market created successfully! Market address: {result['market_address']}")
        return result
    except Exception as e:
        logger.error(f"Error creating market: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"error": str(e)}
    finally:
        await wallet_manager.close()

async def main():
    """Main function to parse arguments and dispatch commands."""
    parser = argparse.ArgumentParser(description='DevnetAdapter Test Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Airdrop command
    airdrop_parser = subparsers.add_parser('airdrop', help='Request a SOL airdrop')
    airdrop_parser.add_argument('--wallet', required=False, default='MAIN', help='Wallet name to receive SOL')
    airdrop_parser.add_argument('--amount', type=float, default=1.0, help='Amount of SOL to request')
    
    # Create token command
    create_token_parser = subparsers.add_parser('create-token', help='Create a test token')
    create_token_parser.add_argument('--name', required=True, help='Token name')
    create_token_parser.add_argument('--symbol', required=True, help='Token symbol')
    create_token_parser.add_argument('--decimals', type=int, default=9, help='Token decimals')
    create_token_parser.add_argument('--wallet', required=False, default='MAIN', help='Wallet name to create token with')
    
    # Mint tokens command
    mint_parser = subparsers.add_parser('mint', help='Mint test tokens')
    mint_parser.add_argument('--token', required=True, help='Token address or symbol')
    mint_parser.add_argument('--amount', type=float, required=True, help='Amount to mint')
    mint_parser.add_argument('--to-wallet', required=False, default='MAIN', help='Recipient wallet name')
    mint_parser.add_argument('--authority-wallet', required=False, default='MAIN', help='Mint authority wallet name')
    
    # Create market command
    market_parser = subparsers.add_parser('create-market', help='Create a test market')
    market_parser.add_argument('--base', required=True, help='Base token address or symbol')
    market_parser.add_argument('--quote', required=True, help='Quote token address or symbol')
    market_parser.add_argument('--wallet', required=False, default='MAIN', help='Wallet name to create market with')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize DevnetAdapter
    adapter = DevnetAdapter()
    await adapter.connect()
    
    try:
        if args.command == 'airdrop':
            await handle_airdrop(adapter, args.wallet, args.amount)
        elif args.command == 'create-token':
            await handle_create_token(adapter, args.name, args.symbol, args.decimals, args.wallet)
        elif args.command == 'mint':
            await handle_mint_tokens(adapter, args.token, args.amount, args.to_wallet, args.authority_wallet)
        elif args.command == 'create-market':
            await handle_create_market(adapter, args.base, args.quote, args.wallet)
        else:
            logger.error(f"Unknown command: {args.command}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main()) 