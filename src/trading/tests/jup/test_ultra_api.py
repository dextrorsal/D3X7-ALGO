"""
Test script for Jupiter Ultra API features
"""

import asyncio
import logging
import json
import os
import base64
from datetime import datetime
from src.trading.jup.jup_adapter import JupiterAdapter
from solders.transaction import VersionedTransaction

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_ultra_features():
    """Test Jupiter Ultra API features"""
    logger.info("\n=== Testing Jupiter Ultra API Features on Devnet ===")
    
    adapter = None
    try:
        # Initialize adapter with devnet
        adapter = JupiterAdapter(network="devnet")
        logger.info(f"✓ Connected to Jupiter on devnet with wallet: {adapter.wallet.pubkey}")
        
        # Test getting a quote for SOL -> TEST
        market = "SOL-TEST"
        input_amount = 0.1  # 0.1 SOL
        
        # Get order from Ultra API
        order = await adapter.get_ultra_quote(market, input_amount)
        logger.info(f"Order response: {json.dumps(order, indent=2)}")
        
        if not order or "error" in order:
            raise Exception(f"Failed to get order: {order.get('error') if order else 'No order returned'}")
            
        logger.info(f"✓ Got order for {input_amount} SOL -> TEST")
        logger.info(f"  Request ID: {order.get('requestId')}")
        logger.info(f"  Input amount: {order.get('inAmount')} SOL")
        logger.info(f"  Output amount: {order.get('outAmount')} TEST")
        logger.info(f"  Price impact: {order.get('priceImpactPct', 0.0)}%")
        logger.info(f"  Swap type: {order.get('swapType', 'unknown')}")
        
        # Check if we got a transaction to sign
        if "transaction" in order:
            logger.info("✓ Order includes transaction to sign")
        else:
            logger.info("Note: Order does not include transaction (this is normal for RFQ orders)")
        
        logger.info("✓ Successfully tested Jupiter Ultra API order functionality")
                
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
        
    finally:
        if adapter:
            await adapter.close()
            logger.info("Disconnected from Jupiter API")

async def main():
    """Main entry point"""
    try:
        await test_ultra_features()
        logger.info("\n✅ All Ultra API tests completed successfully!")
    except Exception as e:
        logger.error("\n❌ Some tests failed")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 