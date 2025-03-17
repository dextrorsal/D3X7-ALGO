#!/usr/bin/env python3
import asyncio
import logging
from src.exchanges.jup import JupiterHandler
from src.core.config import ExchangeConfig, ExchangeCredentials

async def check_balances():
    logging.basicConfig(level=logging.INFO)
    
    # Create exchange config for Jupiter
    config = ExchangeConfig(
        name="jupiter",
        enabled=True,
        credentials=ExchangeCredentials(),
        rate_limit=10,
        markets=["SOL-USDC", "BTC-USDC", "ETH-USDC"],
        base_url="https://quote-api.jup.ag/v6"
    )
    
    handler = JupiterHandler(config)
    
    print('\nConnecting to Jupiter...')
    await handler.start()
    
    print('\nJupiter Account Details:')
    print('------------------------')
    
    try:
        # Get wallet address
        wallet = await handler.get_wallet_address()
        print(f'Wallet Address: {wallet}')
        
        # Get token balances
        balances = await handler.get_token_balances()
        print('\nToken Balances:')
        for token, amount in balances.items():
            print(f'{token}: {amount}')
            
        # Get market prices for context
        print('\nCurrent Market Prices:')
        for market in ['SOL-USDC', 'BTC-USDC', 'ETH-USDC']:
            try:
                price = await handler.get_market_price(market)
                print(f'{market}: ${price:.2f}')
            except Exception as e:
                print(f'Error getting {market} price: {str(e)}')
                continue
    except Exception as e:
        print(f'Error: {str(e)}')
    finally:
        await handler.stop()

if __name__ == "__main__":
    asyncio.run(check_balances())