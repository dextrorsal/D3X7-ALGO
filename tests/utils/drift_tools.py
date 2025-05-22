#!/usr/bin/env python3
import asyncio
import logging
import json
import os
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from driftpy.drift_client import DriftClient
from solana.rpc.async_api import AsyncClient
from anchorpy import Wallet
from solders.keypair import Keypair
from src.trading.drift.drift_adapter import DriftAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DriftTools:
    def __init__(self, rpc_url_or_adapter: Union[str, DriftAdapter, None] = None):
        if isinstance(rpc_url_or_adapter, DriftAdapter):
            self.adapter = rpc_url_or_adapter
            self.rpc_url = None
        else:
            self.adapter = None
            self.rpc_url = rpc_url_or_adapter or os.environ.get(
                "HELIUS_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com"
            )
        self.client = None
        logger.info(
            f"Initialized DriftTools with {'adapter' if self.adapter else 'RPC URL: ' + str(self.rpc_url)}"
        )

    async def connect(self) -> None:
        if self.client is not None:
            return
        try:
            if self.adapter:
                # Use the adapter's client if available
                if self.adapter.client:
                    self.client = self.adapter.client
                    return
                # Otherwise, let the adapter connect
                await self.adapter.connect()
                self.client = self.adapter.client
                if not self.client:
                    raise ValueError("Failed to get client from adapter")
            else:
                # Connect using RPC URL
                wallet = Wallet(Keypair())
                connection = AsyncClient(self.rpc_url)
                # Determine network from RPC URL
                network = (
                    "devnet" if self.rpc_url and "devnet" in self.rpc_url else "mainnet"
                )
                # Initialize with simpler parameters
                self.client = DriftClient(
                    connection=connection, wallet=wallet, env=network
                )
                await self.client.initialize()  # Ensure client is initialized
            await self.client.subscribe()
            logger.info("Connected to Drift Protocol")
        except Exception as e:
            logger.error(f"Failed to connect to Drift Protocol: {e}")
            raise

    async def get_markets(self) -> List[Dict[str, Any]]:
        await self.connect()
        markets = []
        try:
            logger.info("DriftTools: Attempting to get perp market accounts...")
            # Check if the method returns a coroutine or directly a list
            perp_markets_result = self.client.get_perp_market_accounts()
            logger.info(
                f"DriftTools: perp_markets_result type: {type(perp_markets_result)}"
            )

            if asyncio.iscoroutine(perp_markets_result):
                logger.info("DriftTools: awaiting perp_markets_result coroutine")
                perp_markets = await perp_markets_result
            else:
                logger.info(
                    "DriftTools: using perp_markets_result directly (not a coroutine)"
                )
                perp_markets = perp_markets_result

            logger.info(
                f"DriftTools: Got {len(perp_markets) if perp_markets else 0} perp markets"
            )

            # Debug the first market structure
            if perp_markets and len(perp_markets) > 0:
                perp_market_sample = perp_markets[0]
                logger.info(
                    f"DriftTools: Sample perp market attrs: {dir(perp_market_sample)}"
                )
                logger.info(
                    f"DriftTools: Sample perp market name type: {type(perp_market_sample.name)}"
                )
                # Check if name is a ListContainer
                if hasattr(perp_market_sample.name, "__iter__") and not isinstance(
                    perp_market_sample.name, (str, bytes)
                ):
                    logger.info(
                        f"DriftTools: Name is iterable, converting to string: {list(perp_market_sample.name)}"
                    )

            # Debug AMM structure
            if hasattr(perp_market_sample, "amm"):
                logger.info(
                    f"DriftTools: AMM attributes: {dir(perp_market_sample.amm)}"
                )

            for i, perp_market in enumerate(perp_markets):
                status_str = str(perp_market.status)
                logger.info(
                    f"DriftTools: Processing perp market {i}, status: {status_str}"
                )

                # Check if the market is not initialized (Active, FundingPaused, AmmPaused, etc all indicate active markets)
                # Status "Initialized" is the only one we want to exclude
                if "Initialized" not in status_str:
                    # Handle ListContainer name
                    if hasattr(perp_market.name, "__iter__") and not isinstance(
                        perp_market.name, (str, bytes)
                    ):
                        # Convert ListContainer to string by joining the bytes
                        name_bytes = bytes(perp_market.name)
                        market_name = name_bytes.decode("utf-8").strip("\x00")
                    else:
                        # Use original method if name is bytes
                        market_name = perp_market.name.decode("utf-8").strip("\x00")

                    market_symbol = f"{market_name}-PERP"

                    # Get price safely - check different attributes structures
                    price = None
                    if hasattr(perp_market.amm, "oracle_price_data") and hasattr(
                        perp_market.amm.oracle_price_data, "price"
                    ):
                        price = (
                            perp_market.amm.oracle_price_data.price / QUOTE_PRECISION
                        )
                    elif hasattr(perp_market.amm, "oracle") and hasattr(
                        perp_market.amm.oracle, "price"
                    ):
                        price = perp_market.amm.oracle.price / QUOTE_PRECISION
                    elif hasattr(perp_market.amm, "last_oracle_price"):
                        price = perp_market.amm.last_oracle_price / QUOTE_PRECISION
                    elif hasattr(perp_market.amm, "last_mark_price_twap"):
                        price = perp_market.amm.last_mark_price_twap / QUOTE_PRECISION
                    else:
                        logger.warning(
                            f"DriftTools: Could not find price for market {market_symbol}, using default"
                        )
                        price = 0.0  # Default value when price is not available

                    market_info = {
                        "symbol": market_symbol,
                        "name": market_name,
                        "market_index": perp_market.market_index,
                        "price": price,
                        "type": "perp",
                    }
                    markets.append(market_info)
                    logger.info(f"DriftTools: Added perp market: {market_info}")
                else:
                    logger.info(
                        f"DriftTools: Skipped perp market with status {status_str}"
                    )

            logger.info("DriftTools: Attempting to get spot market accounts...")
            # Check if the method returns a coroutine or directly a list
            spot_markets_result = self.client.get_spot_market_accounts()
            logger.info(
                f"DriftTools: spot_markets_result type: {type(spot_markets_result)}"
            )

            if asyncio.iscoroutine(spot_markets_result):
                logger.info("DriftTools: awaiting spot_markets_result coroutine")
                spot_markets = await spot_markets_result
            else:
                logger.info(
                    "DriftTools: using spot_markets_result directly (not a coroutine)"
                )
                spot_markets = spot_markets_result

            logger.info(
                f"DriftTools: Got {len(spot_markets) if spot_markets else 0} spot markets"
            )

            # Debug the first spot market structure if available
            if spot_markets and len(spot_markets) > 0:
                spot_market_sample = spot_markets[0]
                logger.info(
                    f"DriftTools: Sample spot market attrs: {dir(spot_market_sample)}"
                )
                # Debug spot market name
                if hasattr(spot_market_sample, "name"):
                    logger.info(
                        f"DriftTools: Sample spot market name type: {type(spot_market_sample.name)}"
                    )

            for i, spot_market in enumerate(spot_markets):
                status_str = str(spot_market.status)
                logger.info(
                    f"DriftTools: Processing spot market {i}, status: {status_str}"
                )

                # Check if the market is not initialized
                if "Initialized" not in status_str:
                    # Handle ListContainer name
                    if hasattr(spot_market.name, "__iter__") and not isinstance(
                        spot_market.name, (str, bytes)
                    ):
                        # Convert ListContainer to string by joining the bytes
                        name_bytes = bytes(spot_market.name)
                        market_name = name_bytes.decode("utf-8").strip("\x00")
                    else:
                        # Use original method if name is bytes
                        market_name = spot_market.name.decode("utf-8").strip("\x00")

                    market_symbol = f"{market_name}-SPOT"

                    # Get price safely
                    price = None
                    if (
                        hasattr(spot_market, "oracle_price")
                        and spot_market.oracle_price
                    ):
                        price = spot_market.oracle_price / QUOTE_PRECISION
                    elif hasattr(spot_market, "oracle") and hasattr(
                        spot_market.oracle, "price"
                    ):
                        price = spot_market.oracle.price / QUOTE_PRECISION
                    else:
                        logger.warning(
                            f"DriftTools: Could not find price for market {market_symbol}, using default"
                        )
                        price = 0.0  # Default value when price is not available

                    market_info = {
                        "symbol": market_symbol,
                        "name": market_name,
                        "market_index": spot_market.market_index,
                        "price": price,
                        "type": "spot",
                    }
                    markets.append(market_info)
                    logger.info(f"DriftTools: Added spot market: {market_info}")
                else:
                    logger.info(
                        f"DriftTools: Skipped spot market with status {status_str}"
                    )

            logger.info(f"DriftTools: Total markets: {len(markets)}")
        except Exception as e:
            logger.error(f"DriftTools: Failed to get markets: {e}")
            raise
        return markets

    async def get_prices(
        self, markets: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        if markets is None:
            markets = await self.get_markets()
        return {market["symbol"]: market["price"] for market in markets}

    async def save_markets_to_file(self, filename: str = "drift_markets.json") -> str:
        markets = await self.get_markets()
        data = {"timestamp": datetime.now(timezone.utc).isoformat(), "markets": markets}
        try:
            with open(filename, "w") as f:
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
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(prices)} prices to {filename}")
        except Exception as e:
            logger.error(f"Failed to save prices to file: {e}")
            raise
        return filename


async def main():
    parser = argparse.ArgumentParser(description="Drift Protocol Tools")
    parser.add_argument(
        "command",
        choices=["markets", "prices", "save-markets", "save-prices"],
        help="Command to execute",
    )
    parser.add_argument(
        "--rpc",
        help="Solana RPC URL",
        default=os.environ.get(
            "HELIUS_RPC_ENDPOINT", "https://api.mainnet-beta.solana.com"
        ),
    )
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
