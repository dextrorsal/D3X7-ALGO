# Data Fetching Scripts

This directory contains scripts for fetching cryptocurrency data from various sources.

## Scripts

- `fetch.py`: Main launcher script for fetching data from cryptocurrency exchanges
- `fetch_btc_data.py`: Script to fetch Bitcoin data specifically
- `fetch_all.py`: Script to fetch data from all configured exchanges
- `test_fetch.py`: Test script for the fetching functionality

## Usage

These scripts can be run directly from the command line. For example:

```bash
# Show available exchanges and markets
python src/scripts/fetching/fetch.py list

# Fetch historical data for the last 7 days
python src/scripts/fetching/fetch.py historical --days 7 --markets BTC-PERP ETH-PERP SOL-PERP --resolution 1D

# Fetch historical data with specific date range
python src/scripts/fetching/fetch.py historical --start-date "2023-01-01" --end-date "2023-01-31" --markets BTC-PERP --exchanges binance

# Start live data fetching
python src/scripts/fetching/fetch.py live --markets BTC-PERP ETH-PERP --resolution 15 --interval 30
```