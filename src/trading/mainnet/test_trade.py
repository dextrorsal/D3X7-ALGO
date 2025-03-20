#!/usr/bin/env python3
"""
Mainnet trading script that leverages existing infrastructure with security limits.
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

# Get env values
WALLET_PASSWORD = os.getenv("WALLET_PASSWORD")
ENABLE_ENCRYPTION = os.getenv("ENABLE_ENCRYPTION", "true").lower() in ("true", "1", "yes")
MAINNET_RPC_ENDPOINT = os.getenv("MAINNET_RPC_ENDPOINT")
DRIFT_NETWORK = os.getenv("DRIFT_NETWORK", "mainnet-beta")
DRIFT_PRIVATE_KEY_PATH = os.getenv("DRIFT_PRIVATE_KEY_PATH")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
KP_PATH = os.getenv("KP_PATH")
AG_PATH = os.getenv("AG_PATH")

# Security checks
if not MAINNET_RPC_ENDPOINT:
    logger.warning("MAINNET_RPC_ENDPOINT not set, using default public endpoint")

if DRIFT_NETWORK != "mainnet-beta":
    logger.warning(f"DRIFT_NETWORK set to {DRIFT_NETWORK}, should be 'mainnet-beta' for mainnet trading")

if not WALLET_PASSWORD and ENABLE_ENCRYPTION:
    logger.error("WALLET_PASSWORD not set but encryption is enabled")
    raise ValueError("WALLET_PASSWORD must be set when ENABLE_ENCRYPTION is true")

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

async def test_drift_trade(
    market: str,
    size: float,
    side: str = "buy",
    wallet_name: str = "MAIN",
    security_config: Optional[Dict[str, Any]] = None
):
    """
    Execute a test trade on Drift mainnet with security limits.
    
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
        
        # For this test, we'll just log the trade details rather than executing
        if security_config.get("test_mode", True):
            logger.info(f"TEST MODE: Would place {direction} order for {size} on {market} (index {market_index})")
            result = {
                "status": "simulated",
                "market": market,
                "size": size,
                "direction": direction,
                "market_index": market_index,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Execute actual trade using your existing place_perp_order function
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
                "status": "simulated" if security_config.get("test_mode", True) else "executed",
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
        logger.error(f"Error executing test trade: {e}")
        return {
            "status": "failed",
            "reason": str(e),
            "market": market,
            "size": size,
            "side": side
        }

async def test_jupiter_swap(
    market: str,
    input_amount: float,
    wallet_name: str = "MAIN",
    security_config: Optional[Dict[str, Any]] = None
):
    """
    Execute a test token swap on Jupiter with security limits.
    
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
    
    # Log the swap attempt
    logger.info(f"Attempting swap of {input_amount} on {market} with security limits")
    
    # Validate trade size first
    if not security_limits.validate_trade_size(market, input_amount):
        logger.error(f"Swap rejected: amount {input_amount} exceeds security limits")
        return {
            "status": "rejected",
            "reason": "amount_exceeded",
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
        
        # Initialize Jupiter adapter with wallet
        adapter = JupiterAdapter(keypair_path=wallet.get_keypair_path())
        await adapter.connect()
        
        # Set slippage from security config
        slippage_bps = security_config.get("slippage_bps", 300)
        
        # For this test, we'll just log the swap details rather than executing
        if security_config.get("test_mode", True):
            logger.info(f"TEST MODE: Would swap {input_amount} on {market} with slippage {slippage_bps} bps")
            result = {
                "status": "simulated",
                "market": market,
                "input_amount": input_amount,
                "slippage_bps": slippage_bps,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Execute actual swap using your existing execute_swap function
            result = await adapter.execute_swap(
                market=market,
                input_amount=input_amount,
                slippage_bps=slippage_bps
            )
        
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
                "input_amount": input_amount,
                "slippage_bps": slippage_bps,
                "status": "simulated" if security_config.get("test_mode", True) else "executed",
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
        logger.error(f"Error executing test swap: {e}")
        return {
            "status": "failed",
            "reason": str(e),
            "market": market,
            "input_amount": input_amount
        }

async def main():
    """Main entry point for test trading script."""
    parser = argparse.ArgumentParser(description="Test trading on mainnet with security limits")
    
    # Trade type subparsers
    subparsers = parser.add_subparsers(dest="trade_type", help="Type of trade to execute")
    
    # Drift trade parser
    drift_parser = subparsers.add_parser("drift", help="Execute a Drift trade")
    drift_parser.add_argument("--market", type=str, default="SOL-PERP", help="Market symbol")
    drift_parser.add_argument("--size", type=float, required=True, help="Trade size")
    drift_parser.add_argument("--side", type=str, default="buy", choices=["buy", "sell"], help="Trade side")
    drift_parser.add_argument("--wallet", type=str, default="MAIN", help="Wallet name to use")
    
    # Jupiter swap parser
    jup_parser = subparsers.add_parser("jupiter", help="Execute a Jupiter swap")
    jup_parser.add_argument("--market", type=str, default="SOL-USDC", help="Market symbol")
    jup_parser.add_argument("--amount", type=float, required=True, help="Input amount")
    jup_parser.add_argument("--wallet", type=str, default="MAIN", help="Wallet name to use")
    
    # Security limit options for both trade types
    for p in [drift_parser, jup_parser]:
        p.add_argument("--max-trade-size", type=float, default=0.01, help="Maximum trade size")
        p.add_argument("--max-fee", type=float, default=0.00001, help="Maximum fee")
        p.add_argument("--slippage-bps", type=int, default=300, help="Maximum slippage in basis points")
        p.add_argument("--test-mode", action="store_true", help="Run in test mode (no actual trades)")
    
    args = parser.parse_args()
    
    # Build security config from arguments
    security_config = {
        "max_trade_size": args.max_trade_size,
        "max_fee": args.max_fee,
        "slippage_bps": args.slippage_bps,
        "test_mode": args.test_mode
    }
    
    # Execute the appropriate trade type
    if args.trade_type == "drift":
        result = await test_drift_trade(
            market=args.market,
            size=args.size,
            side=args.side,
            wallet_name=args.wallet,
            security_config=security_config
        )
    elif args.trade_type == "jupiter":
        result = await test_jupiter_swap(
            market=args.market,
            input_amount=args.amount,
            wallet_name=args.wallet,
            security_config=security_config
        )
    else:
        parser.print_help()
        return
    
    # Print the result
    print("\nTrade Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())