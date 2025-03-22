"""
Test script for running a simplified Jupiter strategy on testnet.
This script is completely isolated from the main implementation and only uses test components.
"""

import asyncio
import logging
import sys
import os
import numpy as np
import aiohttp
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

# Add the project root to the Python path to allow imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# Import only what we need for testing
from src.utils.indicators.supertrend import supertrend
from src.utils.indicators.knn import knnStrategy
from src.trading.tests.test_wallet import TestWallet
from src.core.models import StandardizedCandle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleTestStrategy:
    """A simplified test strategy that uses Jupiter and our indicators."""
    
    def __init__(self, config_dict):
        self.config = config_dict
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized Simple Test Strategy")
        
        # Jupiter Price API v2 endpoint
        self.price_url = "https://api.jup.ag/price/v2"
        
        # Token addresses
        self.sol_mint = "So11111111111111111111111111111111111111112"  # SOL
        self.usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    
    async def fetch_price_data(self, market="SOL-USDC", resolution="1m"):
        """Fetch current price data and simulate historical data for testing."""
        try:
            # For SOL-USDC, we'll use the SOL mint address to get its price in USDC
            if market.upper() == "SOL-USDC":
                token_id = self.sol_mint
            else:
                self.logger.error(f"Market {market} not supported")
                return None
            
            # Use the Jupiter Price API v2
            async with aiohttp.ClientSession() as session:
                params = {
                    "ids": token_id,
                    "showExtraInfo": "true"
                }
                
                async with session.get(self.price_url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Jupiter API error: {response.status} - {error_text}")
                        return None
                    
                    data = await response.json()
                    self.logger.info(f"Jupiter price response: {json.dumps(data, indent=2)}")
                    
                    # Extract the price from the response
                    if "data" in data and token_id in data["data"]:
                        token_data = data["data"][token_id]
                        price = float(token_data["price"])
                        self.logger.info(f"Current SOL price: {price} USDC")
                        
                        # Create a standardized candle
                        current_candle = StandardizedCandle(
                            timestamp=datetime.now(timezone.utc),
                            open=price,
                            high=price,
                            low=price,
                            close=price,
                            volume=0.0,  # Volume not provided by the price API
                            source="jupiter",
                            resolution=resolution,
                            market=market,
                            raw_data=token_data
                        )
                        
                        # Simulate historical data by creating fake candles with slight variations
                        candles = []
                        
                        # Create 20 fake candles with random variations around the current price
                        np.random.seed(42)  # For reproducible results
                        for i in range(20):
                            variation = np.random.uniform(-0.02, 0.02)  # ±2% variation
                            candle_price = price * (1 + variation)
                            
                            # Create a new candle with the varied price
                            candle = StandardizedCandle(
                                timestamp=datetime.now(timezone.utc),
                                open=candle_price * 0.998,
                                high=candle_price * 1.005,
                                low=candle_price * 0.995,
                                close=candle_price,
                                volume=100 + i * 10,  # Fake volume
                                source="jupiter",
                                resolution=resolution,
                                market=market,
                                raw_data=None
                            )
                            candles.append(candle)
                        
                        # Add the current candle at the end
                        candles.append(current_candle)
                        return candles
                    else:
                        self.logger.error(f"Invalid response format: {data}")
                        return None
            
        except Exception as e:
            self.logger.error(f"Error fetching price data: {str(e)}")
            return None
    
    def compute_signals(self, candles):
        """Compute trading signals using our indicators."""
        if not candles or len(candles) < 10:
            self.logger.warning("Not enough data to compute signals")
            return "hold", "hold"
        
        # Extract price data
        closes = [candle.close for candle in candles]
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        volumes = [candle.volume for candle in candles]
        
        # Compute Super Trend signal
        try:
            st_values, directions = supertrend(highs, lows, closes, atr_length=10, factor=3)
            st_signal = "buy" if directions[-1] == 1 else "sell" if directions[-1] == -1 else "hold"
            self.logger.info(f"Super Trend signal: {st_signal}")
        except Exception as e:
            self.logger.error(f"Error computing Super Trend: {e}")
            st_signal = "hold"
        
        # Compute KNN signal
        try:
            knn = knnStrategy()
            knn_result = knn.calculate(closes, volumes)
            knn_signal = "buy" if knn_result == 1 else "sell" if knn_result == -1 else "hold"
            self.logger.info(f"KNN signal: {knn_signal}")
        except Exception as e:
            self.logger.error(f"Error computing KNN: {e}")
            knn_signal = "hold"
        
        return st_signal, knn_signal
    
    def evaluate_signals(self, st_signal, knn_signal):
        """Combine signals to make a trading decision.
        
        For testing purposes, we prioritize the Super Trend signal:
        - If Super Trend says "buy", we buy regardless of KNN
        - If Super Trend says "sell", we sell regardless of KNN
        - If Super Trend says "hold", we check KNN as a secondary indicator
        """
        # Prioritize Super Trend for testing
        if st_signal == "buy":
            return "buy"  # Always follow Super Trend buy signals
        elif st_signal == "sell":
            return "sell"  # Always follow Super Trend sell signals
        else:
            # Only if Super Trend is neutral (hold), consider KNN
            return knn_signal if knn_signal != "hold" else "hold"
    
    async def simulate_transaction(self, decision, wallet, amount_usd=10):
        """Simulate a transaction based on the trading decision.
        
        Args:
            decision (str): The trading decision ("buy", "sell", or "hold")
            wallet (TestWallet): The test wallet to use
            amount_usd (float): The amount in USD to trade
        
        Returns:
            dict: A simulated transaction result
        """
        if decision == "hold":
            self.logger.info("No transaction needed for HOLD decision")
            return None
            
        # Calculate the amount of SOL based on current price
        candles = await self.fetch_price_data()
        if not candles or len(candles) == 0:
            self.logger.error("Cannot simulate transaction: failed to fetch price data")
            return None
            
        current_price = candles[-1].close
        sol_amount = amount_usd / current_price
        
        # Log the transaction details
        action = "BUY" if decision == "buy" else "SELL"
        self.logger.info(f"SIMULATING {action} TRANSACTION:")
        self.logger.info(f"  Wallet: {wallet.get_public_key()}")
        self.logger.info(f"  Amount: {sol_amount:.6f} SOL (${amount_usd:.2f} USD)")
        self.logger.info(f"  Price: ${current_price:.2f} USD per SOL")
        
        # In a real implementation, we would:
        # 1. Get a quote from Jupiter Swap API
        # 2. Create and sign the transaction
        # 3. Submit the transaction to the network
        
        # For now, just return a simulated result
        return {
            "success": True,
            "action": action,
            "sol_amount": sol_amount,
            "usd_amount": amount_usd,
            "price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "wallet": str(wallet.get_public_key()),
            "tx_id": f"SIMULATED_{action}_{datetime.now().timestamp()}"
        }
        
    async def run_test(self):
        """Run a complete test of the strategy."""
        # Fetch price data
        candles = await self.fetch_price_data()
        if not candles:
            self.logger.error("Failed to fetch price data")
            return
        
        # Compute signals
        st_signal, knn_signal = self.compute_signals(candles)
        
        # Evaluate signals
        decision = self.evaluate_signals(st_signal, knn_signal)
        self.logger.info(f"Trading decision: {decision}")
        print(f"Trading decision: {decision}")
        
        return decision

async def run_jup_testnet_strategy():
    """Run the Jupiter strategy on testnet with the test wallet."""
    logger.info("Starting Jupiter testnet strategy test")
    
    # Initialize the test wallet
    wallet = TestWallet()
    
    # Check if a wallet config already exists, or create a new one
    try:
        wallet.load_keypair()
        logger.info(f"Loaded existing test wallet: {wallet.get_public_key()}")
    except (FileNotFoundError, ValueError):
        wallet.generate_new_keypair()
        wallet.save_keypair()
        logger.info(f"Generated new test wallet: {wallet.get_public_key()}")
    
    # Check balance and request an airdrop if needed
    balance = wallet.get_balance()
    logger.info(f"Current balance: {balance} SOL")
    
    if balance is not None and balance < 0.5:
        logger.info("Balance is low, requesting an airdrop...")
        signature = wallet.request_airdrop(1)
        if signature:
            logger.info(f"Airdrop requested. Signature: {signature}")
            # Wait a moment for the airdrop to be processed
            await asyncio.sleep(5)
            new_balance = wallet.get_balance()
            logger.info(f"New balance: {new_balance} SOL")
    
    # Initialize our simple test strategy
    config = {
        "base_url": "",  # base_url is not used for the price endpoint right now
        "testnet": True,
        "wallet_pubkey": str(wallet.get_public_key())
    }
    
    test_strat = SimpleTestStrategy(config)
    
    # Track our transactions
    transactions = []
    
    # Run the strategy for a few iterations to test
    for i in range(3):
        logger.info(f"Running strategy iteration {i+1}/3")
        
        # Get the trading decision
        decision = await test_strat.run_test()
        
        # If we have a buy or sell signal, simulate a transaction
        if decision in ["buy", "sell"]:
            logger.info(f"Got {decision.upper()} signal, simulating transaction...")
            tx_result = await test_strat.simulate_transaction(decision, wallet)
            if tx_result:
                transactions.append(tx_result)
                logger.info(f"Transaction simulated: {tx_result['tx_id']}")
        
        # Wait a bit between iterations
        await asyncio.sleep(5)
    
    # Print a summary of all transactions
    if transactions:
        logger.info("Transaction Summary:")
        for i, tx in enumerate(transactions):
            logger.info(f"  {i+1}. {tx['action']} {tx['sol_amount']:.6f} SOL at ${tx['price']:.2f}")
    else:
        logger.info("No transactions were executed during this test run")
    
    logger.info("Jupiter testnet strategy test completed")

if __name__ == "__main__":
    try:
        asyncio.run(run_jup_testnet_strategy())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error running test: {str(e)}", exc_info=True) 