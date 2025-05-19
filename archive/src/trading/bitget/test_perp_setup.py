import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path
import argparse

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / 'exchanges'))

from bitget.bitget.client import Client
from bitget.bitget.consts import GET, POST
from bitget.bitget.exceptions import BitgetAPIException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_api_credentials(creds_path: str) -> Dict[str, str]:
    """Load API credentials from JSON file."""
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
            # Check for direct Bitget credentials format
            if all(k in creds for k in ['api_key', 'api_secret_key', 'passphrase']):
                return creds
            elif all(k in creds for k in ['apiKey', 'secret', 'passphrase']):
                return {
                    'api_key': creds['apiKey'],
                    'api_secret_key': creds['secret'],
                    'passphrase': creds['passphrase']
                }
            else:
                raise ValueError("Invalid credentials format. Required: api_key, api_secret_key, passphrase")
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        raise

class BitgetAccountViewer:
    """Safe viewer class for Bitget account information - NO TRADING FUNCTIONALITY."""
    
    def __init__(self, creds_path: str):
        self.creds = load_api_credentials(creds_path)
        self.client = Client(
            api_key=self.creds['api_key'],
            api_secret_key=self.creds['api_secret_key'],
            passphrase=self.creds['passphrase']
        )

    def get_markets(self) -> Dict:
        """Get available USDT perpetual markets."""
        response = self.client._request_with_params(GET, '/api/mix/v1/market/contracts', {'productType': 'UMCBL'})
        if not isinstance(response, dict) or 'data' not in response:
            raise ValueError(f"Unexpected markets response format: {response}")
        return response['data']

    def get_account_info(self, symbol: str = 'BTCUSDT_UMCBL') -> Dict:
        """Get account information for a specific symbol."""
        return self.client._request_with_params(GET, '/api/mix/v1/account/account', {'symbol': symbol})

    def get_positions(self) -> Dict:
        """Get all current positions."""
        return self.client._request_with_params(GET, '/api/mix/v1/position/allPosition', {'productType': 'UMCBL'})

    def display_account_overview(self):
        """Display a comprehensive account overview."""
        try:
            # Get and display positions first
            positions = self.get_positions()
            if positions.get('data'):
                logger.info("\n=== Current Positions ===")
                for pos in positions['data']:
                    symbol = pos.get('symbol', 'UNKNOWN')
                    size = float(pos.get('total', '0'))
                    side = pos.get('holdSide', 'UNKNOWN')
                    margin = float(pos.get('margin', '0'))
                    unrealized_pnl = float(pos.get('unrealizedPL', '0'))
                    
                    logger.info(f"""
Symbol: {symbol}
Side: {side}
Size: {size}
Margin: {margin:.2f} USDT
Unrealized PnL: {unrealized_pnl:.2f} USDT
------------------------""")
            else:
                logger.info("\n=== No Open Positions ===")

            # Get and display account information
            account = self.get_account_info()
            if account.get('data'):
                acc_data = account['data'][0]
                logger.info("\n=== Account Summary ===")
                logger.info(f"""
Total Equity: {float(acc_data.get('usdtEquity', 0)):.2f} USDT
Available Balance: {float(acc_data.get('available', 0)):.2f} USDT
Margin Balance: {float(acc_data.get('marginBalance', 0)):.2f} USDT
Margin Ratio: {float(acc_data.get('marginRatio', 0)):.2%}
------------------------""")

        except Exception as e:
            logger.error(f"Error getting account overview: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Bitget Account Viewer - READ ONLY')
    parser.add_argument('--creds', type=str, default='/home/dex/keys/BITGET_KEY.json',
                      help='Path to credentials JSON file')
    parser.add_argument('--action', type=str, choices=['overview', 'markets'],
                      default='overview', help='Action to perform')
    
    args = parser.parse_args()
    
    try:
        viewer = BitgetAccountViewer(args.creds)
        
        if args.action == 'overview':
            viewer.display_account_overview()
        elif args.action == 'markets':
            markets = viewer.get_markets()
            logger.info("\n=== Available USDT-M Markets ===")
            for market in markets:
                symbol = market.get('symbol', 'UNKNOWN')
                status = market.get('symbolStatus', 'UNKNOWN')
                min_size = float(market.get('minTradeNum', 0))
                maker_fee = float(market.get('makerFeeRate', 0))
                taker_fee = float(market.get('takerFeeRate', 0))
                
                logger.info(f"""
Symbol: {symbol}
Status: {status}
Min Trade Size: {min_size}
Maker Fee: {maker_fee:.4%}
Taker Fee: {taker_fee:.4%}
------------------------""")
                
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 