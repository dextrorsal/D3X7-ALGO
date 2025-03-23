#!/usr/bin/env python3
"""
Mainnet Trading Script

A production-ready script for executing trades and swaps on mainnet with security limits.
Supports both Drift perpetual markets and Jupiter token swaps with comprehensive
security checks, logging, and balance tracking.

Usage:
    For Drift trades:
        ./mainnet_trade.py --market SOL-PERP --size 1.0 --side buy
    
    For Jupiter swaps:
        ./mainnet_trade.py --market SOL-USDC --size 1.0

Features:
    - Security limits enforcement
    - Comprehensive logging
    - Balance tracking
    - Support for multiple wallets
"""

import asyncio
import logging
import argparse
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Import security module
from .security_limits import SecurityLimits

# Import existing infrastructure
from src.utils.wallet.wallet_cli import WalletCLI
from src.trading.drift.account_manager import DriftAccountManager
from src.trading.jup.jup_adapter import JupiterAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


MAINNET_RPC_ENDPOINT = os.getenv("MAINNET_RPC_ENDPOINT")
DRIFT_NETWORK = os.getenv("DRIFT_NETWORK", "mainnet-beta")
MAIN_KEY_PATH = os.getenv("MAIN_KEY_PATH")
KP_PATH = os.getenv("KP_PATH")
AG_PATH = os.getenv("AG_PATH")

# Security checks
if not MAINNET_RPC_ENDPOINT:
    logger.warning("MAINNET_RPC_ENDPOINT not set, using default public endpoint")

if DRIFT_NETWORK != "mainnet-beta":
    logger.warning(f"DRIFT_NETWORK set to {DRIFT_NETWORK}, should be 'mainnet-beta' for mainnet trading")


async def setup_wallet_cli():
    """Initialize wallet CLI with environment variables"""
    # Create wallet CLI instance
    wallet_cli = WalletCLI()
    
    # Configure with environment variables
    if ENABLE_ENCRYPTION:
        wallet_cli.enable_encryption(WALLET_PASSWORD)
    
    # Set network to mainnet
    wallet_cli.set_network("mainnet")
    
    # Load wallet by default (first one in priority)
    wallet_path = PRIVATE_KEY_PATH or KP_PATH or AG_PATH
    if wallet_path:
        wallet_cli.load_wallet(wallet_path)
    
    return wallet_cli

