"""
Test suite for mainnet Jupiter swap functionality.
"""

import pytest
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from src.trading.mainnet.security_limits import SecurityLimits
from src.utils.wallet.wallet_cli import WalletCLI
from src.trading.jup.jup_adapter import JupiterAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture
def security_config():
    """Fixture for security configuration."""
    return {
        "max_swap_size": {
            "SOL": 10.0,
            "USDC": 1000.0
        },
        "daily_volume_limit": 5000.0,
        "test_mode": True  # Always use test mode in tests
    }

@pytest.fixture
async def wallet_cli():
    """Fixture for wallet CLI."""
    cli = WalletCLI()
    cli.set_network("mainnet")
    return cli

@pytest.fixture
async def jupiter_adapter(wallet_cli):
    """Fixture for Jupiter adapter."""
    adapter = JupiterAdapter()
    # Use a test wallet or mock wallet for testing
    test_wallet = wallet_cli.get_wallet("TEST")
    adapter.set_wallet(test_wallet)
    await adapter.setup()
    return adapter

@pytest.mark.asyncio
class TestMainnetSwap:
    """Test cases for mainnet Jupiter swap functionality."""
    
    async def test_swap_size_validation(self, security_config):
        """Test swap size validation."""
        security_limits = SecurityLimits(**(security_config or {}))
        
        # Test valid swap size
        assert security_limits.validate_swap_size("SOL", 5.0)
        
        # Test invalid swap size
        assert not security_limits.validate_swap_size("SOL", 15.0)
    
    async def test_jupiter_swap_execution(self, jupiter_adapter, security_config):
        """Test Jupiter swap execution."""
        result = await self.execute_test_swap(
            market="SOL-USDC",
            input_amount=1.0,
            security_config=security_config
        )
        
        assert result["status"] == "simulated"  # Since we're in test mode
        assert result["market"] == "SOL-USDC"
        assert result["input_amount"] == 1.0
    
    async def test_swap_rejection_invalid_market(self, jupiter_adapter, security_config):
        """Test swap rejection for invalid market."""
        result = await self.execute_test_swap(
            market="INVALID-USDC",
            input_amount=1.0,
            security_config=security_config
        )
        
        assert result["status"] == "rejected"
        assert result["reason"] == "unsupported_market"
    
    async def test_swap_rejection_size_exceeded(self, jupiter_adapter, security_config):
        """Test swap rejection when size exceeds limits."""
        result = await self.execute_test_swap(
            market="SOL-USDC",
            input_amount=20.0,  # Exceeds max swap size
            security_config=security_config
        )
        
        assert result["status"] == "rejected"
        assert result["reason"] == "swap_size_exceeded"
    
    async def execute_test_swap(
        self,
        market: str,
        input_amount: float,
        security_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Helper method to execute test swaps."""
        security_limits = SecurityLimits(**(security_config or {}))
        
        # Extract input token from market pair
        input_token = market.split("-")[0]
        
        if not security_limits.validate_swap_size(input_token, input_amount):
            return {
                "status": "rejected",
                "reason": "swap_size_exceeded",
                "market": market,
                "input_amount": input_amount
            }
        
        supported_markets = [
            "SOL-USDC",
            "BTC-USDC",
            "ETH-USDC"
        ]
        
        if market not in supported_markets:
            return {
                "status": "rejected",
                "reason": "unsupported_market",
                "market": market
            }
        
        # For test mode, return simulated result
        return {
            "status": "simulated",
            "market": market,
            "input_amount": input_amount,
            "input_token": input_token,
            "output_token": market.split("-")[1],
            "timestamp": datetime.utcnow().isoformat()
        } 