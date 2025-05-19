import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
from Supabase.Supabase-adapter import SupabaseAdapter

# Constants
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_API_KEY"
DATA_PATH = Path("data/historical/processed")  # Update with your actual path

async def sync_csv_to_supabase():
    """Sync existing CSV files to Supabase."""
    adapter = SupabaseAdapter(SUPABASE_URL, SUPABASE_KEY)
    
    # Walk through the directory structure
    for exchange_dir in DATA_PATH.iterdir():
        if not exchange_dir.is_dir():
            continue
            
        exchange = exchange_dir.name
        print(f"Processing exchange: {exchange}")
        
        for market_dir in exchange_dir.iterdir():
            if not market_dir.is_dir():
                continue
                
            market = market_dir.name
            print(f"  Processing market: {market}")
            
            for resolution_dir in market_dir.iterdir():
                # Handle cases like "SOL/15" or direct timeframe directories
                if resolution_dir.is_dir():
                    parts = resolution_dir.name.split('/')
                    if len(parts) > 1:
                        resolution = parts[1]  # Extract resolution from path like "SOL/15"
                    else:
                        resolution = resolution_dir.name
                        
                    print(f"    Processing resolution: {resolution}")
                    
                    # Process year/month directories
                    for year_dir in resolution_dir.iterdir():
                        if not year_dir.is_dir() or not year_dir.name.isdigit():
                            continue
                            
                        for month_dir in year_dir.iterdir():
                            if not month_dir.is_dir() or not month_dir.name.isdigit():
                                continue
                                
                            # Process CSV files
                            for csv_file in month_dir.glob("*.csv"):
                                print(f"      Processing file: {csv_file}")
                                
                                try:
                                    # Read CSV into DataFrame
                                    df = pd.read_csv(csv_file)
                                    
                                    # Ensure timestamp column is datetime
                                    if 'timestamp' in df.columns:
                                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                                    
                                    # Store in Supabase
                                    await adapter.store_candles(exchange, market, resolution, df)
                                    
                                    print(f"      Successfully processed {csv_file}")
                                    
                                except Exception as e:
                                    print(f"      Error processing {csv_file}: {e}")
    
    print("Sync completed!")

if __name__ == "__main__":
    asyncio.run(sync_csv_to_supabase())