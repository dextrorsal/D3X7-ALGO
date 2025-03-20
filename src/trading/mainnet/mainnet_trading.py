#!/usr/bin/env python3
"""
Mainnet trading script with enhanced security controls.
Uses existing infrastructure with strict limits for safe mainnet trading.
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
from src.utils.wallet.sol_rpc import get_network, NETWORK_URLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get RPC endpoint from environment
# MAINNET_RPC_ENDPOINT = os.getenv("MAINNET_RPC_ENDPOINT")
# if not MAINNET_RPC_ENDPOINT:
#     logger.warning("MAINNET_RPC_ENDPOINT not set - using default public endpoint")
#     MAINNET_RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"

# Import existing infrastructure
# Note: These imports will work if PYTHONPATH includes the project root
from src.trading.drift.account_manager import DriftAccountManager
from src.trading.drift.drift_adapter import DriftAdapter
from src.trading.jup.jup_adapter import JupiterAdapter
from src.utils.wallet.sol_rpc import get_solana_client
from src.utils.wallet.wallet_cli import WalletCLI

class MainnetTrading:
    """
    Mainnet trading with enhanced security controls
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize mainnet trading with security settings
        
        Args:
            config_path: Path to configuration file (optional)
        """
        # Default security limits
        self.max_trade_size = 0.01      # Maximum trade size (SOL or equivalent)
        self.max_fee = 0.00001          # Maximum fee (SOL)
        self.slippage_bps = 300         # Maximum slippage (3%)
        self.test_mode = True           # Default to test mode
        self.requires_confirmation = True  # Require confirmation for all trades
        
        # Load configuration if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.max_trade_size = config.get("max_trade_size", self.max_trade_size)
                    self.max_fee = config.get("max_fee", self.max_fee)
                    self.slippage_bps = config.get("slippage_bps", self.slippage_bps)
                    self.test_mode = config.get("test_mode", self.test_mode)
                    self.requires_confirmation = config.get("requires_confirmation", self.requires_confirmation)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
        
        # Initialize client
        self.client = get_solana_client("mainnet")
        
        # Create logs directory
        self.log_dir = Path(os.path.expanduser("~/.config/mainnet_trading/logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Load wallet CLI
        self.wallet_cli = WalletCLI()
        
        # Log configuration
        self._log_configuration()
    
    def _log_configuration(self):
        """Log current configuration"""
        logger.info("=== Mainnet Trading Configuration ===")
        logger.info(f"Max Trade Size: {self.max_trade_size} SOL")
        logger.info(f"Max Fee: {self.max_fee} SOL")
        logger.info(f"Slippage: {self.slippage_bps/100}%")
        logger.info(f"Test Mode: {'Enabled' if self.test_mode else 'Disabled'}")
        logger.info(f"Confirmation Required: {'Yes' if self.requires_confirmation else 'No'}")
        # logger.info(f"RPC Endpoint: {MAINNET_RPC_ENDPOINT}")
        
    def _confirm_trade(self, trade_details: Dict[str, Any]) -> bool:
        """
        Request user confirmation for a trade
        
        Args:
            trade_details: Trade details dictionary
            
        Returns:
            True if confirmed, False otherwise
        """
        if not self.requires_confirmation:
            return True
            
        print("\n" + "="*50)
        print("MAINNET TRADE CONFIRMATION REQUIRED")
        print("="*50)
        print(f"Type: {trade_details.get('type', 'Unknown')}")
        print(f"Market: {trade_details.get('market', 'Unknown')}")
        print(f"Size: {trade_details.get('size', 'Unknown')}")
        if 'price' in trade_details:
            print(f"Price: {trade_details.get('price', 'Unknown')}")
        if 'direction' in trade_details:
            print(f"Direction: {trade_details.get('direction', 'Unknown')}")
        print("-"*50)
        print("WARNING: This is a MAINNET transaction using REAL funds")
        print("-"*50)
        
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        return confirm.lower() == 'yes'
    
    def _log_trade(self, trade_details: Dict[str, Any], status: str = "initiated"):
        """
        Log trade details for auditing
        
        Args:
            trade_details: Trade details
            status: Trade status
        """
        # Add timestamp and status
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            **trade_details
        }
        
        # Determine log file path (one file per day)
        log_file = self.log_dir / f"trades_{datetime.utcnow().strftime('%Y%m%d')}.json"
        
        try:
            # Load existing logs or create new array
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            
            # Add new log entry
            logs.append(log_entry)
            
            # Write back to file
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    def validate_trade_size(self, market: str, size: float) -> bool:
        """
        Validate trade size against limits
        
        Args:
            market: Market symbol (e.g., "SOL-PERP")
            size: Trade size
            
        Returns:
            True if valid, False if rejected
        """
        # For SOL markets, directly check against max trade size
        if market.startswith("SOL"):
            if size > self.max_trade_size:
                logger.warning(f"Trade size {size} exceeds maximum allowed {self.max_trade_size}")
                return False
                
        # For other markets, apply a conversion (simplified version)
        # In a real implementation, you'd calculate the SOL equivalent value
        else:
            # Apply a conservative estimate for other markets
            adjusted_size = size * 10  # Arbitrary multiplier for demonstration
            if adjusted_size > self.max_trade_size:
                logger.warning(f"Estimated value exceeds maximum allowed {self.max_trade_size}")
                return False
                
        return True
    
    async def drift_perp_trade(self, 
                             market: str, 
                             size: float, 
                             direction: str, 
                             wallet_name: str = "MAIN",
                             dry_run: bool = False):
        """
        Execute a perpetual futures trade on Drift
        
        Args:
            market: Market symbol (e.g., "SOL-PERP")
            size: Trade size
            direction: Trade direction ("long" or "short")
            wallet_name: Wallet name to use
            dry_run: If True, simulate but don't execute
            
        Returns:
            Trade result dictionary
        """
        # Validate trade size
        if not self.validate_trade_size(market, size):
            return {
                "status": "rejected",
                "reason": "size_limit_exceeded",
                "market": market,
                "size": size
            }
        
        # Prepare trade details
        trade_details = {
            "type": "drift_perp",
            "market": market,
            "size": size,
            "direction": direction,
            "wallet": wallet_name,
            "test_mode": dry_run or self.test_mode
        }
        
        # Get confirmation
        if not dry_run and not self.test_mode:
            if not self._confirm_trade(trade_details):
                return {
                    "status": "rejected",
                    "reason": "user_declined",
                    "details": trade_details
                }
        
        # Log trade
        self._log_trade(trade_details)
        
        try:
            # Convert market to index
            market_indices = {
                "SOL-PERP": 0,
                "BTC-PERP": 1,
                "ETH-PERP": 2
            }
            
            if market not in market_indices:
                return {
                    "status": "rejected",
                    "reason": "unsupported_market",
                    "market": market
                }
                
            market_index = market_indices[market]
            
            # Initialize adapter
            adapter = DriftAdapter()
            await adapter.connect()
            
            # Test mode or dry run
            if dry_run or self.test_mode:
                logger.info(f"TEST MODE: Would place {direction} order for {size} on {market}")
                return {
                    "status": "simulated",
                    "market": market,
                    "size": size,
                    "direction": direction,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Execute real trade
            order_result = await adapter.place_perp_order(
                market=market,
                side=direction,
                size=size,
                order_type="market"
            )
            
            # Log successful trade
            self._log_trade(trade_details, "executed")
            
            return {
                "status": "success",
                "result": order_result
            }
            
        except Exception as e:
            logger.error(f"Error executing drift perp trade: {e}")
            # Log failed trade
            self._log_trade(trade_details, "failed")
            
            return {
                "status": "failed",
                "reason": str(e),
                "details": trade_details
            }
    
    async def jupiter_swap(self, 
                          market: str, 
                          input_amount: float, 
                          wallet_name: str = "MAIN",
                          dry_run: bool = False):
        """
        Execute a token swap via Jupiter
        
        Args:
            market: Market symbol (e.g., "SOL-USDC")
            input_amount: Amount of input token
            wallet_name: Wallet name to use
            dry_run: If True, simulate but don't execute
            
        Returns:
            Swap result dictionary
        """
        # Validate trade size
        if not self.validate_trade_size(market, input_amount):
            return {
                "status": "rejected",
                "reason": "size_limit_exceeded",
                "market": market,
                "input_amount": input_amount
            }
        
        # Prepare trade details
        trade_details = {
            "type": "jupiter_swap",
            "market": market,
            "input_amount": input_amount,
            "wallet": wallet_name,
            "slippage_bps": self.slippage_bps,
            "test_mode": dry_run or self.test_mode
        }
        
        # Get confirmation
        if not dry_run and not self.test_mode:
            if not self._confirm_trade(trade_details):
                return {
                    "status": "rejected",
                    "reason": "user_declined",
                    "details": trade_details
                }
        
        # Log trade
        self._log_trade(trade_details)
        
        try:
            # Initialize adapter
            adapter = JupiterAdapter()
            await adapter.connect()
            
            # Test mode or dry run
            if dry_run or self.test_mode:
                logger.info(f"TEST MODE: Would swap {input_amount} on {market}")
                return {
                    "status": "simulated",
                    "market": market,
                    "input_amount": input_amount,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Execute real swap
            swap_result = await adapter.execute_swap(
                market=market,
                input_amount=input_amount,
                slippage_bps=self.slippage_bps
            )
            
            # Log successful swap
            self._log_trade(trade_details, "executed")
            
            return {
                "status": "success",
                "result": swap_result
            }
            
        except Exception as e:
            logger.error(f"Error executing Jupiter swap: {e}")
            # Log failed swap
            self._log_trade(trade_details, "failed")
            
            return {
                "status": "failed",
                "reason": str(e),
                "details": trade_details
            }
    
    async def check_balances(self, wallet_name: str = "MAIN"):
        """
        Check balances for a wallet
        
        Args:
            wallet_name: Wallet name to check
        """
        try:
            # Initialize account manager
            manager = DriftAccountManager()
            await manager.setup()
            
            # Show balances
            await manager.show_balances()
            
        except Exception as e:
            logger.error(f"Error checking balances: {e}")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Mainnet Trading with Enhanced Security")
    
    # Global options
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--wallet", type=str, default="MAIN", help="Wallet to use")
    parser.add_argument("--dry-run", action="store_true", help="Simulate but don't execute")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Drift perp order command
    drift_parser = subparsers.add_parser("drift", help="Execute Drift perp order")
    drift_parser.add_argument("--market", type=str, required=True, choices=["SOL-PERP", "BTC-PERP", "ETH-PERP"], help="Market to trade")
    drift_parser.add_argument("--size", type=float, required=True, help="Trade size")
    drift_parser.add_argument("--direction", type=str, required=True, choices=["long", "short"], help="Trade direction")
    
    # Jupiter swap command
    jup_parser = subparsers.add_parser("jupiter", help="Execute Jupiter swap")
    jup_parser.add_argument("--market", type=str, required=True, help="Market to trade (e.g. SOL-USDC)")
    jup_parser.add_argument("--amount", type=float, required=True, help="Input amount")
    
    # Balance check command
    balance_parser = subparsers.add_parser("balance", help="Check balances")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create mainnet trading instance
    trading = MainnetTrading(config_path=args.config)
    
    # Override settings from command line
    if args.force:
        trading.requires_confirmation = False
    
    # Execute command
    if args.command == "drift":
        result = await trading.drift_perp_trade(
            market=args.market,
            size=args.size,
            direction=args.direction,
            wallet_name=args.wallet,
            dry_run=args.dry_run
        )
        print("\nTrade Result:")
        print(json.dumps(result, indent=2))
        
    elif args.command == "jupiter":
        result = await trading.jupiter_swap(
            market=args.market,
            input_amount=args.amount,
            wallet_name=args.wallet,
            dry_run=args.dry_run
        )
        print("\nSwap Result:")
        print(json.dumps(result, indent=2))
        
    elif args.command == "balance":
        await trading.check_balances(wallet_name=args.wallet)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())