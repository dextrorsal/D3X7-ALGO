# src/data/providers/supabase_provider.py

import os
import pandas as pd
from datetime import datetime
import asyncio
from supabase import create_client
from .base_provider import BaseDataProvider


class SupabaseProvider(BaseDataProvider):
    """
    Supabase data provider that fetches market data from Supabase database.
    """
    
    def __init__(self):
        """
        Initialize the Supabase data provider using environment variables.
        Requires SUPABASE_URL and SUPABASE_KEY environment variables.
        """
        # Get credentials from environment
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_KEY environment variables"
            )
            
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Cache for exchange and market IDs
        self.exchange_cache = {}
        self.market_cache = {}
    
    async def get_or_create_exchange(self, exchange_name: str) -> int:
        """Get exchange ID or create if it doesn't exist."""
        if exchange_name in self.exchange_cache:
            return self.exchange_cache[exchange_name]
            
        # Check if exchange exists
        response = (
            self.supabase.table("exchanges")
            .select("id")
            .eq("name", exchange_name)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            exchange_id = response.data[0]["id"]
        else:
            # Create new exchange
            response = (
                self.supabase.table("exchanges")
                .insert({"name": exchange_name})
                .execute()
            )
            exchange_id = response.data[0]["id"]
        
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
        response = (
            self.supabase.table("markets")
            .select("id")
            .eq("exchange_id", exchange_id)
            .eq("symbol", symbol)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            market_id = response.data[0]["id"]
        else:
            # Parse base and quote assets from symbol
            parts = symbol.split("/")
            if len(parts) == 2:
                base_asset, quote_asset = parts
            else:
                # Handle other formats like SOL-USD, BTC-PERP, etc.
                parts = symbol.split("-")
                if len(parts) == 2:
                    base_asset, quote_asset = parts
                else:
                    # Fallback: check for valid quote assets
                    for q in ["USDT", "USDC", "USD", "PERP"]:
                        if symbol.endswith(q):
                            base_asset = symbol[: -len(q)]
                            quote_asset = q
                            break
                    else:
                    base_asset = symbol
                    quote_asset = "UNKNOWN"
            
            # Create new market
            response = (
                self.supabase.table("markets")
                .insert(
                    {
                        "exchange_id": exchange_id,
                        "symbol": symbol,
                        "base_asset": base_asset,
                        "quote_asset": quote_asset,
                    }
                )
                .execute()
            )
            market_id = response.data[0]["id"]
        
        # Cache the result
        self.market_cache[cache_key] = market_id
        return market_id
    
    async def store_candles(
        self, exchange: str, market: str, resolution: str, candles: list
    ) -> bool:
        """
        Store candles in Supabase.
        Compatible with your UltimateDataFetcher's storage methods.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            candles: List of candles (either StandardizedCandle objects or dictionaries)
            
        Returns:
            bool: Success status
        """
        try:
            # Get market_id
            market_id = await self.get_or_create_market(exchange, market)
            
            # Prepare records for insertion
            records = []
            
            for candle in candles:
                # Handle both StandardizedCandle objects and dictionaries
                if hasattr(candle, "timestamp"):
                    # It's a StandardizedCandle object
                    timestamp = candle.timestamp.isoformat()
                    open_price = candle.open
                    high_price = candle.high
                    low_price = candle.low
                    close_price = candle.close
                    volume = candle.volume
                else:
                    # It's a dictionary
                    if isinstance(candle["timestamp"], str):
                        timestamp = candle["timestamp"]
                    else:
                        timestamp = candle["timestamp"].isoformat()
                        
                    open_price = candle["open"]
                    high_price = candle["high"]
                    low_price = candle["low"]
                    close_price = candle["close"]
                    volume = candle["volume"]
                
                record = {
                    "market_id": market_id,
                    "resolution": resolution,
                    "timestamp": timestamp,
                    "open": float(open_price),
                    "high": float(high_price),
                    "low": float(low_price),
                    "close": float(close_price),
                    "volume": float(volume),
                }
                records.append(record)
            
            # Insert in batches to avoid timeouts
            batch_size = 500
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                self.supabase.table("candles").insert(batch).execute()
                # Simple throttling to avoid overwhelming the API
                await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"Error storing candles: {e}")
            return False
    
    async def load_candles(
        self,
        exchange: str,
        market: str,
        resolution: str,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Load candles from Supabase.
        Compatible with your UltimateDataFetcher's loading methods.
        
        Args:
            exchange: Exchange name
            market: Market symbol
            resolution: Candle resolution
            start_time: Start time
            end_time: End time
            
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
            response = (
                self.supabase.table("candles")
                .select("timestamp,open,high,low,close,volume")
                .eq("market_id", market_id)
                .eq("resolution", resolution)
                .gte("timestamp", start_iso)
                .lte("timestamp", end_iso)
                .order("timestamp", desc=False)
                .execute()
            )
            
            if response.data:
                # Convert to DataFrame
                df = pd.DataFrame(response.data)
                
                # Convert timestamp to datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error loading candles: {e}")
            return pd.DataFrame()
