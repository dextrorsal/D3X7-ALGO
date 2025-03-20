#!/usr/bin/env python3
"""
Test script to verify security features integration with Drift
"""

import asyncio
import logging
from typing import Dict
import time

from driftpy.types import OrderParams, PositionDirection
from src.trading.devnet.drift_auth import DriftHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_security_features():
    """Test all integrated security features"""
    helper = DriftHelper()
    
    try:
        # 1. Initialize and perform security audit
        logger.info("\n=== Testing Security Initialization ===")
        drift_client = await helper.initialize_drift()
        
        audit_results = helper.perform_security_audit()
        logger.info("\nSecurity Audit Results:")
        for check in audit_results['checks']:
            logger.info(f"{check['name']}: {check['status']}")
            
        # 2. Test session timeout
        logger.info("\n=== Testing Session Management ===")
        helper.security_manager.session_timeout = 5  # Set to 5 seconds for testing
        logger.info("Waiting for session timeout...")
        time.sleep(6)
        
        # Try to place an order (should fail due to timeout)
        logger.info("\n=== Testing Order Placement After Timeout ===")
        try:
            order_params = OrderParams(
                order_type=0,  # MARKET order type
                market_type=0,  # SPOT market type
                direction=0,  # LONG direction
                base_asset_amount=int(0.1 * 1e9),  # 0.1 SOL
                market_index=1,  # SOL-USDC market
                price=100 * 1e6  # Price in quote precision (USDC)
            )
            
            await helper.place_order(
                order_params,
                market_name="SOL/USDC",
                value=100.0
            )
        except Exception as e:
            logger.info(f"Expected timeout error: {e}")
            
        # 3. Test transaction confirmation
        logger.info("\n=== Testing Transaction Confirmation ===")
        # Reset session
        helper.security_manager.update_activity()
        
        # Try to place an order (should require confirmation)
        order_params = OrderParams(
            order_type=0,  # MARKET order type
            market_type=0,  # SPOT market type
            direction=0,  # LONG direction
            base_asset_amount=int(0.1 * 1e9),  # 0.1 SOL
            market_index=1,  # SOL-USDC market
            price=100 * 1e6  # Price in quote precision (USDC)
        )
        
        logger.info("Attempting to place order (requires confirmation)...")
        result = await helper.place_order(
            order_params,
            market_name="SOL/USDC",
            value=100.0
        )
        
        if result:
            logger.info("✅ Order placed successfully after confirmation")
        else:
            logger.info("Order was rejected by user")
            
    except Exception as e:
        logger.error(f"Test error: {e}")
    finally:
        if drift_client:
            await drift_client.unsubscribe()
            logger.info("Cleaned up Drift client")

async def main():
    """Run all security tests"""
    try:
        await test_security_features()
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Error running tests: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 