import pandas as pd
from datetime import datetime
from typing import List, Union
from src.Supabase.Supabase_adapter import SupabaseAdapter


class SupabaseDataStorage:
    """
    Storage class for OHLCV data using Supabase as the backend.
    Provides store_candles and load_candles methods compatible with DataManager.
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        self.adapter = SupabaseAdapter(supabase_url, supabase_key)

    async def store_candles(
        self,
        exchange: str,
        market: str,
        resolution: str,
        candles: Union[List, pd.DataFrame],
    ):
        """
        Store candles in Supabase. Accepts a list of StandardizedCandle or a DataFrame.
        """
        # Convert to DataFrame if needed
        if isinstance(candles, list) and candles and hasattr(candles[0], "timestamp"):
            df = pd.DataFrame([candle.__dict__ for candle in candles])
        elif isinstance(candles, pd.DataFrame):
            df = candles
        else:
            raise ValueError(
                "Candles must be a list of StandardizedCandle objects or a DataFrame"
            )
        # Ensure timestamp is datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        await self.adapter.store_candles(exchange, market, resolution, df)

    async def load_candles(
        self,
        exchange: str,
        market: str,
        resolution: str,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Load candles from Supabase for the given time range.
        """
        return await self.adapter.load_candles(
            exchange, market, resolution, start_time, end_time
        )
