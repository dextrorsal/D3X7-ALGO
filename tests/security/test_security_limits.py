"""
Test suite for enhanced security limits.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

from src.trading.mainnet.security_limits import SecurityLimits

@pytest.fixture
def test_config():
    """Fixture for test configuration."""
    return {
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

@pytest.fixture
def security_limits(test_config, tmp_path):
    """Fixture for SecurityLimits instance."""
    config_path = tmp_path / "test_config.json"
    with open(config_path, 'w') as f:
        json.dump(test_config, f)
    
    return SecurityLimits(config_path=str(config_path))

class TestSecurityLimits:
    """Test cases for SecurityLimits class."""
    
    def test_position_size_limits(self, security_limits):
        """Test position size validation."""
        # Test valid position size
        assert security_limits.validate_position_size("SOL-PERP", 1.5)
        
        # Test position size exceeding limit
        assert not security_limits.validate_position_size("SOL-PERP", 2.5)
        
        # Test default limit for unknown market
        assert security_limits.validate_position_size("NEW-PERP", 0.05)
    
    def test_leverage_limits(self, security_limits):
        """Test leverage validation."""
        # Test valid leverage
        assert security_limits.validate_leverage("SOL-PERP", 2.5)
        
        # Test leverage exceeding limit
        assert not security_limits.validate_leverage("SOL-PERP", 4.0)
    
    def test_daily_volume_tracking(self, security_limits):
        """Test daily volume tracking and limits."""
        # Test single trade within limit
        assert security_limits.update_daily_volume(2.0)
        
        # Test cumulative trades approaching limit
        assert security_limits.update_daily_volume(2.0)
        
        # Test exceeding daily limit
        assert not security_limits.update_daily_volume(2.0)
    
    def test_emergency_shutdown(self, security_limits):
        """Test emergency shutdown triggers."""
        # Test loss threshold trigger
        assert security_limits.check_emergency_shutdown(current_loss_pct=4.0)
        assert security_limits.emergency_shutdown
        
        # Reset and test volume spike
        security_limits.reset_emergency_shutdown()
        security_limits.daily_volume = Decimal('2.0')
        assert security_limits.check_emergency_shutdown(current_volume=5.0)
    
    def test_emergency_shutdown_blocks_trading(self, security_limits):
        """Test that emergency shutdown prevents new positions."""
        # Trigger emergency shutdown
        security_limits.check_emergency_shutdown(current_loss_pct=4.0)
        
        # Verify that new positions are blocked
        assert not security_limits.validate_position_size("SOL-PERP", 0.1)
        
        # Reset and verify trading is restored
        security_limits.reset_emergency_shutdown()
        assert security_limits.validate_position_size("SOL-PERP", 0.1) 