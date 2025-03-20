#!/usr/bin/env python3
"""
🔒 Test suite for enhanced security limits.
Provides visual feedback for test results with color-coded output.
"""

import unittest
from decimal import Decimal
from datetime import datetime, timedelta
import json
import tempfile
import os
from pathlib import Path
from colorama import init, Fore, Style, Back
import time

from security_limits import SecurityLimits

# Initialize colorama for cross-platform color support
init()

class ColorTestResult(unittest.TestResult):
    """Custom test result formatter with colors and emojis."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tests_run = []
        self.start_time = None

    def startTest(self, test):
        self.start_time = time.time()
        test_name = str(test).split(' ')[0]
        # Create a more readable test name from the method name
        readable_name = test_name.replace('test_', '').replace('_', ' ').title()
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Running Test:{Style.RESET_ALL} {Fore.WHITE}{readable_name}{Style.RESET_ALL}")
        super().startTest(test)

    def addSuccess(self, test):
        duration = time.time() - self.start_time
        print(f"{Fore.GREEN}✅ PASSED{Style.RESET_ALL} {Fore.WHITE}({duration:.2f}s){Style.RESET_ALL}")
        super().addSuccess(test)

    def addError(self, test, err):
        print(f"{Fore.RED}❌ ERROR: {err[1]}{Style.RESET_ALL}")
        super().addError(test, err)

    def addFailure(self, test, err):
        print(f"{Fore.RED}❌ FAILED: {err[1]}{Style.RESET_ALL}")
        super().addFailure(test, err)

class TestSecurityLimits(unittest.TestCase):
    """🛡️ Test cases for SecurityLimits class."""
    
    def setUp(self):
        """Initialize test environment."""
        print(f"\n{Fore.BLUE}🔧 Setting up test environment...{Style.RESET_ALL}")
        
        self.test_config = {
            "max_position_size": {
                "SOL-PERP": 2.0,  # Custom test limit
                "BTC-PERP": 0.05
            },
            "max_leverage": {
                "SOL-PERP": 3,  # Custom test limit
                "BTC-PERP": 2
            },
            "daily_volume_limit": 5.0,  # Lower limit for testing
            "emergency_shutdown_triggers": {
                "loss_threshold_pct": 3.0,  # Lower for testing
                "volume_spike_multiplier": 2.0
            }
        }
        
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
            
        self.security = SecurityLimits(config_path=str(self.config_path))
    
    def tearDown(self):
        """Clean up test environment."""
        print(f"{Fore.BLUE}🧹 Cleaning up test environment...{Style.RESET_ALL}")
        if self.config_path.exists():
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_position_size_limits(self):
        """Test position size validation."""
        print(f"\n{Fore.CYAN}Testing Position Size Limits:{Style.RESET_ALL}")
        
        # Test valid position size
        result = self.security.validate_position_size("SOL-PERP", 1.5)
        print(f"  {'✅' if result else '❌'} SOL-PERP position size 1.5: {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
        
        # Test position size exceeding limit
        result = self.security.validate_position_size("SOL-PERP", 2.5)
        print(f"  {'✅' if not result else '❌'} SOL-PERP position size 2.5 (should fail): {Fore.GREEN if not result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertFalse(result)
        
        # Test default limit for unknown market
        result = self.security.validate_position_size("NEW-PERP", 0.05)
        print(f"  {'✅' if result else '❌'} NEW-PERP position size 0.05: {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
    
    def test_leverage_limits(self):
        """Test leverage validation."""
        print(f"\n{Fore.CYAN}Testing Leverage Limits:{Style.RESET_ALL}")
        
        # Test valid leverage
        result = self.security.validate_leverage("SOL-PERP", 2.5)
        print(f"  {'✅' if result else '❌'} SOL-PERP leverage 2.5x: {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
        
        # Test leverage exceeding limit
        result = self.security.validate_leverage("SOL-PERP", 4.0)
        print(f"  {'✅' if not result else '❌'} SOL-PERP leverage 4.0x (should fail): {Fore.GREEN if not result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertFalse(result)
    
    def test_daily_volume_tracking(self):
        """Test daily volume tracking and limits."""
        print(f"\n{Fore.CYAN}Testing Daily Volume Tracking:{Style.RESET_ALL}")
        
        # Test single trade within limit
        result = self.security.update_daily_volume(2.0)
        print(f"  {'✅' if result else '❌'} First trade (2.0): {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
        
        # Test cumulative trades approaching limit
        result = self.security.update_daily_volume(2.0)
        print(f"  {'✅' if result else '❌'} Second trade (2.0): {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
        
        # Test exceeding daily limit
        result = self.security.update_daily_volume(2.0)
        print(f"  {'✅' if not result else '❌'} Third trade (2.0, should fail): {Fore.GREEN if not result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertFalse(result)
    
    def test_emergency_shutdown(self):
        """Test emergency shutdown triggers."""
        print(f"\n{Fore.CYAN}Testing Emergency Shutdown:{Style.RESET_ALL}")
        
        # Test loss threshold trigger
        result = self.security.check_emergency_shutdown(current_loss_pct=4.0)
        print(f"  {'✅' if result else '❌'} Loss threshold trigger (4.0%): {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
        self.assertTrue(self.security.emergency_shutdown)
        
        # Reset and test volume spike
        self.security.reset_emergency_shutdown()
        self.security.daily_volume = Decimal('2.0')
        result = self.security.check_emergency_shutdown(current_volume=5.0)
        print(f"  {'✅' if result else '❌'} Volume spike trigger (5.0): {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)
    
    def test_emergency_shutdown_blocks_trading(self):
        """Test that emergency shutdown prevents new positions."""
        print(f"\n{Fore.CYAN}Testing Emergency Shutdown Trading Block:{Style.RESET_ALL}")
        
        # Trigger emergency shutdown
        self.security.check_emergency_shutdown(current_loss_pct=4.0)
        
        # Verify that new positions are blocked
        result = self.security.validate_position_size("SOL-PERP", 0.1)
        print(f"  {'✅' if not result else '❌'} Position blocked during shutdown: {Fore.GREEN if not result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertFalse(result)
        
        # Reset and verify trading is restored
        self.security.reset_emergency_shutdown()
        result = self.security.validate_position_size("SOL-PERP", 0.1)
        print(f"  {'✅' if result else '❌'} Position allowed after reset: {Fore.GREEN if result else Fore.RED}{result}{Style.RESET_ALL}")
        self.assertTrue(result)

def run_tests():
    """Run the test suite with custom formatting."""
    print(f"\n{Back.BLUE}{Fore.WHITE} 🚀 Running Security Limits Test Suite {Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
    
    # Create a test suite and run with custom result class
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecurityLimits)
    runner = unittest.TextTestRunner(resultclass=ColorTestResult)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Test Summary:{Style.RESET_ALL}")
    print(f"  ✅ Passed: {Fore.GREEN}{result.testsRun - len(result.failures) - len(result.errors)}{Style.RESET_ALL}")
    print(f"  ❌ Failed: {Fore.RED}{len(result.failures)}{Style.RESET_ALL}")
    print(f"  ⚠️ Errors: {Fore.RED}{len(result.errors)}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")

if __name__ == '__main__':
    run_tests() 