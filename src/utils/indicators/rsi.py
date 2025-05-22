import numpy as np
import pandas as pd
import warnings
import logging

try:
    import talib

    _has_talib_rsi = hasattr(talib, "RSI")
    _has_talib_atr = hasattr(talib, "ATR")
except ImportError:
    talib = None
    _has_talib_rsi = False
    _has_talib_atr = False
logger = logging.getLogger(__name__)
from .base_indicator import BaseIndicator
from src.core.config import Config


class RsiBase:
    """
    Relative Strength Index (RSI) calculator with configurable parameters
    """

    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.prices = []

    def update(self, price):
        """Update RSI calculation with new price"""
        self.prices.append(price)
        if len(self.prices) > self.period * 2:  # Keep sufficient history
            self.prices.pop(0)

        if len(self.prices) >= self.period:
            if talib and _has_talib_rsi:
                return talib.RSI(np.array(self.prices), timeperiod=self.period)[-1]
            else:
                warnings.warn("talib.RSI not found, using fallback RSI implementation.")
                logger.warning(
                    "talib.RSI not found, using fallback RSI implementation."
                )
                return fallback_rsi(np.array(self.prices), period=self.period)[-1]
        return None


class RsiIndicator(BaseIndicator):
    """RSI indicator wrapper with signal generation functionality"""

    def __init__(self, config_path="config/indicator_settings.json"):
        config = Config()
        rsi_config = config.get("indicators", {}).get("rsi", {})

        self.period = rsi_config.get("period", 14)
        self.overbought = rsi_config.get("overbought", 70)
        self.oversold = rsi_config.get("oversold", 30)
        self.filter_signals_by = rsi_config.get("filter_signals_by", "None")
        self.holding_period = rsi_config.get("holding_period", 5)
        self.debug = False
        self.model = RsiBase(self.period, self.overbought, self.oversold)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index, dtype=int)
        current_signal = 0
        bar_count = 0

        if "close" not in df.columns:
            return signals

        if talib and _has_talib_rsi:
            rsi_values = talib.RSI(df["close"], timeperiod=self.period)
        else:
            warnings.warn("talib.RSI not found, using fallback RSI implementation.")
            logger.warning("talib.RSI not found, using fallback RSI implementation.")
            rsi_values = fallback_rsi(df["close"], period=self.period)

        for i in range(len(df)):
            if pd.isna(rsi_values[i]):
                signals.iloc[i] = 0
                continue

            new_signal = 0
            if rsi_values[i] > self.overbought:
                new_signal = -1
            elif rsi_values[i] < self.oversold:
                new_signal = 1

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
                print(f"Bar {i}: RSI={rsi_values[i]:.2f}, Signal={new_signal}")

        return signals

    def _passes_filter(self, df, i):
        # Same filter logic as your existing indicator
        if self.filter_signals_by == "None":
            return True
        if i < 10:
            return True

        # Volatility filter
        if self.filter_signals_by in ("Volatility", "Both"):
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            if talib and _has_talib_atr:
                atr1 = talib.ATR(high, low, close, 1)
                atr10 = talib.ATR(high, low, close, 10)
            else:
                warnings.warn("talib.ATR not found, using fallback ATR implementation.")
                logger.warning(
                    "talib.ATR not found, using fallback ATR implementation."
                )
                atr1 = fallback_atr(high, low, close, 1)
                atr10 = fallback_atr(high, low, close, 10)
            if atr1[i] <= atr10[i]:
                return False

        # Volume filter
        if self.filter_signals_by in ("Volume", "Both"):
            if "volume" not in df.columns:
                return True
            vol = df["volume"].values
            if talib and _has_talib_rsi:
                rsi_vol = talib.RSI(vol, 14)
            else:
                warnings.warn(
                    "talib.RSI not found, using fallback RSI implementation for volume."
                )
                logger.warning(
                    "talib.RSI not found, using fallback RSI implementation for volume."
                )
                rsi_vol = fallback_rsi(vol, period=14)
            if rsi_vol[i] <= 49:
                return False

        return True


def fallback_rsi(prices, period=14):
    prices = np.asarray(prices)
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100.0 - 100.0 / (1.0 + rs)
    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.0
        else:
            upval = 0.0
            downval = -delta
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def fallback_atr(high, low, close, period=14):
    high = np.asarray(high)
    low = np.asarray(low)
    close = np.asarray(close)
    tr = np.maximum(
        high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])
    )
    atr = np.zeros_like(close)
    atr[:period] = np.nan
    atr[period:] = np.convolve(tr, np.ones(period) / period, mode="valid")
    return atr