async def execute_drift_trade(
    market: str,
    size: float,
    side: str = "buy",
    wallet_name: str = "MAIN",
    security_config: Optional[Dict[str, Any]] = None
):
    """
    Execute a trade on Drift mainnet with security limits.
    
    Args:
        market: Market symbol (e.g., "SOL-PERP")
        size: Trade size
        side: Trade side ("buy" or "sell")
        wallet_name: Wallet name to use
        security_config: Security configuration
    """
    # Initialize security limits with provided config or defaults
    security_limits = SecurityLimits(
        config_path=None,  # No config file for this example
        **(security_config or {})  # Use provided config or empty dict
    )
    
    # Log the trade attempt
    logger.info(f"Attempting {side} trade for {size} on {market} with security limits")
    
    # Validate trade size first
    if not security_limits.validate_trade_size(market, size):
        logger.error(f"Trade rejected: size {size} exceeds security limits")
        return {
            "status": "rejected",
            "reason": "trade_size_exceeded",
            "market": market,
            "size": size,
            "side": side
        }
    
    try:
        # Initialize wallet CLI
        wallet_cli = await setup_wallet_cli()
        
        # Get wallet object from wallet name
        wallet = wallet_cli.get_wallet(wallet_name)
        if not wallet:
            logger.error(f"Wallet {wallet_name} not found")
            return {
                "status": "rejected",
                "reason": "wallet_not_found",
                "wallet_name": wallet_name
            }
        
        # Initialize Drift account manager
        manager = DriftAccountManager()
        
        # Set wallet from CLI
        manager.set_wallet(wallet)
        
        # Setup with correct RPC endpoint
        await manager.setup(rpc_url=MAINNET_RPC_ENDPOINT)
        
        # Show initial balances
        await manager.show_balances()
        
        # Determine market index
        market_indices = {
            "SOL-PERP": 0,
            "BTC-PERP": 1,
            "ETH-PERP": 2
        }
        
        if market not in market_indices:
            logger.error(f"Unsupported market: {market}")
            return {
                "status": "rejected",
                "reason": "unsupported_market",
                "market": market
            }
            
        market_index = market_indices[market]
        
        # Execute the trade with security limits applied to the API call
        logger.info(f"Executing {side} order for {size} on {market}...")
        
        # Convert side to direction
        direction = "long" if side.lower() == "buy" else "short"
        
        # Execute actual trade
        result = await manager.place_perp_order(
            market_index=market_index,
            direction=direction,
            size=size,
            order_type="market"
        )
        
        # Show updated balances
        await manager.show_balances()
        
        # Create the trade log directory if it doesn't exist
        log_dir = Path(os.path.expanduser("~/.config/mainnet_trading/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the trade
        try:
            log_file = log_dir / f"trades_{datetime.utcnow().strftime('%Y%m%d')}.json"
            
            # Load existing logs or create new array
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    
            # Create log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "market": market,
                "size": size,
                "side": side,
                "status": "executed",
                "result": result
            }
            
            # Add to logs
            logs.append(log_entry)
            
            # Write back to file
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return {
            "status": "failed",
            "reason": str(e),
            "market": market,
            "size": size,
            "side": side
        }

async def execute_jupiter_swap(
    market: str,
    input_amount: float,
    wallet_name: str = "MAIN",
    security_config: Optional[Dict[str, Any]] = None
):
    """
    Execute a token swap on Jupiter with security limits.
    
    Args:
        market: Market symbol (e.g., "SOL-USDC")
        input_amount: Amount of input token
        wallet_name: Wallet name to use
        security_config: Security configuration
    """
    # Initialize security limits with provided config or defaults
    security_limits = SecurityLimits(
        config_path=None,  # No config file for this example
        **(security_config or {})  # Use provided config or empty dict
    )
    
    # Extract input token from market pair
    input_token = market.split("-")[0]
    
    # Log the swap attempt
    logger.info(f"Attempting swap of {input_amount} {input_token} on {market}")
    
    # Validate swap size first
    if not security_limits.validate_swap_size(input_token, input_amount):
        logger.error(f"Swap rejected: amount {input_amount} exceeds security limits")
        return {
            "status": "rejected",
            "reason": "swap_size_exceeded",
            "market": market,
            "input_amount": input_amount
        }
    
    try:
        # Initialize wallet CLI
        wallet_cli = await setup_wallet_cli()
        
        # Get wallet object from wallet name
        wallet = wallet_cli.get_wallet(wallet_name)
        if not wallet:
            logger.error(f"Wallet {wallet_name} not found")
            return {
                "status": "rejected",
                "reason": "wallet_not_found",
                "wallet_name": wallet_name
            }
        
        # Initialize Jupiter adapter
        adapter = JupiterAdapter()
        
        # Set wallet from CLI
        adapter.set_wallet(wallet)
        
        # Setup with correct RPC endpoint
        await adapter.setup(rpc_url=MAINNET_RPC_ENDPOINT)
        
        # Show initial balances
        await adapter.show_balances()
        
        # Execute the swap
        logger.info(f"Executing swap of {input_amount} {input_token} on {market}...")
        
        result = await adapter.execute_swap(
            market=market,
            input_amount=input_amount
        )
        
        # Show updated balances
        await adapter.show_balances()
        
        # Create the swap log directory if it doesn't exist
        log_dir = Path(os.path.expanduser("~/.config/mainnet_trading/logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the swap
        try:
            log_file = log_dir / f"swaps_{datetime.utcnow().strftime('%Y%m%d')}.json"
            
            # Load existing logs or create new array
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    
            # Create log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "market": market,
                "input_amount": input_amount,
                "input_token": input_token,
                "status": "executed",
                "result": result
            }
            
            # Add to logs
            logs.append(log_entry)
            
            # Write back to file
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log swap: {e}")
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing swap: {e}")
        return {
            "status": "failed",
            "reason": str(e),
            "market": market,
            "input_amount": input_amount
        }

async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Execute trades on mainnet with security limits")
    parser.add_argument("--market", required=True, help="Market symbol (e.g., SOL-PERP or SOL-USDC)")
    parser.add_argument("--size", type=float, required=True, help="Trade size or input amount")
    parser.add_argument("--side", default="buy", choices=["buy", "sell"], help="Trade side (for perp markets)")
    parser.add_argument("--wallet", default="MAIN", help="Wallet name to use")
    args = parser.parse_args()
    
    # Determine if this is a perp trade or swap based on market name
    is_perp = args.market.endswith("-PERP")
    
    if is_perp:
        result = await execute_drift_trade(
            market=args.market,
            size=args.size,
            side=args.side,
            wallet_name=args.wallet
        )
    else:
        result = await execute_jupiter_swap(
            market=args.market,
            input_amount=args.size,
            wallet_name=args.wallet
        )
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())