# src/utils/inidcators/supertrend.py

import numpy as np
import pandas as pd
import talib
from .base_indicator import BaseIndicator
from src.core.config import Config


def atr(high, low, close, length=10):
    """
    Calculate ATR as a rolling mean of the True Range.
    Returns a NumPy array.
    """
    # Convert inputs to Pandas Series if needed, then to NumPy
    if not isinstance(high, pd.Series):
        high = pd.Series(high)
    if not isinstance(low, pd.Series):
        low = pd.Series(low)
    if not isinstance(close, pd.Series):
        close = pd.Series(close)

    tr = np.maximum(
        high - low,
        np.maximum((high - close.shift()).abs(), (low - close.shift()).abs()),
    )
    # Rolling mean -> convert final result to NumPy
    return tr.rolling(window=length).mean().to_numpy()


def supertrend(high, low, close, atr_length=10, factor=3):
    """
    Standard Supertrend calculation.
    Returns:
      - supertrend line (NumPy array)
      - direction array (NumPy array of 1 or -1)
    """
    # Convert to NumPy arrays for consistent integer indexing
    high_arr = np.array(high)
    low_arr = np.array(low)
    close_arr = np.array(close)

    atr_values = atr(high_arr, low_arr, close_arr, atr_length)
    hl2 = (high_arr + low_arr) / 2

    upper_band = hl2 + factor * atr_values
    lower_band = hl2 - factor * atr_values

    st = np.zeros_like(close_arr)
    direction = np.ones_like(close_arr)

    for i in range(1, len(close_arr)):
        if close_arr[i - 1] > upper_band[i - 1]:
            direction[i] = -1
        elif close_arr[i - 1] < lower_band[i - 1]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]
            if direction[i] == -1:
                # Use Python's built-in max/min, not np.max/min, to compare single floats
                lower_band[i] = max(lower_band[i], lower_band[i - 1])
            else:
                upper_band[i] = min(upper_band[i], upper_band[i - 1])

        st[i] = lower_band[i] if direction[i] == -1 else upper_band[i]

    return st, direction


def k_means_volatility(
    atr_values, training_period=100, highvol=0.75, midvol=0.50, lowvol=0.25
):
    """
    Assign each bar to one of three volatility clusters (high, medium, low)
    based on ATR values.
    Returns:
      - clusters (NumPy int array)
      - centroids (list of NumPy arrays)
    """
    # Ensure atr_values is a NumPy array
    if isinstance(atr_values, pd.Series):
        atr_values = atr_values.to_numpy()

    # We'll use a rolling max/min but do it with Pandas, then convert to arrays
    s = pd.Series(atr_values)
    upper_series = s.rolling(window=training_period).max()
    lower_series = s.rolling(window=training_period).min()

    upper = upper_series.to_numpy()
    lower = lower_series.to_numpy()

    high_volatility = lower + (upper - lower) * highvol
    medium_volatility = lower + (upper - lower) * midvol
    low_volatility = lower + (upper - lower) * lowvol

    # Ensure clusters is an int array
    clusters = np.zeros(len(atr_values), dtype=int)
    centroids = [high_volatility, medium_volatility, low_volatility]

    for i in range(len(atr_values)):
        # c[i] is also valid because c is a NumPy array
        distances = [abs(atr_values[i] - c[i]) for c in centroids]
        clusters[i] = np.argmin(distances)

    return clusters, centroids


def adaptive_supertrend(
    high,
    low,
    close,
    atr_length=10,
    factor=3,
    training_period=100,
    highvol=0.75,
    midvol=0.50,
    lowvol=0.25,
):
    """
    Adaptive Supertrend that first clusters volatility using k_means_volatility,
    then calls the standard Supertrend function.
    """
    # 1. Compute ATR as a NumPy array
    atr_values = atr(high, low, close, atr_length)

    # 2. Cluster volatility
    clusters, centroids = k_means_volatility(
        atr_values,
        training_period=training_period,
        highvol=highvol,
        midvol=midvol,
        lowvol=lowvol,
    )

    # 4. Return standard supertrend
    return supertrend(high, low, close, atr_length, factor)


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    data = pd.DataFrame(
        {
            "high": np.random.rand(200) * 100,
            "low": np.random.rand(200) * 100,
            "close": np.random.rand(200) * 100,
        }
    )

    st_values, st_direction = adaptive_supertrend(
        data["high"], data["low"], data["close"]
    )

    print("Supertrend values shape:", st_values.shape)
    print("Direction array shape:  ", st_direction.shape)
    print("First 10 directions:    ", st_direction[:10])


