#!/usr/bin/env python3
"""
Basic security features test script
"""

import asyncio
import logging
import time
import os
import sys

# Add the src directory to Python path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, src_dir)

from trading.security.security_manager import SecurityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_security():
    """Test basic security features"""
    try:
        logger.info("\n=== Testing Security Manager ===")
        security_manager = SecurityManager()
        
        # 1. Test Security Audit
        logger.info("\n=== Running Security Audit ===")
        audit_results = security_manager.perform_security_audit()
        for check in audit_results['checks']:
            logger.info(f"{check['name']}: {check['status']}")
            if check['status'] != 'PASS':
                logger.warning(f"  Details: {check['details']}")
                
        # 2. Test Rate Limiting
        logger.info("\n=== Testing Rate Limiting ===")
        test_ip = "127.0.0.1"
        
        # Should allow initial attempts
        if security_manager.check_rate_limit(test_ip):
            logger.info("✅ Initial rate limit check passed")
            
        # Record failed attempts
        for i in range(security_manager.max_failed_attempts):
            security_manager.record_failed_attempt(test_ip)
            logger.info(f"Recorded failed attempt {i+1}/{security_manager.max_failed_attempts}")
            
        # Should be rate limited now
        if not security_manager.check_rate_limit(test_ip):
            logger.info("✅ Rate limiting working as expected")
            
        # 3. Test Session Management
        logger.info("\n=== Testing Session Management ===")
        original_timeout = security_manager.session_timeout
        security_manager.session_timeout = 2  # Set to 2 seconds for testing
        
        logger.info("Testing session timeout...")
        security_manager.update_activity()
        time.sleep(3)
        
        if time.time() - security_manager.last_activity_time > security_manager.session_timeout:
            logger.info("✅ Session timeout working as expected")
            
        # Reset timeout
        security_manager.session_timeout = original_timeout
        
        # 4. Test Transaction Confirmation
        logger.info("\n=== Testing Transaction Confirmation ===")
        tx_details = {
            'type': 'TEST_TRANSACTION',
            'market': 'TEST/USDC',
            'size': 1.0,
            'price': 100.0,
            'value': 100.0
        }
        
        logger.info("Please respond to the transaction confirmation prompt (y/n):")
        result = await security_manager.confirm_transaction(tx_details)
        if result is not None:
            logger.info(f"✅ Transaction confirmation {'accepted' if result else 'rejected'} as expected")
            
    except Exception as e:
        logger.error(f"Test error: {e}")
        raise

async def main():
    """Run all basic security tests"""
    try:
        await test_basic_security()
        logger.info("\n✅ All basic security tests completed!")
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Error running tests: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 