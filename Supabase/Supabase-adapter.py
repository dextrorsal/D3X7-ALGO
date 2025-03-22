from supabase import create_client
import pandas as pd
from datetime import datetime
import asyncio
from typing import List, Dict, Any

class SupabaseAdapter:
    """
    Adapter class to bridge your existing storage system with Supabase.
    This allows you to keep using your existing code while adding Supabase support.
    """
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize the Supabase adapter with credentials."""
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Cache for exchanges and markets to avoid repeated lookups
        self.exchange_cache = {}
        self.market_cache = {}
    
    async def get_or_create_exchange(self, exchange_name: str) -> int:
        """Get exchange ID or create if it doesn't exist."""
        if exchange_name in self.exchange_cache:
            return self.exchange_cache[exchange_name]
            
        # Check if exchange exists
        response = self.supabase.table('exchanges').select('id').eq('name', exchange_name).execute()
        
        if response.data and len(response.data) > 0:
            exchange_id = response.data[0]['id']
        else:
            # Create new exchange
            response = self.supabase.table('exchanges').insert({'name': exchange_name}).execute()
            exchange_id = response.data[0]['id']
        
        # Cache the result
        self.exchange_cache[exchange_name] = exchange_id
        return exchange_id
    
    async def get_or_create_market(self, exchange_name: str, symbol: str) -> int:
        """Get market ID or create if it doesn't exist."""
        cache_key = f"{exchange_name}:{symbol}"
        if cache_key in self.market_cache:
            return self.market_cache[cache_key]
            
        # Get exchange_id
        exchange_id = await self.get_or_create_exchange(exchange_name)
        
        # Check if market exists
        response = self.supabase.table('markets').select('id').eq('exchange_id', exchange_id).eq('symbol', symbol).execute()
        
        if response.data and len(response.data) > 0:
            market_id = response.data[0]['id']
        else:
            # Parse base and quote assets from symbol
            parts = symbol.split('/')
            if len(parts) == 2:
                base_asset, quote_asset = parts
            else:
                # Handle other formats like SOL-USD, BTC-PERP, etc.
                parts = symbol.split('-')
                if len(parts) == 2:
                    base_asset, quote_asset = parts
                else:
                    # Fallback
                    base_asset = symbol
                    quote_asset = "UNKNOWN"
            
            # Create new market
            response = self.supabase.table('markets').insert({
                'exchange_id': exchange_id,
                'symbol': symbol,
                'base_asset': base_asset,
                'quote_asset': quote_asset
            }).execute()
            market_id = response.data[0]['id']
        
        # Cache the result
        self.market_cache[cache_key] = market_id
        return market_id
    
    async def store_candles(self, exchange: str, market: str, resolution: str, df: pd.DataFrame) -> bool:
        """
        Store candles from a pandas DataFrame into Supabase.
        Compatible with your ProcessedDataStorage format.
        
        Args:
            exchange: Exchange name (e.g., 'binance')
            market: Market symbol (e.g., 'SOL/USDT')
            resolution: Candle timeframe (e.g., '1m', '5m', '1h')
            df: DataFrame with OHLCV data
        
        Returns:
            bool: Success status
        """
        try:
            # Get market_id
            market_id = await self.get_or_create_market(exchange, market)
            
            # Prepare records for insertion
            records = []
            
            # Handle different DataFrame structures
            timestamp_col = 'timestamp' if 'timestamp' in df.columns else df.index.name
            
            for _, row in df.iterrows():
                if timestamp_col == df.index.name:
                    timestamp = row.name
                else:
                    timestamp = row[timestamp_col]
                
                # Convert timestamp to ISO format if it's a datetime
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()
                
                record = {
                    'market_id': market_id,
                    'resolution': resolution,
                    'timestamp': timestamp,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
                records.append(record)
            
            # Insert in batches to avoid timeouts
            batch_size = 500
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                response = self.supabase.table('candles').insert(batch).execute()
                
                # Simple throttling to avoid overwhelming the API
                await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"Error storing candles: {e}")
            return False
    
    async def load_candles(self, exchange: str, market: str, resolution: str, 
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Load candles from Supabase.
        Compatible with your ProcessedDataStorage.load_candles method.
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Get market_id
            market_id = await self.get_or_create_market(exchange, market)
            
            # Format timestamps
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            # Query Supabase
            response = self.supabase.table('candles') \
                .select('timestamp,open,high,low,close,volume') \
                .eq('market_id', market_id) \
                .eq('resolution', resolution) \
                .gte('timestamp', start_iso) \
                .lte('timestamp', end_iso) \
                .order('timestamp', desc=False) \
                .execute()
            
            if response.data:
                # Convert to DataFrame
                df = pd.DataFrame(response.data)
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error loading candles: {e}")
            return pd.DataFrame()

    async def store_prediction(self, exchange: str, market: str, resolution: str,
                             timestamp: datetime, model_version: str,
                             direction_prediction: float, magnitude_prediction: float,
                             signal: int) -> bool:
        """
        Store ML model prediction in Supabase.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle timeframe
            timestamp: Prediction timestamp
            model_version: ML model version (e.g., 'pytorch_v1.0')
            direction_prediction: Probability of upward movement (0-1)
            magnitude_prediction: Predicted percent change
            signal: Trading signal (1=buy, -1=sell, 0=hold)
            
        Returns:
            bool: Success status
        """
        try:
            # Get market_id
            market_id = await self.get_or_create_market(exchange, market)
            
            # Prepare record
            record = {
                'market_id': market_id,
                'resolution': resolution,
                'timestamp': timestamp.isoformat(),
                'model_version': model_version,
                'direction_prediction': float(direction_prediction),
                'magnitude_prediction': float(magnitude_prediction),
                'signal': int(signal)
            }
            
            # Insert the prediction
            self.supabase.table('predictions').insert(record).execute()
            
            return True
            
        except Exception as e:
            print(f"Error storing prediction: {e}")
            return False