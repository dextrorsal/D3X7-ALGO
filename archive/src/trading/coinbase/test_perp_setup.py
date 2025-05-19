"""
Test script to complete Coinbase Perpetual Futures onboarding using official SDK.
"""

import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from coinbase.rest import RESTClient

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_credentials(key_path):
    """Load API credentials from JSON file."""
    try:
        with open(key_path, 'r') as f:
            creds = json.load(f)
        return creds.get('name'), creds.get('privateKey')
    except Exception as e:
        logger.error(f"Failed to load credentials from {key_path}: {e}")
        return None, None

async def check_perp_setup():
    """
    Follow the official documentation steps for perpetual futures setup:
    1. Check if we have a perpetuals portfolio
    2. If not, create one
    3. Allocate funds if needed
    4. Check portfolio summary
    """
    # Load environment variables
    load_dotenv()
    
    # Try both key paths
    key_paths = [
        os.getenv("CDP_KEY_PATH"),
        os.getenv("CDP_KEY_PATH2")
    ]
    
    client = None
    working_key_path = None
    
    # Try each key path until we get a working connection
    for key_path in key_paths:
        if not key_path:
            continue
            
        logger.info(f"\nTrying credentials from: {key_path}")
        api_key, api_secret = load_credentials(key_path)
        
        if not api_key or not api_secret:
            logger.warning(f"Could not load credentials from {key_path}")
            continue
            
        try:
            # Initialize the official Coinbase REST client
            client = RESTClient(api_key=api_key, api_secret=api_secret)
            # Test connection
            accounts = client.get_accounts()
            logger.info("✅ API Connection successful with this key!")
            working_key_path = key_path
            break
        except Exception as e:
            logger.warning(f"Failed to connect with {key_path}: {e}")
            continue
    
    if not client:
        raise ValueError("Could not establish connection with any provided keys")

    results = {
        "has_perp_portfolio": False,
        "portfolio_uuid": None,
        "usdc_balance": 0,
        "sol_balance": 0,
        "portfolio_summary": None,
        "allocation_needed": False
    }

    try:
        # Step 1: Check Account Balances First
        logger.info("\n=== Checking Account Balances ===")
        accounts = client.get_accounts()
        for account in accounts.to_dict().get('accounts', []):
            currency = account['currency']
            if currency in ['SOL', 'USDC']:
                balance = float(account['available_balance']['value'])
                if currency == 'SOL':
                    results['sol_balance'] = balance
                else:
                    results['usdc_balance'] = balance
                logger.info(f"{currency} Balance: {balance}")

        # Step 2: List Portfolios to Find or Create Perpetuals Portfolio
        logger.info("\n=== Checking for Perpetuals Portfolio ===")
        try:
            portfolios = client.list_portfolios()
            logger.info("Available portfolios:")
            print(json.dumps(portfolios.to_dict(), indent=2))
            
            # Look for perpetuals portfolio
            for portfolio in portfolios.to_dict().get('portfolios', []):
                if portfolio.get('name', '').lower().startswith('perp'):
                    results['has_perp_portfolio'] = True
                    results['portfolio_uuid'] = portfolio['uuid']
                    logger.info(f"✅ Found perpetuals portfolio: {portfolio['uuid']}")
                    break
                    
        except Exception as e:
            logger.warning(f"Could not list portfolios: {e}")
            logger.info("You need to complete onboarding at: https://www.coinbase.com/advanced-trade/perpetuals")

        # Step 3: If we have a portfolio, get its summary
        if results['portfolio_uuid']:
            logger.info("\n=== Getting Portfolio Summary ===")
            try:
                summary = client.get_perps_portfolio_summary(portfolio_uuid=results['portfolio_uuid'])
                logger.info("Portfolio summary:")
                print(json.dumps(summary.to_dict(), indent=2))
                results['portfolio_summary'] = summary.to_dict()
                
                # Check if allocation is needed
                total_balance = float(summary.to_dict().get('summary', {}).get('total_balance', {}).get('value', '0'))
                if total_balance < 10:  # Minimum 10 USDC needed
                    results['allocation_needed'] = True
                    
            except Exception as e:
                logger.warning(f"Could not get portfolio summary: {e}")

            # Step 4: If allocation needed and we have USDC, try to allocate
            if results['allocation_needed'] and results['usdc_balance'] >= 10:
                logger.info("\n=== Attempting to Allocate USDC to Portfolio ===")
                try:
                    allocation = client.allocate_portfolio(
                        portfolio_uuid=results['portfolio_uuid'],
                        symbol="SOL-PERP-INTX",  # The trading pair we want to use
                        amount=str(min(results['usdc_balance'], 10)),  # Allocate minimum required
                        currency="USDC"
                    )
                    logger.info("Allocation result:")
                    print(json.dumps(allocation.to_dict(), indent=2))
                except Exception as e:
                    logger.warning(f"Could not allocate funds: {e}")

        return results

    except Exception as e:
        logger.error(f"❌ Error during setup check: {e}")
        raise

