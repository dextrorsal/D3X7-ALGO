#!/usr/bin/env python3
"""
Basic examples of using the Jupiter adapter for DEX operations
"""

import asyncio
import logging
from tabulate import tabulate
from src.trading.jup.jup_adapter import JupiterAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def show_account_overview(adapter: JupiterAdapter):
    """Display comprehensive account overview"""
    # Get account balances
    balances = await adapter.get_account_balances()
    
    print("\n=== ACCOUNT OVERVIEW ===")
    
    # Format balances
    balance_data = [[
        token,
        f"{amount:.6f}",
        f"${await adapter.get_market_price(f'{token}-USDC') * amount:.2f}" if token != "USDC" else f"${amount:.2f}"
    ] for token, amount in balances.items()]
    
    print(tabulate(balance_data, headers=['Token', 'Amount', 'Value (USD)'], tablefmt='simple'))

async def execute_sample_swap(adapter: JupiterAdapter):
    """Example of executing a token swap"""
    try:
        # Get SOL-USDC price
        sol_price = await adapter.get_market_price("SOL-USDC")
        print(f"\nCurrent SOL-USDC price: ${sol_price:.2f}")
        
        # Get route options for a small swap
        routes = await adapter.get_route_options("SOL-USDC", 0.1)
        print("\nAvailable Routes:")
        for i, route in enumerate(routes[:3], 1):  # Show top 3 routes
            print(f"{i}. Rate: ${route['price']:.2f} | Impact: {route['priceImpactPct']:.2f}%")
        
        # Execute a small swap (commented out for safety)
        """
        result = await adapter.execute_swap(
            market="SOL-USDC",
            input_amount=0.1,
            slippage_bps=50  # 0.5% slippage
        )
        print(f"\nSwap executed:")
        print(f"Input: 0.1 SOL")
        print(f"Output: {result['outputAmount']} USDC")
        print(f"Transaction: {result['transaction']}")
        """
        
    except Exception as e:
        logger.error(f"Error executing swap: {str(e)}")

async def monitor_prices(adapter: JupiterAdapter):
    """Monitor prices for multiple markets"""
    markets = ["SOL-USDC", "BTC-USDC", "ETH-USDC"]
    
    print("\nMonitoring prices (press Ctrl+C to exit)...")
    while True:
        prices = {}
        for market in markets:
            prices[market] = await adapter.get_market_price(market)
        
        print("\033[2J\033[H")  # Clear screen
        print("=== MARKET PRICES ===")
        price_data = [[
            market,
            f"${price:,.2f}",
            "🔼" if price > prices.get(f"{market}_last", 0) else "🔽"
        ] for market, price in prices.items()]
        
        print(tabulate(price_data, headers=['Market', 'Price', 'Move'], tablefmt='simple'))
        
        # Store last prices
        for market, price in prices.items():
            prices[f"{market}_last"] = price
            
        await asyncio.sleep(1)

async def main():
    """Example usage of JupiterAdapter"""
    adapter = JupiterAdapter()
    
    try:
        # Initialize adapter
        await adapter.connect()
        logger.info("Jupiter adapter initialized successfully")
        
        # Show account overview
        await show_account_overview(adapter)
        
        # Show sample swap (route finding)
        await execute_sample_swap(adapter)
        
        # Monitor prices
        await monitor_prices(adapter)
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise 