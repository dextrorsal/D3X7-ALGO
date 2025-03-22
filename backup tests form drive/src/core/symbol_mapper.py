"""
Symbol standardization for cryptocurrency exchanges.
Maps between a standard internal format and exchange-specific formats.
"""

import logging
import re
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class SymbolMapper:
    """
    Manages symbol mapping between a standardized internal format and exchange-specific formats.
    
    Standard Format: BASE-QUOTE (e.g., BTC-USDT, SOL-USDC)
    Perpetual Format: BASE-PERP (e.g., BTC-PERP, SOL-PERP)
    
    Exchange-Specific Formats:
    - Drift (DEX):
        * Spot: SOL, BTC, ETH (representing SOL-USDC, BTC-USDC, ETH-USDC)
        * Perp: SOL-PERP, BTC-PERP, ETH-PERP
    - Binance:
        * Spot: BTCUSDT, ETHUSDT, SOLUSDT
    - Coinbase:
        * Spot: BTC-USD, ETH-USD, SOL-USD
    """
    
    # Core supported assets - focusing only on major cryptocurrencies
    SUPPORTED_ASSETS = {
        "drift": ["SOL", "BTC", "ETH"],  # Both spot and perpetual
        "binance": ["SOL", "BTC", "ETH", "BNB"],  # Spot only
        "coinbase": ["SOL", "BTC", "ETH"]  # Spot only
    }
    
    # Quote currencies for each exchange
    QUOTE_CURRENCIES = {
        "drift": ["USDC"],  # Drift uses USDC for spot
        "binance": ["USDT"],  # Binance primarily uses USDT
        "coinbase": ["USD"]  # Coinbase uses USD
    }
    
    # Perpetual market support
    PERPETUAL_SUPPORT = {
        "drift": True,
        "binance": False,  # We're not using Binance perpetuals
        "coinbase": False
    }
    
    def __init__(self):
        """Initialize the symbol mapper with empty mapping tables."""
        # Maps exchange:standard_symbol → exchange_symbol
        self.to_exchange_map: Dict[str, Dict[str, str]] = {}
        
        # Maps exchange:exchange_symbol → standard_symbol
        self.from_exchange_map: Dict[str, Dict[str, str]] = {}
        
        # Sets of supported symbols for each exchange
        self.supported_symbols: Dict[str, Set[str]] = {}
    
    def register_symbol(self, exchange: str, symbol: str, base_asset: str, 
                       quote_asset: str, is_perpetual: bool = False) -> None:
        """
        Register a symbol with its base and quote assets.
        
        Args:
            exchange: Exchange name
            symbol: Symbol in exchange format
            base_asset: Base asset (e.g., BTC)
            quote_asset: Quote asset (e.g., USDT)
            is_perpetual: Whether this is a perpetual market
        """
        exchange_id = exchange.lower()
        
        if exchange_id not in self.to_exchange_map:
            self.to_exchange_map[exchange_id] = {}
            self.from_exchange_map[exchange_id] = {}
            self.supported_symbols[exchange_id] = set()
        
        # Create standard symbol
        if is_perpetual:
            standard_symbol = f"{base_asset}-PERP"
        else:
            standard_symbol = f"{base_asset}-{quote_asset}"
        
        # Register the mapping in both directions
        self.to_exchange_map[exchange_id][standard_symbol] = symbol
        self.from_exchange_map[exchange_id][symbol] = standard_symbol
        self.supported_symbols[exchange_id].add(standard_symbol)
        
        logger.debug(f"Registered symbol {symbol} → {standard_symbol} for {exchange}")

    def register_exchange(self, exchange: str, markets: List[str]) -> None:
        """
        Register all markets for an exchange.
        
        Args:
            exchange: Exchange name
            markets: List of market symbols in exchange format
        """
        exchange_id = exchange.lower()
        
        for market in markets:
            try:
                if exchange_id == "binance":
                    # For Binance, extract base and quote from combined symbol
                    for quote in self.QUOTE_CURRENCIES["binance"]:
                        if market.endswith(quote):
                            base = market[:-len(quote)]
                            if base in self.SUPPORTED_ASSETS["binance"]:
                                self.register_symbol(exchange, market, base, quote)
                                break
                
                elif exchange_id == "coinbase":
                    # For Coinbase, split on hyphen
                    if "-" in market:
                        base, quote = market.split("-")
                        if base in self.SUPPORTED_ASSETS["coinbase"] and quote in self.QUOTE_CURRENCIES["coinbase"]:
                            self.register_symbol(exchange, market, base, quote)
                
                elif exchange_id == "drift":
                    # For Drift, handle both spot and perpetual
                    if market.endswith("-PERP"):
                        base = market[:-5]
                        if base in self.SUPPORTED_ASSETS["drift"]:
                            self.register_symbol(exchange, market, base, "PERP", True)
                    elif market in self.SUPPORTED_ASSETS["drift"]:
                        self.register_symbol(exchange, market, market, "USDC")
            
            except Exception as e:
                logger.warning(f"Failed to register market {market} for {exchange}: {str(e)}")
                continue
    
    def to_exchange_symbol(self, exchange_name: str, standard_symbol: str) -> str:
        """
        Convert a standard symbol to exchange-specific format.
        
        Args:
            exchange_name: Name of the exchange
            standard_symbol: Symbol in standard format (e.g., BTC-USDT) or 
                            perpetual format (e.g., BTC-PERP)
            
        Returns:
            Symbol in exchange-specific format
            
        Raises:
            ValueError: If the symbol is not supported by the exchange
        """
        exchange_id = exchange_name.lower()
        
        # Check if we have a direct mapping
        if exchange_id in self.to_exchange_map and standard_symbol in self.to_exchange_map[exchange_id]:
            return self.to_exchange_map[exchange_id][standard_symbol]
        
        # Handle perpetual markets
        is_perp = standard_symbol.endswith("-PERP")
        if is_perp and not self.PERPETUAL_SUPPORT.get(exchange_id, False):
            raise ValueError(f"Exchange {exchange_name} does not support perpetual markets")
        
        # Try to generate the exchange symbol format
        try:
            if exchange_id == "binance":
                return self._standard_to_binance(standard_symbol)
            elif exchange_id == "coinbase":
                return self._standard_to_coinbase(standard_symbol)
            elif exchange_id == "drift":
                return self._standard_to_drift(standard_symbol)
            else:
                return standard_symbol.replace("-", "")
        except Exception as e:
            raise ValueError(f"Cannot convert {standard_symbol} to {exchange_name} format: {str(e)}")
    
    def from_exchange_symbol(self, exchange_name: str, exchange_symbol: str) -> str:
        """
        Convert an exchange-specific symbol to standard format.
        
        Args:
            exchange_name: Name of the exchange
            exchange_symbol: Symbol in exchange-specific format
            
        Returns:
            Symbol in standard format (e.g., BTC-USDT) or perpetual format (e.g., BTC-PERP)
            
        Raises:
            ValueError: If the symbol cannot be converted
        """
        exchange_id = exchange_name.lower()
        
        # Check if we have a direct mapping
        if exchange_id in self.from_exchange_map and exchange_symbol in self.from_exchange_map[exchange_id]:
            return self.from_exchange_map[exchange_id][exchange_symbol]
        
        try:
            if exchange_id == "binance":
                return self._binance_to_standard(exchange_symbol)
            elif exchange_id == "coinbase":
                return self._coinbase_to_standard(exchange_symbol)
            elif exchange_id == "drift":
                return self._drift_to_standard(exchange_symbol)
            else:
                return self._generic_to_standard(exchange_symbol)
        except Exception as e:
            raise ValueError(f"Cannot convert {exchange_symbol} from {exchange_name} format: {str(e)}")
    
    def get_supported_exchanges(self, standard_symbol: str) -> List[str]:
        """Get list of exchanges that support the given symbol."""
        supported = []
        for exchange_id, symbols in self.supported_symbols.items():
            if standard_symbol in symbols:
                supported.append(exchange_id)
        return supported
    
    def get_supported_symbols(self, exchange_name: str) -> List[str]:
        """Get list of symbols supported by the exchange."""
        exchange_id = exchange_name.lower()
        if exchange_id in self.supported_symbols:
            return list(self.supported_symbols[exchange_id])
        return []
    
    # -------------------------------------------------------------------------
    # Private methods for exchange-specific conversions
    # -------------------------------------------------------------------------
    
    def _binance_to_standard(self, symbol: str) -> str:
        """Convert Binance symbol to standard format."""
        # Binance spot markets (BTCUSDT format)
        for quote in self.QUOTE_CURRENCIES["binance"]:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"
        
        raise ValueError(f"Cannot determine base/quote for Binance symbol: {symbol}")
    
    def _coinbase_to_standard(self, symbol: str) -> str:
        """Convert Coinbase symbol to standard format."""
        if "-" not in symbol:
            raise ValueError(f"Invalid Coinbase symbol format: {symbol}")
        
        base, quote = symbol.split("-")
        
        if base not in self.SUPPORTED_ASSETS["coinbase"]:
            raise ValueError(f"Unsupported Coinbase asset: {base}")
        if quote not in self.QUOTE_CURRENCIES["coinbase"]:
            raise ValueError(f"Unsupported Coinbase quote currency: {quote}")
        
        return f"{base}-{quote}"
    
    def _drift_to_standard(self, symbol: str) -> str:
        """Convert Drift symbol to standard format."""
        # Handle perpetual contracts
        if symbol.endswith("-PERP"):
            base = symbol[:-5]  # Remove "-PERP"
            if base not in self.SUPPORTED_ASSETS["drift"]:
                raise ValueError(f"Unsupported Drift perpetual asset: {base}")
            return f"{base}-PERP"
        
        # Handle spot markets (just the base asset)
        if symbol in self.SUPPORTED_ASSETS["drift"]:
            return f"{symbol}-USDC"
        
        raise ValueError(f"Unsupported Drift symbol: {symbol}")
    
    def _standard_to_binance(self, standard_symbol: str) -> str:
        """Convert standard symbol to Binance format."""
        # Handle spot markets
        if "-" in standard_symbol:
            base, quote = standard_symbol.split("-")
            # Convert USD to USDT for Binance
            if quote == "USD":
                quote = "USDT"
            elif quote == "USDC":
                quote = "USDT"
        else:
            base = standard_symbol
            quote = "USDT"  # Default to USDT if no quote specified
        
        return f"{base}{quote}"
    
    def _standard_to_coinbase(self, standard_symbol: str) -> str:
        """Convert standard symbol to Coinbase format."""
        if standard_symbol.endswith("-PERP"):
            raise ValueError(f"Perpetual contracts not supported on Coinbase: {standard_symbol}")
        
        if "-" in standard_symbol:
            base, quote = standard_symbol.split("-")
        else:
            base = standard_symbol
            quote = "USD"  # Default quote for Coinbase
        
        if base not in self.SUPPORTED_ASSETS["coinbase"]:
            raise ValueError(f"Unsupported Coinbase asset: {base}")
        
        # Convert quote currency if needed
        if quote in ["USDT", "USDC"]:
            quote = "USD"
        
        if quote not in self.QUOTE_CURRENCIES["coinbase"]:
            raise ValueError(f"Unsupported Coinbase quote currency: {quote}")
        
        return f"{base}-{quote}"
    
    def _standard_to_drift(self, standard_symbol: str) -> str:
        """Convert standard symbol to Drift format."""
        # Handle perpetual contracts
        if standard_symbol.endswith("-PERP"):
            base = standard_symbol[:-5]  # Remove "-PERP"
            if base not in self.SUPPORTED_ASSETS["drift"]:
                raise ValueError(f"Unsupported Drift perpetual asset: {base}")
            return f"{base}-PERP"
        
        # Handle spot markets
        if "-" in standard_symbol:
            base, quote = standard_symbol.split("-")
            if quote not in ["USDC", "USD"]:
                raise ValueError(f"Unsupported Drift quote currency: {quote}")
        else:
            base = standard_symbol
        
        if base not in self.SUPPORTED_ASSETS["drift"]:
            raise ValueError(f"Unsupported Drift spot asset: {base}")
        
        # For Drift spot, we just return the base asset
        return base
    
    def _generic_to_standard(self, symbol: str) -> str:
        """Convert a generic symbol to standard format."""
        if "-" in symbol:
            parts = symbol.split("-")
            if len(parts) == 2:
                return symbol.upper()
        
        # Handle perpetual contracts
        if symbol.endswith("-PERP"):
            base = symbol[:-5]  # Remove "-PERP"
            return f"{base}-PERP"
        
        # Try to identify quote currency
        for quote in ["USDT", "USDC", "USD"]:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"
        
        raise ValueError(f"Cannot determine base/quote for symbol: {symbol}")


# Example usage:
if __name__ == "__main__":
    mapper = SymbolMapper()
    
    # Register exchanges with their supported symbols
    # Binance: Spot only with USDT pairs
    mapper.register_exchange("binance", [
        "BTCUSDT", "ETHUSDT", "SOLUSDT"
    ])
    
    # Coinbase: Spot only with USD pairs
    mapper.register_exchange("coinbase", [
        "BTC-USD", "ETH-USD", "SOL-USD"
    ])
    
    # Drift: Both spot (bare assets) and perpetuals
    mapper.register_exchange("drift", [
        # Spot markets (bare assets)
        "SOL", "BTC", "ETH",
        # Perpetual markets
        "SOL-PERP", "BTC-PERP", "ETH-PERP"
    ])
    
    # Jupiter: Spot only with USDC pairs
    mapper.register_exchange("jupiter", [
        "SOL-USDC", "BTC-USDC", "ETH-USDC"
    ])
    
    print("\nTesting standard spot symbols:")
    spot_symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    for symbol in spot_symbols:
        print(f"\nTesting spot symbol: {symbol}")
        for exchange in ["binance", "coinbase", "drift", "jupiter"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, symbol)
                print(f"  {symbol} → {exchange}: {ex_sym}")
                # Convert back to standard to verify roundtrip
                std_sym = mapper.from_exchange_symbol(exchange, ex_sym)
                print(f"  {ex_sym} → standard: {std_sym}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
    
    print("\nTesting perpetual symbols:")
    perp_symbols = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
    for symbol in perp_symbols:
        print(f"\nTesting perp symbol: {symbol}")
        for exchange in ["binance", "coinbase", "drift", "jupiter"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, symbol)
                print(f"  {symbol} → {exchange}: {ex_sym}")
                # Convert back to standard to verify roundtrip
                std_sym = mapper.from_exchange_symbol(exchange, ex_sym)
                print(f"  {ex_sym} → standard: {std_sym}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
    
    print("\nTesting bare asset symbols:")
    assets = ["BTC", "ETH", "SOL"]
    for asset in assets:
        print(f"\nTesting asset: {asset}")
        for exchange in ["binance", "coinbase", "drift", "jupiter"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, asset)
                print(f"  {asset} → {exchange}: {ex_sym}")
                # Convert back to standard to verify roundtrip
                std_sym = mapper.from_exchange_symbol(exchange, ex_sym)
                print(f"  {ex_sym} → standard: {std_sym}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
    
    print("\nTesting exchange-specific formats:")
    exchange_symbols = {
        "binance": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "coinbase": ["BTC-USD", "ETH-USD", "SOL-USD"],
        "drift": ["BTC", "ETH", "SOL", "BTC-PERP", "ETH-PERP", "SOL-PERP"],
        "jupiter": ["BTC-USDC", "ETH-USDC", "SOL-USDC"]
    }
    
    for exchange, symbols in exchange_symbols.items():
        print(f"\nTesting {exchange} symbols:")
        for symbol in symbols:
            try:
                std_sym = mapper.from_exchange_symbol(exchange, symbol)
                print(f"  {symbol} → standard: {std_sym}")
                # Convert back to exchange format to verify roundtrip
                ex_sym = mapper.to_exchange_symbol(exchange, std_sym)
                print(f"  {std_sym} → {exchange}: {ex_sym}")
            except ValueError as e:
                print(f"  Error for {symbol}: {e}")
