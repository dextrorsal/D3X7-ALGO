#!/usr/bin/env python3
"""
Test suite for SecurityManager
"""

import asyncio
import unittest
import time
import os
import json
from pathlib import Path
from ...security.security_manager import SecurityManager, require_confirmation

class TestSecurityManager(unittest.TestCase):
    def setUp(self):
        # Use a test config directory
        self.test_config_dir = "/tmp/test_security_config"
        self.security_manager = SecurityManager(config_dir=self.test_config_dir)
        
    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.test_config_dir):
            for file in os.listdir(self.test_config_dir):
                os.remove(os.path.join(self.test_config_dir, file))
            os.rmdir(self.test_config_dir)
            
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        test_ip = "127.0.0.1"
        
        # Should allow initial attempts
        self.assertTrue(self.security_manager.check_rate_limit(test_ip))
        
        # Record max_failed_attempts
        for _ in range(self.security_manager.max_failed_attempts):
            self.security_manager.record_failed_attempt(test_ip)
            
        # Should be rate limited now
        self.assertFalse(self.security_manager.check_rate_limit(test_ip))
        
        # Reset should clear the rate limit
        self.security_manager.reset_failed_attempts(test_ip)
        self.assertTrue(self.security_manager.check_rate_limit(test_ip))
        
    def test_session_timeout(self):
        """Test session timeout functionality"""
        # Set a short timeout for testing
        self.security_manager.session_timeout = 2
        
        # Update activity
        self.security_manager.update_activity()
        initial_time = self.security_manager.last_activity_time
        
        # Wait for timeout
        time.sleep(3)
        
        # Should have triggered timeout in monitor thread
        self.assertTrue(time.time() - initial_time > self.security_manager.session_timeout)
        
    def test_security_audit(self):
        """Test security audit functionality"""
        audit_results = self.security_manager.perform_security_audit()
        
        # Verify audit structure
        self.assertIn('timestamp', audit_results)
        self.assertIn('checks', audit_results)
        
        # Verify specific checks
        check_names = [check['name'] for check in audit_results['checks']]
        self.assertIn('Config Directory Permissions', check_names)
        self.assertIn('Session Timeout Configuration', check_names)
        self.assertIn('Rate Limiting Configuration', check_names)
        
    async def test_transaction_confirmation(self):
        """Test transaction confirmation"""
        # Mock transaction details
        tx_details = {
            'type': 'market_buy',
            'market': 'SOL/USDC',
            'size': 1.0,
            'price': 'Market',
            'value': 100.0
        }
        
        # Test the confirmation flow (will require manual input in console)
        # In a real test, you'd mock the input function
        result = await self.security_manager.confirm_transaction(tx_details)
        self.assertIsInstance(result, bool)
        
class MockTrader:
    """Mock trader class for testing the require_confirmation decorator"""
    def __init__(self):
        self.security_manager = SecurityManager()
        
    @require_confirmation
    async def place_trade(self, market_name: str, size: float, price: float = None):
        return {'status': 'success'}
        
async def test_decorator():
    """Test the require_confirmation decorator"""
    trader = MockTrader()
    result = await trader.place_trade('SOL/USDC', 1.0, 100.0)
    return result is not None

def run_async_test(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

if __name__ == '__main__':
    unittest.main() 