class Supertrend:
    """
    Supertrend indicator calculator
    """

    def __init__(self, atr_period=14, multiplier=3.0):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.df = None
        self.final_upperband = None
        self.final_lowerband = None

    def calculate(self, df):
        """Calculate Supertrend values for the given OHLC dataframe"""
        self.df = df.copy()

        # Verify needed columns are present
        required_cols = ["high", "low", "close"]
        if not all(col in self.df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in self.df.columns]
            raise ValueError(f"Missing required columns: {missing}")

        # Calculate ATR
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        tr1 = pd.Series(high - low)
        tr2 = pd.Series(abs(high - close.shift(1)))
        tr3 = pd.Series(abs(low - close.shift(1)))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()

        # Calculate Supertrend
        hl2 = (high + low) / 2
        upperband = hl2 + (self.multiplier * atr)
        lowerband = hl2 - (self.multiplier * atr)

        # Initialize Supertrend values
        self.df["supertrend"] = 0.0
        self.df["uptrend"] = True
        self.df["in_uptrend"] = True

        self.final_upperband = upperband.copy()
        self.final_lowerband = lowerband.copy()

        for i in range(self.atr_period, len(self.df)):
            current = i
            prev = i - 1

            # Calculate upper and lower bands
            if close.iloc[current] > self.final_upperband.iloc[prev]:
                self.final_upperband.iloc[current] = max(
                    upperband.iloc[current], self.final_upperband.iloc[prev]
                )
            else:
                self.final_upperband.iloc[current] = upperband.iloc[current]

            if close.iloc[current] < self.final_lowerband.iloc[prev]:
                self.final_lowerband.iloc[current] = min(
                    lowerband.iloc[current], self.final_lowerband.iloc[prev]
                )
            else:
                self.final_lowerband.iloc[current] = lowerband.iloc[current]

            # Determine trend
            if close.iloc[prev] <= self.final_upperband.iloc[prev]:
                self.df.loc[self.df.index[current], "uptrend"] = True
            else:
                self.df.loc[self.df.index[current], "uptrend"] = False

            if (
                self.df["uptrend"].iloc[current]
                and close.iloc[current] <= self.final_upperband.iloc[current]
            ):
                self.df.loc[self.df.index[current], "in_uptrend"] = False
            elif (
                not self.df["uptrend"].iloc[current]
                and close.iloc[current] >= self.final_lowerband.iloc[current]
            ):
                self.df.loc[self.df.index[current], "in_uptrend"] = True
            else:
                self.df.loc[self.df.index[current], "in_uptrend"] = self.df[
                    "in_uptrend"
                ].iloc[prev]

            # Set Supertrend value
            if self.df["in_uptrend"].iloc[current]:
                self.df.loc[self.df.index[current], "supertrend"] = (
                    self.final_lowerband.iloc[current]
                )
            else:
                self.df.loc[self.df.index[current], "supertrend"] = (
                    self.final_upperband.iloc[current]
                )

        return self.df["supertrend"], self.df["in_uptrend"]

    def get_trend_changes(self):
        """Get points where trend changes"""
        if self.df is None:
            return pd.DataFrame()

        trend_changes = pd.DataFrame()

        # Find trend change points
        trend_changes["trend_change"] = self.df["in_uptrend"].diff().fillna(0) != 0
        trend_changes = trend_changes[trend_changes["trend_change"]]

        # Add direction and price info
        if not trend_changes.empty:
            trend_changes["direction"] = self.df.loc[trend_changes.index, "in_uptrend"]
            trend_changes["signal"] = trend_changes["direction"].map(
                {True: "Buy", False: "Sell"}
            )
            trend_changes["price"] = self.df.loc[trend_changes.index, "close"]
            trend_changes["supertrend"] = self.df.loc[trend_changes.index, "supertrend"]

        return trend_changes


