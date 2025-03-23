# examples/strategy_evaluation_example.py

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from supabase import create_client

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtesting.strategy_evaluator import StrategyEvaluator
from src.backtesting.strategies import donchian_channel_breakout

def fetch_data_from_db(symbol='BTC/USDT', exchange='binance', timeframe='1h', start_date=None, end_date=None):
    """
    Fetch historical OHLCV data from your database
    
    Args:
        symbol: Trading pair symbol
        exchange: Exchange name
        timeframe: Timeframe/resolution of the data
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        
    Returns:
        DataFrame with OHLCV data
    """
    # Load database configuration from environment or config file
    # Adjust this part to match your configuration setup
    try:
        with open('../config/db_config.json', 'r') as f:
            db_config = json.load(f)
    except FileNotFoundError:
        # If config file not found, use environment variables
        db_config = {
            'neon': {
                'host': os.environ.get('NEON_DB_HOST'),
                'database': os.environ.get('NEON_DB_NAME'),
                'user': os.environ.get('NEON_DB_USER'),
                'password': os.environ.get('NEON_DB_PASSWORD'),
                'port': os.environ.get('NEON_DB_PORT', 5432)
            },
            'supabase': {
                'url': os.environ.get('SUPABASE_URL'),
                'key': os.environ.get('SUPABASE_KEY')
            }
        }
    
    # Determine which database to use (Neon or Supabase)
    use_neon = True  # Change this based on your preference
    
    if use_neon:
        # Connect to Neon PostgreSQL database
        conn = psycopg2.connect(
            host=db_config['neon']['host'],
            database=db_config['neon']['database'],
            user=db_config['neon']['user'],
            password=db_config['neon']['password'],
            port=db_config['neon']['port']
        )
        
        # Set default date range if not provided
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Query to fetch data
        query = """
        SELECT 
            timestamp, open, high, low, close, volume
        FROM 
            market_data
        WHERE 
            exchange = %s AND
            symbol = %s AND
            timeframe = %s AND
            timestamp BETWEEN %s AND %s
        ORDER BY 
            timestamp
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (exchange, symbol, timeframe, start_date, end_date))
            rows = cursor.fetchall()
            
        conn.close()
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        df.set_index('timestamp', inplace=True)
        
    else:
        # Connect to Supabase
        supabase = create_client(db_config['supabase']['url'], db_config['supabase']['key'])
        
        # Set default date range if not provided
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch data from Supabase
        response = supabase.table('market_data').select('timestamp,open,high,low,close,volume') \
            .eq('exchange', exchange) \
            .eq('symbol', symbol) \
            .eq('timeframe', timeframe) \
            .gte('timestamp', start_date) \
            .lte('timestamp', end_date) \
            .order('timestamp', ascending=True) \
            .execute()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
    # Ensure numeric data types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
        
    return df

def main():
    """Run a complete strategy evaluation example"""
    # Set parameters for data retrieval
    symbol = 'BTC/USDT'
    exchange = 'binance'
    timeframe = '1h'
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Fetching historical data for {symbol} from {exchange}...")
    
    # Fetch data from your database
    data = fetch_data_from_db(symbol, exchange, timeframe, start_date, end_date)
    
    print(f"Data fetched: {len(data)} periods from {data.index[0]} to {data.index[-1]}")
    
    # Define parameter grid for the Donchian Channel strategy
    param_grid = {
        'lookback': list(range(10, 50, 2))  # Test lookback periods from 10 to 48 in steps of 2
    }
    
    # Create the strategy evaluator
    evaluator = StrategyEvaluator(
        data=data,
        strategy_func=donchian_channel_breakout,
        param_grid=param_grid,
        training_window_days=180,  # 6 months training window
        step_days=30,              # 1 month step size
        n_permutations=100         # 100 permutations for Monte Carlo tests
    )
    
    # Run the full analysis
    print("\nRunning full strategy analysis...")
    results = evaluator.run_full_analysis()
    
    # Print summary
    print("\n" + evaluator.summary())
    
    # Plot results
    evaluator.plot_results()
    
    # Display the parameter history from walk forward optimization
    print("\nParameter evolution during walk forward testing:")
    for i, params in enumerate(results['walk_forward']['params_history']):
        date = results['walk_forward']['dates'][i] if i < len(results['walk_forward']['dates']) else 'N/A'
        score = results['walk_forward']['step_results'][i] if i < len(results['walk_forward']['step_results']) else 'N/A'
        print(f"Period {i+1} (ending {date}): {params}, Score: {score}")

if __name__ == "__main__":
    main()