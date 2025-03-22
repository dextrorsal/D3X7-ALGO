#!/usr/bin/env python3
"""
Basic examples of using the Drift adapter for various operations
"""

import asyncio
import logging
from tabulate import tabulate
from src.trading.drift.drift_adapter import DriftAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def show_account_overview(adapter: DriftAdapter, subaccount_id: int = 0):
    """Display comprehensive account overview"""
    # Get risk metrics
    metrics = await adapter.get_risk_metrics(subaccount_id)
    
    print("\n=== ACCOUNT OVERVIEW ===")
    print(f"Total Collateral: ${metrics['collateral']['total']:,.2f}")
    
    if metrics['spot_positions']:
        print("\nSpot Positions:")
        spot_data = [[
            pos['market'],
            f"{pos['amount']:.6f}",
            f"${pos['price']:.2f}",
            f"${pos['value']:.2f}"
        ] for pos in metrics['spot_positions']]
        print(tabulate(spot_data, headers=['Market', 'Amount', 'Price', 'Value'], tablefmt='simple'))
    
    if metrics['perp_positions']:
        print("\nPerpetual Positions:")
        perp_data = [[
            pos['market'],
            f"{pos['size']:.6f}",
            f"${pos['entry_price']:.2f}",
            f"${pos['current_price']:.2f}",
            f"${pos['unrealized_pnl']:.2f}"
        ] for pos in metrics['perp_positions']]
        print(tabulate(perp_data, 
              headers=['Market', 'Size', 'Entry', 'Current', 'PnL'], 
              tablefmt='simple'))
    
    if 'risk_metrics' in metrics:
        print("\nRisk Metrics:")
        print(f"Free Collateral: ${metrics['risk_metrics']['free_collateral']:,.2f}")
        print(f"Margin Requirement: ${metrics['risk_metrics']['margin_requirement']:,.2f}")
        print(f"Current Leverage: {metrics['risk_metrics']['leverage']:.2f}x")
        print(f"Collateral Utilization: {metrics['risk_metrics']['utilization']*100:.1f}%")

async def place_sample_trades(adapter: DriftAdapter, subaccount_id: int = 0):
    """Example of placing different types of orders"""
    try:
        # Get SOL-PERP price
        sol_price = await adapter.get_market_price("SOL-PERP")
        print(f"\nCurrent SOL-PERP price: ${sol_price:.2f}")
        
        # Place a limit buy 5% below market
        limit_price = sol_price * 0.95
        order = await adapter.place_order(
            market="SOL-PERP",
            side="buy",
            size=0.1,
            price=limit_price,
            order_type="limit",
            post_only=True,
            subaccount_id=subaccount_id
        )
        print(f"\nPlaced limit buy order:")
        print(f"Size: 0.1 SOL")
        print(f"Price: ${limit_price:.2f}")
        print(f"Transaction: {order['transaction']}")
        
    except Exception as e:
        logger.error(f"Error placing orders: {str(e)}")

async def main():
    """Example usage of DriftAdapter"""
    adapter = DriftAdapter()
    
    try:
        # Initialize with default wallet
        await adapter.initialize(wallet_name="MAIN")
        logger.info("Drift adapter initialized successfully")
        
        # Show account overview
        await show_account_overview(adapter)
        
        # Place sample trades
        await place_sample_trades(adapter)
        
        # Monitor prices
        print("\nMonitoring prices (press Ctrl+C to exit)...")
        while True:
            sol_price = await adapter.get_market_price("SOL-PERP")
            btc_price = await adapter.get_market_price("BTC-PERP")
            eth_price = await adapter.get_market_price("ETH-PERP")
            
            print("\033[2J\033[H")  # Clear screen
            print("=== MARKET PRICES ===")
            print(f"SOL-PERP: ${sol_price:,.2f}")
            print(f"BTC-PERP: ${btc_price:,.2f}")
            print(f"ETH-PERP: ${eth_price:,.2f}")
            
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        await adapter.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise 