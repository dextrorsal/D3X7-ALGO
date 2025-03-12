"""
Symbol standardization for cryptocurrency exchanges.
Maps between a standard internal symbol format and exchange-specific formats.
"""

import logging
import re
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class SymbolMapper:
    """
    Manages symbol mapping between a standardized internal format and exchange-specific formats.
    
    The internal standard format is: BASE-QUOTE
    Examples: BTC-USD, ETH-USDT, SOL-USDC, BTC-PERP
    
    For perpetual contracts, we use BASE-PERP as the standard format.
    """
    
    # Standard asset naming (handles aliases like XBT -> BTC)
    ASSET_ALIASES = {
        "XBT": "BTC",
        "DOGE": "DOGE",
        "SHIB": "SHIB",
        "PEPE": "PEPE"
    }
    
    # Common stablecoins to handle quote currencies
    STABLECOINS = ['USD', 'USDT', 'USDC', 'BUSD', 'DAI']
    
    # Common perpetual contract suffixes in different exchanges
    PERPETUAL_IDENTIFIERS = ['PERP', 'PERPETUAL', '-P', '-PERP', 'SWAP']
    
    def __init__(self):
        """Initialize the symbol mapper with empty mapping tables."""
        # Maps exchange:standard_symbol → exchange_symbol
        self.to_exchange_map: Dict[str, Dict[str, str]] = {}
        
        # Maps exchange:exchange_symbol → standard_symbol
        self.from_exchange_map: Dict[str, Dict[str, str]] = {}
        
        # Sets of supported symbols for each exchange
        self.supported_symbols: Dict[str, Set[str]] = {}
    
    def register_exchange(self, exchange_name: str, symbols: List[str]) -> None:
        """
        Register an exchange and its supported symbols.
        
        Args:
            exchange_name: Name of the exchange
            symbols: List of symbols in exchange-specific format
        """
        exchange_id = exchange_name.lower()
        
        if exchange_id not in self.to_exchange_map:
            self.to_exchange_map[exchange_id] = {}
            self.from_exchange_map[exchange_id] = {}
            self.supported_symbols[exchange_id] = set()
        
        for symbol in symbols:
            try:
                standard_symbol = self._exchange_to_standard(exchange_id, symbol)
                
                # Register the mapping in both directions
                self.to_exchange_map[exchange_id][standard_symbol] = symbol
                self.from_exchange_map[exchange_id][symbol] = standard_symbol
                self.supported_symbols[exchange_id].add(standard_symbol)
                
                logger.debug(f"Registered symbol {symbol} → {standard_symbol} for {exchange_name}")
            except ValueError as e:
                logger.warning(f"Skipping invalid symbol {symbol} for {exchange_name}: {str(e)}")
    
    def to_exchange_symbol(self, exchange_name: str, standard_symbol: str) -> str:
        """
        Convert a standard symbol to exchange-specific format.
        
        Args:
            exchange_name: Name of the exchange
            standard_symbol: Symbol in standard format (e.g., BTC-USD) or 
                            exchange-specific format (e.g., BTCUSDT)
            
        Returns:
            Symbol in exchange-specific format
            
        Raises:
            ValueError: If the symbol is not supported by the exchange
        """
        exchange_id = exchange_name.lower()

        # For Binance: if already in a recognized format, return it.
        if exchange_id == 'binance' and re.match(r'^[A-Z]+(USDT|USDC|BTC|ETH)(_PERP)?$', standard_symbol):
            return standard_symbol
        # For Coinbase: if a dash exists, assume it's already in standard format.
        elif exchange_id == 'coinbase' and '-' in standard_symbol:
            return standard_symbol.upper()
        # For Drift: if symbol contains a dash, assume the user provided the full symbol.
        elif exchange_id == 'drift' and '-' in standard_symbol:
            return standard_symbol.upper()

        # If the symbol is provided as a bare asset (like "SOL", "BTC", or "ETH")
        if '-' not in standard_symbol:
            if exchange_id == 'coinbase':
                standard_symbol = f"{standard_symbol}-USD"
            elif exchange_id == 'binance':
                standard_symbol = f"{standard_symbol}-USDT"
            elif exchange_id == 'drift':
                # For drift, a bare asset means spot data; do not append "-PERP"
                standard_symbol = standard_symbol.upper()

        # Check if we have a direct mapping
        if exchange_id in self.to_exchange_map and standard_symbol in self.to_exchange_map[exchange_id]:
            return self.to_exchange_map[exchange_id][standard_symbol]
        
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
            Symbol in standard format (e.g., BTC-USD)
            
        Raises:
            ValueError: If the symbol cannot be converted
        """
        exchange_id = exchange_name.lower()
        
        if '-' in exchange_symbol and not exchange_symbol.endswith('_PERP'):
            parts = exchange_symbol.split('-')
            if len(parts) == 2:
                return exchange_symbol.upper()
        
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
        supported = []
        for exchange_id, symbols in self.supported_symbols.items():
            if standard_symbol in symbols:
                supported.append(exchange_id)
        return supported
    
    def get_supported_symbols(self, exchange_name: str) -> List[str]:
        exchange_id = exchange_name.lower()
        if exchange_id in self.supported_symbols:
            return list(self.supported_symbols[exchange_id])
        return []
    
    def standardize_asset(self, asset: str) -> str:
        asset = asset.upper()
        return self.ASSET_ALIASES.get(asset, asset)
    
    # -------------------------------------------------------------------------
    # Private methods for exchange-specific conversions
    # -------------------------------------------------------------------------
    
    def _exchange_to_standard(self, exchange_id: str, symbol: str) -> str:
        if exchange_id == "binance":
            return self._binance_to_standard(symbol)
        elif exchange_id == "coinbase":
            return self._coinbase_to_standard(symbol)
        elif exchange_id == "drift":
            return self._drift_to_standard(symbol)
        else:
            return self._generic_to_standard(symbol)
    
    def _binance_to_standard(self, symbol: str) -> str:
        if '-' in symbol:
            parts = symbol.split('-')
            if len(parts) == 2:
                return symbol.upper()
        if "_PERP" in symbol:
            base = re.search(r'([A-Z]+)USDT_PERP', symbol)
            if base:
                return f"{base.group(1)}-PERP"
        for stablecoin in self.STABLECOINS:
            if symbol.endswith(stablecoin):
                base = symbol[:-len(stablecoin)]
                return f"{base}-{stablecoin}"
        for quote_length in [3, 4, 5]:
            if len(symbol) > quote_length:
                base = symbol[:-quote_length]
                quote = symbol[-quote_length:]
                return f"{base}-{quote}"
        raise ValueError(f"Cannot parse Binance symbol: {symbol}")
    
    def _coinbase_to_standard(self, symbol: str) -> str:
        if "-" in symbol:
            parts = symbol.split("-")
            if len(parts) == 2:
                base, quote = parts
                return f"{base}-{quote}"
        raise ValueError(f"Cannot parse Coinbase symbol: {symbol}")
    
    def _drift_to_standard(self, symbol: str) -> str:
        # For drift, if symbol ends with "-PERP", assume perpetual.
        # Otherwise, if no dash is present, assume it's spot and return the bare asset.
        if '-' in symbol:
            return symbol.upper()
        else:
            return symbol.upper()
    
    def _generic_to_standard(self, symbol: str) -> str:
        if "-" in symbol:
            parts = symbol.split("-")
            if len(parts) == 2:
                return symbol.upper()
        for perp_id in self.PERPETUAL_IDENTIFIERS:
            if perp_id in symbol:
                base = re.sub(f"{perp_id}.*", "", symbol)
                base = re.sub(r'[^A-Z]', '', base.upper())
                return f"{base}-PERP"
        for stablecoin in self.STABLECOINS:
            if symbol.endswith(stablecoin):
                base = symbol[:-len(stablecoin)]
                return f"{base}-{stablecoin}"
        match = re.match(r'([A-Z]+)([A-Z]{3,5})$', symbol.upper())
        if match:
            base, quote = match.groups()
            return f"{base}-{quote}"
        raise ValueError(f"Cannot determine base/quote for symbol: {symbol}")
    
    def _standard_to_binance(self, standard_symbol: str) -> str:
        if standard_symbol.endswith("-PERP"):
            base = standard_symbol.split("-")[0]
            return f"{base}USDT_PERP"
        parts = standard_symbol.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid standard symbol: {standard_symbol}")
        base, quote = parts
        return f"{base}{quote}"
    
    def _standard_to_coinbase(self, standard_symbol: str) -> str:
        if standard_symbol.endswith("-PERP"):
            base = standard_symbol.split("-")[0]
            return f"{base}-USD"
        return standard_symbol.upper()
    
    def _standard_to_drift(self, standard_symbol: str) -> str:
        # For drift, if the symbol explicitly includes "-PERP", return it.
        # Otherwise, for spot data, return the bare asset (or adjust if needed).
        if standard_symbol.endswith("-PERP"):
            return standard_symbol.upper()
        else:
            # Here, we assume that spot data for drift is stored using the bare asset.
            return standard_symbol.split("-")[0].upper()


# Example usage:
if __name__ == "__main__":
    mapper = SymbolMapper()
    
    # Register exchanges with their supported symbols.
    # For drift, now we register both spot and perp if needed.
    mapper.register_exchange("binance", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BTCUSDT_PERP"])
    mapper.register_exchange("coinbase", ["BTC-USD", "ETH-USD", "SOL-USD"])
    # For drift, register spot symbols as bare assets and perp symbols as with '-PERP'
    mapper.register_exchange("drift", ["SOL", "BTC-PERP", "ETH-PERP"])
    
    print("Testing conversions with standard symbols:")
    standard_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BTC-PERP"]
    for standard_symbol in standard_symbols:
        print(f"\nTesting standard symbol: {standard_symbol}")
        for exchange in ["binance", "coinbase", "drift"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, standard_symbol)
                print(f"  {standard_symbol} → {exchange}: {ex_sym}")
                back = mapper.from_exchange_symbol(exchange, ex_sym)
                print(f"  {exchange}: {ex_sym} → {back}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
    
    print("\nTesting with symbols already in exchange format:")
    exchange_formats = ["BTCUSDT", "ETH-USD", "SOL-PERP"]
    for symbol in exchange_formats:
        print(f"\nTesting symbol: {symbol}")
        for exchange in ["binance", "coinbase", "drift"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, symbol)
                print(f"  {symbol} → {exchange}: {ex_sym}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
    
    print("\nTesting with bare base assets:")
    bare_assets = ["BTC", "ETH", "SOL"]
    for asset in bare_assets:
        print(f"\nTesting asset: {asset}")
        for exchange in ["binance", "coinbase", "drift"]:
            try:
                ex_sym = mapper.to_exchange_symbol(exchange, asset)
                print(f"  {asset} → {exchange}: {ex_sym}")
            except ValueError as e:
                print(f"  Error for {exchange}: {e}")