class SupertrendIndicator(BaseIndicator):
    """Supertrend indicator wrapper with signal generation functionality"""

    def __init__(
        self, config=None, config_path="config/indicator_settings.json", **kwargs
    ):
        """
        Accepts either a config dict (with atr_length/atr_period and factor/multiplier),
        or falls back to config file or defaults. Supports direct kwargs for flexibility.
        """
        config_obj = Config()
        supertrend_config = config_obj.get("indicators", {}).get("supertrend", {})

        # Support config dict as first argument
        if isinstance(config, dict):
            atr_period = config.get("atr_length", config.get("atr_period", 14))
            multiplier = config.get("factor", config.get("multiplier", 3.0))
            filter_signals_by = config.get(
                "filter_signals_by", supertrend_config.get("filter_signals_by", "None")
            )
            holding_period = config.get(
                "holding_period", supertrend_config.get("holding_period", 5)
            )
        else:
            atr_period = kwargs.get(
                "atr_length",
                kwargs.get("atr_period", supertrend_config.get("atr_period", 14)),
            )
            multiplier = kwargs.get(
                "factor",
                kwargs.get("multiplier", supertrend_config.get("multiplier", 3.0)),
            )
            filter_signals_by = kwargs.get(
                "filter_signals_by", supertrend_config.get("filter_signals_by", "None")
            )
            holding_period = kwargs.get(
                "holding_period", supertrend_config.get("holding_period", 5)
            )

        self.atr_period = atr_period
        self.multiplier = multiplier
        self.filter_signals_by = filter_signals_by
        self.holding_period = holding_period
        self.debug = False
        self.model = Supertrend(self.atr_period, self.multiplier)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate trading signals based on Supertrend indicator"""
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0

        # Ensure we have required columns
        required_cols = ["high", "low", "close"]
        if not all(col in df.columns for col in required_cols):
            return signals

        # Calculate Supertrend
        _, in_uptrend = self.model.calculate(df)

        # Generate signals
        for i in range(len(df)):
            # Skip initial records where Supertrend isn't calculated yet
            if pd.isna(in_uptrend.iloc[i]):
                signals.iloc[i] = 0
                continue

            new_signal = 0
            if i > 0:
                if not in_uptrend.iloc[i - 1] and in_uptrend.iloc[i]:
                    new_signal = 1  # Buy signal when trend changes from down to up
                elif in_uptrend.iloc[i - 1] and not in_uptrend.iloc[i]:
                    new_signal = -1  # Sell signal when trend changes from up to down

            if not self._passes_filter(df, i):
                new_signal = 0

            if new_signal != current_signal:
                bar_count = 0
            else:
                bar_count += 1

            if bar_count >= self.holding_period and new_signal != 0:
                new_signal = 0
                bar_count = 0

            signals.iloc[i] = new_signal
            current_signal = new_signal

            if self.debug and i % 100 == 0:
                print(f"Bar {i}: In Uptrend={in_uptrend.iloc[i]}, Signal={new_signal}")

        return signals

    def _passes_filter(self, df, i):
        """Apply filters to signal generation"""
        if self.filter_signals_by == "None":
            return True
        if i < 10:
            return True

        # Volatility filter
        if self.filter_signals_by in ("Volatility", "Both"):
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            atr1 = talib.ATR(high, low, close, 1)
            atr10 = talib.ATR(high, low, close, 10)
            if atr1[i] <= atr10[i]:
                return False

        # Volume filter
        if self.filter_signals_by in ("Volume", "Both"):
            if "volume" not in df.columns:
                return True
            vol = df["volume"].values
            rsi_vol = talib.RSI(vol, 14)
            if rsi_vol[i] <= 49:
                return False

        return True
