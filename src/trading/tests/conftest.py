"""
Common test fixtures and configurations for the D3X7-ALGO trading system tests.
"""
import os
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

from src.utils.wallet import WalletManager
from src.trading.mainnet.security_limits import SecurityLimits
from src.trading.drift.drift_adapter import DriftAdapter
from src.trading.jup.jup_adapter import JupiterAdapter

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration with safe limits for testing."""
    return {
        "max_position_size": {
            "SOL-PERP": 0.1,
            "BTC-PERP": 0.001
        },
        "max_leverage": {
            "SOL-PERP": 2,
            "BTC-PERP": 1
        },
        "daily_volume_limit": 1.0,
        "emergency_shutdown_triggers": {
            "loss_threshold_pct": 5.0,
            "volume_spike_multiplier": 2.0
        }
    }

@pytest.fixture
async def wallet_manager():
    """Initialize wallet manager for testing."""
    test_keypair_path = str(Path.home() / ".config/solana/test-keypair.json")
    manager = WalletManager(keypair_path=test_keypair_path)
    yield manager
    await manager.close()

@pytest.fixture
def security_limits(test_config):
    """Initialize security limits with test configuration."""
    return SecurityLimits(test_config)

@pytest.fixture
async def drift_adapter(wallet_manager):
    """Initialize Drift adapter for testing."""
    adapter = DriftAdapter(wallet_manager, network="devnet")
    yield adapter
    await adapter.close()

@pytest.fixture
async def jup_adapter(wallet_manager):
    """Initialize Jupiter adapter for testing."""
    adapter = JupiterAdapter(wallet_manager)
    yield adapter
    await adapter.close()

@pytest.fixture
def mock_market_config():
    """Provide mock market configuration for testing."""
    return {
        "SOL-PERP": {
            "base_decimals": 9,
            "quote_decimals": 6,
            "min_order_size": 0.1,
            "tick_size": 0.01
        },
        "BTC-PERP": {
            "base_decimals": 8,
            "quote_decimals": 6,
            "min_order_size": 0.001,
            "tick_size": 1.0
        }
    }

@pytest.fixture
def mock_prices():
    """Provide mock price data for testing."""
    return {
        "SOL-PERP": 100.0,
        "BTC-PERP": 50000.0,
        "SOL/USDC": 100.0,
        "BTC/USDC": 50000.0
    } 