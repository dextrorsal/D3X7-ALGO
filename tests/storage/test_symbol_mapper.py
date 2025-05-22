"""
Tests for the symbol mapper functionality.
Focuses on the specific exchange formats we're using:
- Binance: BTCUSDT, ETHUSDT, SOLUSDT (spot only)
- Coinbase: BTC-USD, ETH-USD, SOL-USD (spot only)
- Drift: BTC, ETH, SOL (spot) and BTC-PERP, ETH-PERP, SOL-PERP (perpetual)
"""

import pytest
from src.core.symbol_mapper import SymbolMapper


class TestSymbolMapper:
    """Test the SymbolMapper class with our specific exchange formats."""

    @pytest.fixture
    def mapper(self):
        """Create and initialize a symbol mapper with our test symbols."""
        mapper = SymbolMapper()

        # Register Binance spot symbols
        for base in ["BTC", "ETH", "SOL"]:
            mapper.register_symbol(
                exchange="binance",
                symbol=f"{base}USDT",
                base_asset=base,
                quote_asset="USDT",
                is_perpetual=False,
            )

        # Register Coinbase spot symbols
        for base in ["BTC", "ETH", "SOL"]:
            mapper.register_symbol(
                exchange="coinbase",
                symbol=f"{base}-USD",
                base_asset=base,
                quote_asset="USD",
                is_perpetual=False,
            )

        # Register Drift spot symbols
        for base in ["BTC", "ETH", "SOL"]:
            mapper.register_symbol(
                exchange="drift",
                symbol=base,
                base_asset=base,
                quote_asset="USDC",
                is_perpetual=False,
            )

        # Register Drift perpetual symbols
        for base in ["BTC", "ETH", "SOL"]:
            mapper.register_symbol(
                exchange="drift",
                symbol=f"{base}-PERP",
                base_asset=base,
                quote_asset="PERP",
                is_perpetual=True,
            )

        return mapper

    def test_binance_to_standard(self, mapper):
        """Test converting Binance symbols to standard format."""
        # Test spot markets
        assert mapper.from_exchange_symbol("binance", "BTCUSDT") == "BTC-USDT"
        assert mapper.from_exchange_symbol("binance", "ETHUSDT") == "ETH-USDT"
        assert mapper.from_exchange_symbol("binance", "SOLUSDT") == "SOL-USDT"

    def test_standard_to_binance(self, mapper):
        """Test converting standard symbols to Binance format."""
        # Test spot markets
        assert mapper.to_exchange_symbol("binance", "BTC-USDT") == "BTCUSDT"
        assert mapper.to_exchange_symbol("binance", "ETH-USDT") == "ETHUSDT"
        assert mapper.to_exchange_symbol("binance", "SOL-USDT") == "SOLUSDT"

        # Test with different quote currencies (should convert to USDT)
        assert mapper.to_exchange_symbol("binance", "BTC-USD") == "BTCUSDT"
        assert mapper.to_exchange_symbol("binance", "ETH-USDC") == "ETHUSDT"

        # Test with perpetual markets (should raise error)
        with pytest.raises(ValueError):
            mapper.to_exchange_symbol("binance", "BTC-PERP")

    def test_coinbase_to_standard(self, mapper):
        """Test converting Coinbase symbols to standard format."""
        # Test spot markets
        assert mapper.from_exchange_symbol("coinbase", "BTC-USD") == "BTC-USD"
        assert mapper.from_exchange_symbol("coinbase", "ETH-USD") == "ETH-USD"
        assert mapper.from_exchange_symbol("coinbase", "SOL-USD") == "SOL-USD"

    def test_standard_to_coinbase(self, mapper):
        """Test converting standard symbols to Coinbase format."""
        # Test spot markets
        assert mapper.to_exchange_symbol("coinbase", "BTC-USD") == "BTC-USD"
        assert mapper.to_exchange_symbol("coinbase", "ETH-USD") == "ETH-USD"
        assert mapper.to_exchange_symbol("coinbase", "SOL-USD") == "SOL-USD"

        # Test with different quote currencies (should convert to USD)
        assert mapper.to_exchange_symbol("coinbase", "BTC-USDT") == "BTC-USD"
        assert mapper.to_exchange_symbol("coinbase", "ETH-USDC") == "ETH-USD"

        # Test with perpetual markets (should raise error)
        with pytest.raises(ValueError):
            mapper.to_exchange_symbol("coinbase", "BTC-PERP")

    def test_drift_to_standard(self, mapper):
        """Test converting Drift symbols to standard format."""
        # Test spot markets (bare asset names)
        assert mapper.from_exchange_symbol("drift", "BTC") == "BTC-USDC"
        assert mapper.from_exchange_symbol("drift", "ETH") == "ETH-USDC"
        assert mapper.from_exchange_symbol("drift", "SOL") == "SOL-USDC"

        # Test perpetual markets
        assert mapper.from_exchange_symbol("drift", "BTC-PERP") == "BTC-PERP"
        assert mapper.from_exchange_symbol("drift", "ETH-PERP") == "ETH-PERP"
        assert mapper.from_exchange_symbol("drift", "SOL-PERP") == "SOL-PERP"

    def test_standard_to_drift(self, mapper):
        """Test converting standard symbols to Drift format."""
        # Test spot markets
        assert mapper.to_exchange_symbol("drift", "BTC-USDC") == "BTC"
        assert mapper.to_exchange_symbol("drift", "ETH-USDC") == "ETH"
        assert mapper.to_exchange_symbol("drift", "SOL-USDC") == "SOL"

        # Test with USD quote (should work the same)
        assert mapper.to_exchange_symbol("drift", "BTC-USD") == "BTC"
        assert mapper.to_exchange_symbol("drift", "ETH-USD") == "ETH"

        # Test perpetual markets
        assert mapper.to_exchange_symbol("drift", "BTC-PERP") == "BTC-PERP"
        assert mapper.to_exchange_symbol("drift", "ETH-PERP") == "ETH-PERP"
        assert mapper.to_exchange_symbol("drift", "SOL-PERP") == "SOL-PERP"

    def test_cross_exchange_conversion(self, mapper):
        """Test converting symbols between exchanges."""
        # Binance to Coinbase
        binance_symbol = "BTCUSDT"
        standard_symbol = mapper.from_exchange_symbol("binance", binance_symbol)
        coinbase_symbol = mapper.to_exchange_symbol("coinbase", standard_symbol)
        assert coinbase_symbol == "BTC-USD"

        # Coinbase to Drift
        coinbase_symbol = "ETH-USD"
        standard_symbol = mapper.from_exchange_symbol("coinbase", coinbase_symbol)
        drift_symbol = mapper.to_exchange_symbol("drift", standard_symbol)
        assert drift_symbol == "ETH"

        # Drift to Binance
        drift_symbol = "SOL"
        standard_symbol = mapper.from_exchange_symbol("drift", drift_symbol)
        binance_symbol = mapper.to_exchange_symbol("binance", standard_symbol)
        assert binance_symbol == "SOLUSDT"

    def test_get_supported_exchanges(self, mapper):
        """Test getting supported exchanges for a symbol."""
        # All exchanges support BTC spot
        supported = mapper.get_supported_exchanges("BTC-USDT")
        assert "binance" in supported

        supported = mapper.get_supported_exchanges("BTC-USD")
        assert "coinbase" in supported

        supported = mapper.get_supported_exchanges("BTC-USDC")
        assert "drift" in supported

        # Only Drift supports perpetuals
        supported = mapper.get_supported_exchanges("BTC-PERP")
        assert "drift" in supported
        assert "binance" not in supported
        assert "coinbase" not in supported

    def test_get_supported_symbols(self, mapper):
        """Test getting supported symbols for an exchange."""
        # Binance supports BTC, ETH, SOL spot
        binance_symbols = mapper.get_supported_symbols("binance")
        assert "BTC-USDT" in binance_symbols
        assert "ETH-USDT" in binance_symbols
        assert "SOL-USDT" in binance_symbols
        assert "BTC-PERP" not in binance_symbols

        # Coinbase supports BTC, ETH, SOL spot
        coinbase_symbols = mapper.get_supported_symbols("coinbase")
        assert "BTC-USD" in coinbase_symbols
        assert "ETH-USD" in coinbase_symbols
        assert "SOL-USD" in coinbase_symbols
        assert "BTC-PERP" not in coinbase_symbols

        # Drift supports BTC, ETH, SOL spot and perpetual
        drift_symbols = mapper.get_supported_symbols("drift")
        assert "BTC-USDC" in drift_symbols
        assert "ETH-USDC" in drift_symbols
        assert "SOL-USDC" in drift_symbols
        assert "BTC-PERP" in drift_symbols
        assert "ETH-PERP" in drift_symbols
        assert "SOL-PERP" in drift_symbols
