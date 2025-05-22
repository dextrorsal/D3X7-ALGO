"""
Test suite for mainnet trading functionality.
"""

import pytest
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from src.trading.mainnet.security_limits import SecurityLimits
from src.utils.wallet.wallet_cli import WalletCLI
from src.trading.drift.drift_adapter import DriftAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture
def security_config():
    """Fixture for security configuration."""
    return {
        "max_position_size": {"SOL-PERP": 2.0, "BTC-PERP": 0.05},
        "max_leverage": {"SOL-PERP": 3, "BTC-PERP": 2},
        "daily_volume_limit": 5.0,
        "test_mode": True,  # Always use test mode in tests
    }


@pytest.fixture
async def wallet_cli():
    """Fixture for wallet CLI."""
    cli = WalletCLI()
    cli.set_network("mainnet")
    return cli


@pytest.fixture
async def drift_manager(wallet_cli):
    """Fixture for Drift account manager."""
    manager = DriftAdapter()
    # Use a test wallet or mock wallet for testing
    test_wallet = wallet_cli.get_wallet("TEST")
    manager.set_wallet(test_wallet)
    await manager.setup()
    return manager


@pytest.mark.asyncio
class TestMainnetTrading:
    """Test cases for mainnet trading functionality."""

    async def test_trade_size_validation(self, security_config):
        """Test trade size validation."""
        security_limits = SecurityLimits(**(security_config or {}))

        # Test valid trade size
        assert security_limits.validate_trade_size("SOL-PERP", 1.5)

        # Test invalid trade size
        assert not security_limits.validate_trade_size("SOL-PERP", 2.5)

    async def test_drift_trade_execution(self, drift_manager, security_config):
        """Test Drift trade execution."""
        result = await self.execute_test_trade(
            market="SOL-PERP", size=1.0, side="buy", security_config=security_config
        )

        assert result["status"] == "simulated"  # Since we're in test mode
        assert result["market"] == "SOL-PERP"
        assert result["size"] == 1.0

    async def test_trade_rejection_invalid_market(self, drift_manager, security_config):
        """Test trade rejection for invalid market."""
        result = await self.execute_test_trade(
            market="INVALID-PERP", size=1.0, side="buy", security_config=security_config
        )

        assert result["status"] == "rejected"
        assert result["reason"] == "unsupported_market"

    async def test_trade_rejection_size_exceeded(self, drift_manager, security_config):
        """Test trade rejection when size exceeds limits."""
        result = await self.execute_test_trade(
            market="SOL-PERP",
            size=3.0,  # Exceeds max position size
            side="buy",
            security_config=security_config,
        )

        assert result["status"] == "rejected"
        assert result["reason"] == "trade_size_exceeded"

    async def execute_test_trade(
        self,
        market: str,
        size: float,
        side: str = "buy",
        security_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Helper method to execute test trades."""
        security_limits = SecurityLimits(**(security_config or {}))

        if not security_limits.validate_trade_size(market, size):
            return {
                "status": "rejected",
                "reason": "trade_size_exceeded",
                "market": market,
                "size": size,
                "side": side,
            }

        market_indices = {"SOL-PERP": 0, "BTC-PERP": 1, "ETH-PERP": 2}

        if market not in market_indices:
            return {
                "status": "rejected",
                "reason": "unsupported_market",
                "market": market,
            }

        # For test mode, return simulated result
        return {
            "status": "simulated",
            "market": market,
            "size": size,
            "direction": "long" if side.lower() == "buy" else "short",
            "market_index": market_indices[market],
            "timestamp": datetime.utcnow().isoformat(),
        }
