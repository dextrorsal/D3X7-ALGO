#!/usr/bin/env python3
import asyncio
import logging
import json
import os
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from driftpy.constants.config import configs
from driftpy.drift_client import DriftClient
from driftpy.accounts import get_perp_market_account, get_spot_market_account
from driftpy.constants.numeric_constants import QUOTE_PRECISION, BASE_PRECISION
from solana.rpc.async_api import AsyncClient
from anchorpy import Provider, Wallet
from solders.keypair import Keypair

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DriftTools:
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or os.environ.get("HELIUS_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com")
        self.client = None
        logger.info(f"Initialized DriftTools with RPC URL: {self.rpc_url}")

    async def connect(self) -> None:
        if self.client is not None:
            return
        try:
            wallet = Wallet(Keypair())
            connection = AsyncClient(self.rpc_url)
            provider = Provider(connection, wallet)
            config = configs["mainnet"]
            self.client = DriftClient(program_id=config.program_id, provider=provider, opts=config.default_opts)
            await self.client.subscribe()
            logger.info("Connected to Drift Protocol")
        except Exception as e:
            logger.error(f"Failed to connect to Drift Protocol: {e}")
            raise

    async def get_markets(self) -> List[Dict[str, Any]]:
        await self.connect()
        markets = []
        try:
            perp_markets = await self.client.get_perp_market_accounts()
            for perp_market in perp_markets:
                if perp_market.status == 1:
                    market_name = perp_market.name.decode('utf-8').strip('\x00')
                    market_symbol = f"{market_name}-PERP"
                    price = perp_market.amm.oracle_price_data.price / QUOTE_PRECISION
                    markets.append({"symbol": market_symbol, "name": market_name, "type": "perpetual", "price": price, "base_decimals": perp_market.base_decimals, "quote_decimals": 6, "status": "active"})

            spot_markets = await self.client.get_spot_market_accounts()
            for spot_market in spot_markets:
                if spot_market.status == 1:
                    market_name = spot_market.name.decode('utf-8').strip('\x00')
                    market_symbol = f"{market_name}-USDC"
                    price = spot_market.oracle_price_data.price / QUOTE_PRECISION
                    markets.append({"symbol": market_symbol, "name": market_name, "type": "spot", "price": price, "base_decimals": spot_market.decimals, "quote_decimals": 6, "status": "active"})
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            raise
        return markets

    async def get_prices(self) -> Dict[str, float]:
        markets = await self.get_markets()
        return {market["symbol"]: market["price"] for market in markets}

    async def save_markets_to_file(self, filename: str = "drift_markets.json") -> str:
        markets = await self.get_markets()
        data = {"timestamp": datetime.now(timezone.utc).isoformat(), "markets": markets}
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(markets)} markets to {filename}")
        except Exception as e:
            logger.error(f"Failed to save markets to file: {e}")
            raise
        return filename

    async def save_prices_to_file(self, filename: str = "drift_prices.json") -> str:
        prices = await self.get_prices()
        data = {"timestamp": datetime.now(timezone.utc).isoformat(), "prices": prices}
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(prices)} prices to {filename}")
        except Exception as e:
            logger.error(f"Failed to save prices to file: {e}")
            raise
        return filename

async def main():
    parser = argparse.ArgumentParser(description="Drift Protocol Tools")
    parser.add_argument("command", choices=["markets", "prices", "save-markets", "save-prices"], help="Command to execute")
    parser.add_argument("--rpc", help="Solana RPC URL", default=os.environ.get("HELIUS_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com"))
    parser.add_argument("--output", "-o", help="Output file for save commands")
    args = parser.parse_args()
    drift_tools = DriftTools(rpc_url=args.rpc)

    try:
        if args.command == "markets":
            markets = await drift_tools.get_markets()
            print(f"Found {len(markets)} markets:")
            for market in markets:
                print(f"  {market['symbol']}: ${market['price']:.4f}")
        elif args.command == "prices":
            prices = await drift_tools.get_prices()
            print(f"Current prices for {len(prices)} markets:")
            for symbol, price in prices.items():
                print(f"  {symbol}: ${price:.4f}")
        elif args.command == "save-markets":
            filename = args.output or "drift_markets.json"
            await drift_tools.save_markets_to_file(filename)
            print(f"Markets saved to {filename}")
        elif args.command == "save-prices":
            filename = args.output or "drift_prices.json"
            await drift_tools.save_prices_to_file(filename)
            print(f"Prices saved to {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())