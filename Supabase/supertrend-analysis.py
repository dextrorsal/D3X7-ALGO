# src/examples/supertrend_analysis.py

import asyncio
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# Import your data manager
from src.data.manager import DataManager

# Import your SupertrendIndicator
from src.utils.indicators.supertrend import SupertrendIndicator

async def analyze_with_supertrend(exchange="binance", market="SOL/USDT", 
                                  days=30, provider_type="supabase"):
    """
    Analyze market data with the SupertrendIndicator.
    
    Args:
        exchange: Exchange name
        market: Market symbol
        days: Number of days of data to analyze
        provider_type: Data provider type ('csv' or 'supabase')
    """
    print(f"Analyzing {exchange}/{market} using {provider_type} data provider")
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Define time range (last N days)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Resolution (you can change this as needed)
    resolution = "1h"
    
    # Load data from the specified provider
    df = await data_manager.load_candles(
        exchange, market, resolution, start_time, end_time, provider_type=provider_type
    )
    
    # Check if we got data
    if df.empty:
        print(f"No data found for {exchange}/{market} using {provider_type} provider")
        if provider_type == "supabase":
            print("Falling back to CSV provider...")
            df = await data_manager.load_candles(
                exchange, market, resolution, start_time, end_time, provider_type="csv"
            )
    
    if df.empty:
        print(f"No data available for {exchange}/{market}")
        return
    
    print(f"Loaded {len(df)} candles for analysis")
    
    # Ensure DataFrame has the right column names
    # Supabase might return lowercase column names, while your indicator expects specific case
    column_mapping = {
        'timestamp': 'timestamp',
        'open': 'open', 
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    
    # Rename columns if they exist but with different case
    for expected_col, std_col in column_mapping.items():
        cols = [c for c in df.columns if c.lower() == expected_col.lower()]
        if cols and cols[0] != std_col:
            df.rename(columns={cols[0]: std_col}, inplace=True)
    
    # Initialize the SupertrendIndicator
    supertrend = SupertrendIndicator()
    
    # Generate signals
    signals = supertrend.generate_signals(df)
    
    # Print results
    print(f"Generated {len(signals)} signals")
    print(f"Buy signals: {(signals == 1).sum()}")
    print(f"Sell signals: {(signals == -1).sum()}")
    
    # Create a visualization (optional)
    plt.figure(figsize=(12, 8))
    
    # Price subplot
    plt.subplot(2, 1, 1)
    plt.plot(df.index if df.index.name == 'timestamp' else df['timestamp'], 
             df['close'], label='Price')
    
    # Mark buy/sell signals
    buy_signals = df.index[signals == 1] if df.index.name == 'timestamp' else df.loc[signals == 1, 'timestamp']
    sell_signals = df.index[signals == -1] if df.index.name == 'timestamp' else df.loc[signals == -1, 'timestamp']
    
    if len(buy_signals) > 0:
        buy_prices = df.loc[buy_signals, 'close'] if df.index.name == 'timestamp' else df.loc[signals == 1, 'close']
        plt.scatter(buy_signals, buy_prices, color='green', marker='^', s=100, label='Buy')
    
    if len(sell_signals) > 0:
        sell_prices = df.loc[sell_signals, 'close'] if df.index.name == 'timestamp' else df.loc[signals == -1, 'close']
        plt.scatter(sell_signals, sell_prices, color='red', marker='v', s=100, label='Sell')
    
    plt.title(f'Supertrend Analysis for {market}')
    plt.ylabel('Price')
    plt.legend()
    
    # Signals subplot
    plt.subplot(2, 1, 2)
    plt.plot(df.index if df.index.name == 'timestamp' else df['timestamp'], 
             signals, label='Signal')
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    plt.ylabel('Signal')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(f"{market.replace('/', '_')}_supertrend_analysis.png")
    plt.close()
    
    print(f"Analysis saved to {market.replace('/', '_')}_supertrend_analysis.png")
    
    return signals

async def main():
    """Main function to run analysis with different providers"""
    # Try both providers
    await analyze_with_supertrend(provider_type="supabase")
    await analyze_with_supertrend(provider_type="csv")
    
    # You can also run analysis for multiple markets
    # await analyze_with_supertrend(market="BTC/USDT", provider_type="supabase")
    # await analyze_with_supertrend(market="ETH/USDT", provider_type="supabase")

if __name__ == "__main__":
    asyncio.run(main())