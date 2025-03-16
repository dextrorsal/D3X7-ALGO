# Scripts

This directory contains various scripts for the Ultimate Data Fetcher project.

## Structure

- **data_fetching/**: Scripts for fetching data from various sources
  - `fetch.py`: Main launcher script for fetching data
  - `fetch_btc_data.py`: Script to fetch BTC data
  - `fetch_all.py`: Script to fetch data from all exchanges

- **trading/**: Scripts for trading operations
  - `trade.py`: Command Line Interface for Live Trading

## Usage

These scripts can be run directly from the command line. For example:

```bash
# Fetch data
python src/scripts/data_fetching/fetch.py list

# Run live trading
python src/scripts/trading/trade.py --strategy supertrend --market SOL-PERP
```