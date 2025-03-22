"""
Comprehensive integration tests for Drift protocol functionality in devnet environment.
Tests account management, markets, deposits, and trading operations.
"""
import pytest
import asyncio
import json
from decimal import Decimal
from pathlib import Path
from solders.keypair import Keypair

from src.utils.wallet import WalletManager
from src.trading.drift.drift_adapter import DriftAdapter
from src.trading.mainnet.security_limits import SecurityLimits

@pytest.mark.asyncio
class TestDriftIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self, test_config):
        """Setup test environment with Drift connection."""
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
        self.security = SecurityLimits(test_config)
        
        yield
        
        # Cleanup
        if self.wallet_path.exists():
            self.wallet_path.unlink()
            
        await self.drift.close()
        await self.wallet.close()

    # Account Management Tests
    async def test_account_creation(self):
        """Test Drift account creation and initialization."""
        account = await self.drift.create_account()
        assert account is not None
        assert await self.drift.get_account_exists()

    async def test_account_subscription(self):
        """Test account subscription and updates."""
        await self.drift.subscribe_to_account()
        assert self.drift.is_subscribed()
        
        # Test account updates
        await self.drift.update_account_info()
        assert self.drift.account_info is not None

    # Deposit and Balance Tests
    async def test_deposit_flow(self):
        """Test deposit functionality."""
        # Ensure we have some SOL from faucet
        main_wallet = self.wallet.get_wallet("MAIN")
        await main_wallet.request_airdrop(1.0)
        await asyncio.sleep(1)

        # Test USDC deposit
        initial_balance = await self.drift.get_usdc_balance()
        deposit_amount = Decimal("10.0")
        
        await self.drift.deposit_usdc(deposit_amount)
        await asyncio.sleep(1)
        
        new_balance = await self.drift.get_usdc_balance()
        assert new_balance > initial_balance

    async def test_collateral_check(self):
        """Test collateral verification."""
        collateral = await self.drift.get_total_collateral()
        assert collateral is not None
        assert collateral >= 0

    # Market Operations Tests
    async def test_market_data(self):
        """Test market data retrieval and validation."""
        markets = await self.drift.get_markets()
        assert len(markets) > 0
        
        # Test specific market
        sol_market = await self.drift.get_market_by_symbol("SOL-PERP")
        assert sol_market is not None
        assert sol_market["symbol"] == "SOL-PERP"

    async def test_orderbook_data(self):
        """Test orderbook functionality."""
        orderbook = await self.drift.get_orderbook("SOL-PERP")
        assert orderbook is not None
        assert "bids" in orderbook
        assert "asks" in orderbook

    # Trading Tests
    async def test_perp_order_placement(self):
        """Test perpetual order placement."""
        # Ensure we have enough collateral
        await self.drift.deposit_usdc(Decimal("100.0"))
        await asyncio.sleep(1)

        # Place a small test order
        order = await self.drift.place_perp_order(
            market="SOL-PERP",
            side="buy",
            size=0.1,
            price=None,  # Market order
            reduce_only=False
        )
        assert order is not None
        assert order["status"] in ["open", "filled"]

    async def test_position_management(self):
        """Test position management functionality."""
        # Get current position
        position = await self.drift.get_position("SOL-PERP")
        initial_size = position["size"] if position else 0

        # Open small test position
        await self.drift.place_perp_order(
            market="SOL-PERP",
            side="buy",
            size=0.1,
            price=None
        )
        await asyncio.sleep(1)

        # Verify position
        new_position = await self.drift.get_position("SOL-PERP")
        assert new_position is not None
        assert new_position["size"] > initial_size

        # Close position
        await self.drift.place_perp_order(
            market="SOL-PERP",
            side="sell",
            size=0.1,
            price=None,
            reduce_only=True
        )

    # Risk Management Tests
    async def test_leverage_limits(self):
        """Test leverage limit enforcement."""
        max_leverage = self.security.get_max_leverage("SOL-PERP")
        
        # Attempt to place order exceeding leverage
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market="SOL-PERP",
                side="buy",
                size=10.0,  # Large size to exceed leverage
                price=None
            )

    async def test_position_limits(self):
        """Test position size limits."""
        max_size = self.security.get_max_position_size("SOL-PERP")
        
        # Attempt to exceed position limit
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market="SOL-PERP",
                side="buy",
                size=max_size * 2,
                price=None
            )

    # Error Handling Tests
    async def test_invalid_market(self):
        """Test handling of invalid market."""
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market="INVALID-PERP",
                side="buy",
                size=0.1,
                price=None
            )

    async def test_insufficient_margin(self):
        """Test handling of insufficient margin."""
        # Attempt trade without enough collateral
        with pytest.raises(Exception):
            await self.drift.place_perp_order(
                market="SOL-PERP",
                side="buy",
                size=100.0,  # Large size requiring lots of margin
                price=None
            ) 