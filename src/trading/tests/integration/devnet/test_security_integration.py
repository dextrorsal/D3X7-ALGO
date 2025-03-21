#!/usr/bin/env python3
"""
Test script to verify security features integration with Drift
"""

import asyncio
import logging
import time
import pytest
from decimal import Decimal
from pathlib import Path
import json

from driftpy.types import OrderParams, PositionDirection
from src.trading.devnet.devnet_adapter import DevnetAdapter
from src.utils.wallet import WalletManager
from src.trading.mainnet.security_limits import SecurityLimits
from src.trading.drift.drift_adapter import DriftAdapter
from src.trading.jup.jup_adapter import JupiterAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestSecurityIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self, test_config):
        """Setup test environment with security controls."""
        # Create test wallet configuration
        self.wallet_path = Path.home() / ".config/solana/test-devnet.json"
        self.test_keypair = Keypair()
        
        # Create test wallet configuration
        self.wallet_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.wallet_path, 'w') as f:
            json.dump([x for x in self.test_keypair.secret()], f)
        
        # Initialize wallet manager and add test wallet
        self.wallet = WalletManager()
        self.wallet.add_wallet("MAIN", str(self.wallet_path))
        
        self.drift = DriftAdapter(self.wallet, network="devnet")
        self.jupiter = JupiterAdapter(self.wallet)
        self.security = SecurityLimits(test_config)
        
        yield
        
        # Cleanup
        if self.wallet_path.exists():
            self.wallet_path.unlink()
            
        await self.drift.close()
        await self.jupiter.close()
        await self.wallet.close()

    # Basic Security Tests
    async def test_position_size_limits(self):
        """Test position size limit enforcement."""
        market = "SOL-PERP"
        max_size = self.security.get_max_position_size(market)
        
        # Test valid size
        assert self.security.validate_position_size(market, max_size * 0.5)
        
        # Test invalid size
        with pytest.raises(Exception):
            self.security.validate_position_size(market, max_size * 2)

    async def test_leverage_limits(self):
        """Test leverage limit enforcement."""
        market = "SOL-PERP"
        max_leverage = self.security.get_max_leverage(market)
        
        # Test valid leverage
        assert self.security.validate_leverage(market, max_leverage * 0.5)
        
        # Test invalid leverage
        with pytest.raises(Exception):
            self.security.validate_leverage(market, max_leverage * 2)

    async def test_daily_volume_tracking(self):
        """Test daily volume tracking and limits."""
        # Reset daily volume
        self.security.reset_daily_volume()
        
        # Add some volume
        self.security.add_trade_volume(0.5)
        assert self.security.get_daily_volume() == 0.5
        
        # Test volume limit
        with pytest.raises(Exception):
            self.security.add_trade_volume(1000.0)  # Exceed daily limit

    # Integration Tests with Trading
    async def test_drift_trade_security(self):
        """Test security integration with Drift trading."""
        market = "SOL-PERP"
        
        # Setup test position
        await self.drift.deposit_usdc(Decimal("100.0"))
        await asyncio.sleep(1)
        
        # Test valid trade
        size = self.security.get_max_position_size(market) * 0.1
        order = await self.drift.place_perp_order(
            market=market,
            side="buy",
            size=size,
            price=None
        )
        assert order is not None
        
        # Test invalid trade
        size = self.security.get_max_position_size(market) * 2
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market=market,
                side="buy",
                size=size,
                price=None
            )

    async def test_jupiter_swap_security(self):
        """Test security integration with Jupiter swaps."""
        # Test valid swap
        amount = Decimal("0.1")
        assert self.security.validate_swap_size("SOL/USDC", amount)
        
        # Test invalid swap
        large_amount = Decimal("1000.0")
        with pytest.raises(Exception):
            self.security.validate_swap_size("SOL/USDC", large_amount)

    # Emergency Controls Tests
    async def test_emergency_shutdown(self):
        """Test emergency shutdown functionality."""
        # Trigger emergency shutdown
        self.security.trigger_emergency_shutdown()
        assert self.security.is_emergency_mode()
        
        # Verify trading is blocked
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market="SOL-PERP",
                side="buy",
                size=0.1,
                price=None
            )
        
        # Reset emergency mode
        self.security.reset_emergency_mode()
        assert not self.security.is_emergency_mode()

    async def test_loss_threshold(self):
        """Test loss threshold monitoring."""
        # Setup initial state
        initial_equity = await self.drift.get_total_collateral()
        
        # Simulate loss
        loss_pct = self.security.config["emergency_shutdown_triggers"]["loss_threshold_pct"]
        simulated_loss = initial_equity * (1 - loss_pct/100)
        
        # Test loss threshold trigger
        with pytest.raises(Exception):
            self.security.check_loss_threshold(simulated_loss, initial_equity)

    # Risk Management Tests
    async def test_risk_metrics(self):
        """Test risk metrics calculation and monitoring."""
        # Calculate position risk
        position_risk = self.security.calculate_position_risk("SOL-PERP", 0.1, 100.0)
        assert position_risk is not None
        assert position_risk >= 0
        
        # Test risk thresholds
        assert self.security.is_risk_acceptable("SOL-PERP", position_risk)
        
        # Test high risk scenario
        high_risk = position_risk * 10
        assert not self.security.is_risk_acceptable("SOL-PERP", high_risk)

    async def test_market_stress(self):
        """Test market stress detection."""
        # Normal market conditions
        normal_volatility = 0.02  # 2% volatility
        assert not self.security.is_market_stressed("SOL-PERP", normal_volatility)
        
        # Stressed market conditions
        high_volatility = 0.15  # 15% volatility
        assert self.security.is_market_stressed("SOL-PERP", high_volatility)

    # Configuration Tests
    def test_config_validation(self):
        """Test security configuration validation."""
        # Test valid config
        assert self.security.validate_config(self.security.config)
        
        # Test invalid config
        invalid_config = {
            "max_position_size": {},  # Empty market config
            "max_leverage": {},
            "daily_volume_limit": -1  # Invalid negative value
        }
        with pytest.raises(Exception):
            self.security.validate_config(invalid_config)

async def test_security_features():
    """Test all integrated security features"""
    helper = DevnetAdapter()
    
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