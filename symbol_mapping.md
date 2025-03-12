# Symbol Mapping Guide

## Overview
This document explains how cryptocurrency symbols are mapped between different exchanges in our system. We use a standardized internal format and convert to/from exchange-specific formats as needed.

## Standard Format
- **Spot Markets**: `BASE-QUOTE` (e.g., `BTC-USDT`, `SOL-USDC`)
- **Perpetual Markets**: `BASE-PERP` (e.g., `BTC-PERP`, `SOL-PERP`)

## Exchange-Specific Formats

### Binance (Spot Only)
- **Format**: `BASEQUOTE` (no hyphen)
- **Examples**: 
  - `BTCUSDT`
  - `ETHUSDT`
  - `SOLUSDT`
- **Quote Currency**: Always uses `USDT`
- **Note**: USD and USDC are automatically converted to USDT

### Coinbase (Spot Only)
- **Format**: `BASE-USD`
- **Examples**:
  - `BTC-USD`
  - `ETH-USD`
  - `SOL-USD`
- **Quote Currency**: Always uses `USD`
- **Note**: USDT and USDC are automatically converted to USD

### Drift (Spot and Perpetual)
- **Spot Format**: Just the base asset (e.g., `SOL`, `BTC`, `ETH`)
  - Important: Drift uses ONLY the base asset symbol for spot markets
  - Examples:
    - `SOL` (represents `SOL-USDC` internally)
    - `BTC` (represents `BTC-USDC` internally)
    - `ETH` (represents `ETH-USDC` internally)
- **Perpetual Format**: `BASE-PERP`
  - Examples:
    - `SOL-PERP`
    - `BTC-PERP`
    - `ETH-PERP`
- **Quote Currency**: 
  - Spot: No quote currency in symbol (uses bare asset symbol)
  - Perpetual: Uses `-PERP` suffix

## Supported Assets
- **Core Assets**:
  - `BTC`
  - `ETH`
  - `SOL`
- **Additional Assets**:
  - Binance: Also supports `BNB`

## Quote Currencies
- Binance: `USDT`
- Coinbase: `USD`
- Drift: 
  - Spot: No quote currency in symbol (bare asset symbol represents USDC pair internally)
  - Perpetual: `-PERP` suffix

## Cross-Exchange Conversions
Examples of how symbols are converted between exchanges:

1. **Binance → Coinbase**
   ```
   BTCUSDT → BTC-USD
   ETHUSDT → ETH-USD
   ```

2. **Coinbase → Drift**
   ```
   BTC-USD → BTC (for spot)
   ETH-USD → ETH (for spot)
   ```

3. **Drift → Binance**
   ```
   SOL → SOLUSDT (from spot)
   BTC → BTCUSDT (from spot)
   ```

## Market Support
- **Perpetual Markets**: Only supported by Drift
- **Spot Markets**: Supported by all exchanges

## Usage in Code
The `SymbolMapper` class handles all symbol conversions:

```python
# Initialize mapper
mapper = SymbolMapper()

# Convert to exchange format
binance_symbol = mapper.to_exchange_symbol("binance", "BTC-USDT")  # Returns "BTCUSDT"
coinbase_symbol = mapper.to_exchange_symbol("coinbase", "BTC-USDT")  # Returns "BTC-USD"
drift_symbol = mapper.to_exchange_symbol("drift", "BTC-USDC")  # Returns "BTC"

# Convert from exchange format
standard_symbol = mapper.from_exchange_symbol("binance", "BTCUSDT")  # Returns "BTC-USDT"
```

## Error Handling
- Invalid symbols or unsupported markets will raise a `ValueError`
- Attempting to use perpetual markets on exchanges that don't support them will raise an error
- Quote currency mismatches are automatically converted where possible

## Best Practices
1. Always use the `SymbolMapper` for conversions rather than manual string manipulation
2. Register new markets with the mapper before using them
3. Use try-catch blocks when converting symbols to handle potential errors
4. Verify market support before attempting conversions
5. Remember that each exchange has its preferred quote currency