def print_next_steps(results):
    logger.info("\n=== Required Steps ===")
    
    # Step 1: Onboarding
    if not results.get('has_perp_portfolio'):
        logger.info("\n1. Complete Perpetuals Onboarding:")
        logger.info("   - Visit: https://www.coinbase.com/advanced-trade/perpetuals")
        logger.info("   - Complete eligibility questionnaire")
        logger.info("   - Enable perpetuals trading")
    else:
        logger.info("✅ Perpetuals portfolio ready")

    # Step 2: USDC Balance
    usdc_balance = results.get('usdc_balance', 0)
    if usdc_balance < 10:
        logger.info("\n2. Increase USDC Balance:")
        logger.info("   - Current USDC: {:.2f}".format(usdc_balance))
        logger.info("   - Need minimum 10 USDC for margin")
        
        # Calculate SOL conversion if needed
        sol_balance = results.get('sol_balance', 0)
        if sol_balance > 0:
            sol_to_convert = min(sol_balance * 0.5, 1.0)
            logger.info(f"   - Consider converting {sol_to_convert:.2f} SOL to USDC")
    else:
        logger.info("✅ Sufficient USDC balance for margin")

    # Step 3: Portfolio Allocation
    if results.get('allocation_needed'):
        logger.info("\n3. Portfolio Allocation Needed:")
        logger.info("   - Need to allocate minimum 10 USDC to your perpetuals portfolio")
        if results.get('portfolio_uuid'):
            logger.info(f"   - Use portfolio UUID: {results['portfolio_uuid']}")
    elif results.get('portfolio_summary'):
        logger.info("\n✅ Portfolio ready for trading")
        summary = results['portfolio_summary'].get('summary', {})
        logger.info(f"   - Buying Power: {summary.get('buying_power', {}).get('value', '0')} {summary.get('buying_power', {}).get('currency', 'USDC')}")
        logger.info(f"   - Total Balance: {summary.get('total_balance', {}).get('value', '0')} {summary.get('total_balance', {}).get('currency', 'USDC')}")

    logger.info("\nNext Steps:")
    if not results.get('has_perp_portfolio'):
        logger.info("1. Complete onboarding first")
    elif usdc_balance < 10:
        logger.info("1. Convert SOL to USDC")
        logger.info("2. Allocate USDC to perpetuals portfolio")
    elif results.get('allocation_needed'):
        logger.info("1. Allocate USDC to perpetuals portfolio")
    else:
        logger.info("✅ Ready to start trading!")
        logger.info("1. You can now create perpetual futures orders")
        logger.info("2. Monitor your positions and margin health")
        logger.info("3. Set up your trading strategy")

if __name__ == "__main__":
    try:
        results = asyncio.run(check_perp_setup())
        print_next_steps(results)
    except Exception as e:
        logger.error(f"Failed to complete setup check: {e}")