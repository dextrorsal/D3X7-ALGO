# src/strategy/sol_spot_strategy.py
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from .segmented import SegmentedStrategy
from src.utils.indicators.wrapper_supertrend import SupertrendIndicator
from src.utils.indicators.lorentzian import LorentzianIndicator
from src.utils.indicators.wrapper_rsi import RsiIndicator
from src.utils.indicators.knn import KNNIndicator
from src.utils.indicators.wrapper_macd import MacdIndicator
import logging

logger = logging.getLogger(__name__)


class SOLSpotStrategy(SegmentedStrategy):
    """
    Strategy optimized for SOL spot trading on Solana DEXes.
    Combines regime detection with adaptive weighting and SOL-specific filters.
    """

    def __init__(self, config: Dict):
        """
        Initialize SOL-optimized strategy with custom indicator configurations.

        Parameters:
            config: Configuration dictionary
        """
        # SOL-specific configuration parameters
        config.setdefault("volatility_threshold", 0.025)  # SOL can be volatile
        config.setdefault("trend_threshold", 0.45)  # Catch trends earlier for SOL
        config.setdefault("regime_window", 15)  # Shorter for faster adaptation
        config.setdefault("consensus_threshold", 0.15)  # Higher for stronger signals
        config.setdefault("adaptive_weights", True)  # Use adaptive weights

        # Create indicators optimized for SOL

        # Trending market indicators
        trend_indicators = [
            SupertrendIndicator(
                {
                    "atr_length": 10,
                    "factor": 2.5,  # Lower than default (3.0) to catch SOL moves earlier
                }
            ),
            LorentzianIndicator(
                {
                    "general_settings": {"neighbors_count": 8, "max_bars_back": 2000},
                    "filters": {"use_volatility_filter": True},
                }
            ),
            MacdIndicator(
                {
                    "fast_period": 10,  # Faster periods for SOL
                    "slow_period": 21,  # Slightly faster than default
                    "signal_period": 9,
                }
            ),
        ]
        trend_weights = [0.5, 0.3, 0.2]  # Higher weight on Supertrend for trends

        # Ranging market indicators
        range_indicators = [
            RsiIndicator(
                {
                    "period": 14,
                    "overbought": 68,  # Adjusted for SOL (tends to run higher before reversing)
                    "oversold": 32,
                }
            ),
            KNNIndicator(
                {
                    "short_period": 12,  # Faster for SOL
                    "long_period": 26,
                    "volatility_filter": True,  # Important for SOL
                }
            ),
            SupertrendIndicator(
                {
                    "atr_length": 14,
                    "factor": 3.0,  # Standard for ranging
                }
            ),
        ]
        range_weights = [0.5, 0.3, 0.2]  # Higher weight on RSI for ranges

        # Volatile market indicators
        volatile_indicators = [
            SupertrendIndicator(
                {
                    "atr_length": 8,  # Shorter period for volatile conditions
                    "factor": 2.0,  # Lower factor for faster signals
                }
            ),
            RsiIndicator(
                {
                    "period": 10,  # Faster RSI for volatile conditions
                    "overbought": 75,  # Wider thresholds for volatile markets
                    "oversold": 25,
                }
            ),
            LorentzianIndicator(
                {  # Good for classification in volatile periods
                    "general_settings": {"neighbors_count": 8, "max_bars_back": 2000},
                    "filters": {
                        "use_volatility_filter": True,
                        "use_adx_filter": True,  # Add ADX filter for volatile periods
                        "adx_threshold": 30,  # Higher threshold for volatility
                    },
                }
            ),
        ]
        volatile_weights = [0.4, 0.4, 0.2]  # Balance between fast indicators

        # Initialize the base segmented strategy
        super().__init__(
            config=config,
            trend_indicators=trend_indicators,
            range_indicators=range_indicators,
            volatile_indicators=volatile_indicators,
            trend_weights=trend_weights,
            range_weights=range_weights,
            volatile_weights=volatile_weights,
        )

        # Track adaptive performance
        self.performance_history = {
            "regime_performance": {"trend": [], "range": [], "volatile": []},
            "signal_quality": [],
            "weight_adjustments": [],
        }

    def _detect_market_regime(self, df: pd.DataFrame) -> str:
        """
        Enhanced market regime detection for SOL.
        Uses additional SOL-specific metrics for better classification.

        Returns:
            str: "trend", "range", or "volatile"
        """
        if len(df) < self.regime_window:
            return "trend"  # Default when insufficient data

        # Get baseline regime from parent method
        base_regime = super()._detect_market_regime(df)

        # Add SOL-specific enhancements
        window = df.iloc[-self.regime_window :]

        # Calculate SOL-specific volatility using Bollinger Bandwidth
        # SOL tends to have higher bandwidth during volatile periods
        typical_price = (window["high"] + window["low"] + window["close"]) / 3
        sma20 = typical_price.rolling(20).mean()
        std20 = typical_price.rolling(20).std()
        upper_band = sma20 + 2 * std20
        lower_band = sma20 - 2 * std20
        bandwidth = (upper_band - lower_band) / sma20
        current_bandwidth = bandwidth.iloc[-1] if not pd.isna(bandwidth.iloc[-1]) else 0

        # Calculate SOL trend strength
        # SOL often trends more strongly than other assets
        price_change = abs(window["close"].iloc[-1] - window["close"].iloc[0])
        price_range = window["high"].max() - window["low"].min()
        directional_strength = price_change / price_range if price_range > 0 else 0

        # Volume spike detection (SOL often has volume spikes in volatile regimes)
        if "volume" in df.columns:
            vol_avg = window["volume"].mean()
            current_vol = window["volume"].iloc[-1]
            vol_ratio = current_vol / vol_avg if vol_avg > 0 else 1
            vol_spike = vol_ratio > 2.0  # Volume more than 2x average
        else:
            vol_spike = False

        # Enhanced regime detection logic for SOL
        # 1. Check for high volatility first
        if current_bandwidth > 0.06 or vol_spike:
            logger.debug(
                f"Detected volatile regime (bandwidth: {current_bandwidth:.4f}, vol_spike: {vol_spike})"
            )
            return "volatile"
        # 2. Check for strong trending
        elif directional_strength > self.trend_threshold:
            logger.debug(
                f"Detected trending regime (directional_strength: {directional_strength:.4f})"
            )
            return "trend"
        # 3. Default to ranging if not volatile or trending
        else:
            logger.debug(
                f"Detected ranging regime (directional_strength: {directional_strength:.4f})"
            )
            return "range"

    def _adjust_weights(
        self, df: pd.DataFrame, regime: str, indicators: List, weights: List[float]
    ) -> List[float]:
        """
        Dynamically adjust indicator weights based on recent performance.

        Parameters:
            df: DataFrame with market data
            regime: Current market regime
            indicators: List of active indicators
            weights: Current weights

        Returns:
            List[float]: Updated weights
        """
        if not self.config.get("adaptive_weights", False) or len(df) < 20:
            return weights.copy()

        # Store original weights for tracking changes
        original_weights = weights.copy()
        updated_weights = weights.copy()

        # Get recent price movement
        recent_returns = df["close"].pct_change().iloc[-20:].values
        future_return = (
            df["close"].pct_change().shift(-1).iloc[-21]
        )  # Next bar's return

        # Assess each indicator's recent performance
        for i, indicator in enumerate(indicators):
            if i >= len(updated_weights):
                continue

            # Generate signals on recent data
            signals = indicator.generate_signals(df.iloc[-30:])

            if len(signals) < 2:
                continue

            # Get last signal
            last_signal = signals.iloc[-2]  # Use second-to-last to match with return

            # Calculate if signal was right about direction
            signal_correct = (last_signal > 0 and future_return > 0) or (
                last_signal < 0 and future_return < 0
            )

            # Adjust weight based on correctness
            adjustment = 0.1  # 10% adjustment
            if signal_correct:
                updated_weights[i] *= 1 + adjustment
            else:
                updated_weights[i] *= (
                    1 - adjustment * 0.5
                )  # Penalize less for wrong signals

        # Normalize weights to maintain scale
        total = sum(updated_weights)
        if total > 0:
            updated_weights = [
                w / total * len(updated_weights) for w in updated_weights
            ]

        # Store adjustment for analysis
        self.performance_history["weight_adjustments"].append(
            {"regime": regime, "original": original_weights, "updated": updated_weights}
        )

        return updated_weights

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate SOL-optimized trading signals with adaptive weighting.

        Parameters:
            df: DataFrame with OHLCV market data

        Returns:
            pd.Series: Trading signals (1=long, -1=short, 0=neutral)
        """
        # Detect current market regime
        regime = self._detect_market_regime(df)
        self.detected_regimes.append(regime)

        # Select appropriate indicators and weights based on regime
        if regime == "trend":
            indicators = self.trend_indicators
            weights = self.trend_weights
        elif regime == "range":
            indicators = self.range_indicators
            weights = self.range_weights
        else:  # volatile
            indicators = self.volatile_indicators
            weights = self.volatile_weights

        # Adjust weights if adaptive mode is enabled
        if self.config.get("adaptive_weights", False):
            updated_weights = self._adjust_weights(df, regime, indicators, weights)
            # Update the regime-specific weights for future use
            if regime == "trend":
                self.trend_weights = updated_weights
            elif regime == "range":
                self.range_weights = updated_weights
            else:  # volatile
                self.volatile_weights = updated_weights

        # Generate weighted signals
        weighted_signals = []
        for indicator, weight in zip(indicators, weights):
            signals = indicator.generate_signals(df)
            weighted_signals.append(signals * weight)

        # If no signals are produced, default to neutral
        if not weighted_signals:
            return pd.Series(0, index=df.index)

        # Combine signals
        combined_df = pd.concat(weighted_signals, axis=1)
        summed_signals = combined_df.sum(axis=1)

        # Final signals based on threshold
        final_signals = summed_signals.apply(
            lambda x: 1 if x > self.threshold else (-1 if x < -self.threshold else 0)
        )

        # Apply SOL-specific filters to improve signal quality

        # 1. Avoid trading during extreme volatility events
        if len(df) > 20:
            returns = df["close"].pct_change()
            volatility = returns.rolling(10).std()
            if len(volatility) >= len(final_signals):
                extreme_vol = (
                    volatility.iloc[-len(final_signals) :] > 0.05
                )  # 5% daily std dev is extreme
                final_signals[extreme_vol] = 0  # Don't trade during extreme volatility

        # 2. Filter against major market trend for SOL
        # SOL tends to follow overall market direction strongly
        if len(df) > 50:
            sma50 = df["close"].rolling(50).mean()
            sma20 = df["close"].rolling(20).mean()

            if len(sma50) >= len(final_signals) and len(sma20) >= len(final_signals):
                sma50 = sma50.iloc[-len(final_signals) :]
                sma20 = sma20.iloc[-len(final_signals) :]
                price = df["close"].iloc[-len(final_signals) :]

                # Strong uptrend (price > sma20 > sma50)
                strong_uptrend = (price > sma20) & (sma20 > sma50)
                # Strong downtrend (price < sma20 < sma50)
                strong_downtrend = (price < sma20) & (sma20 < sma50)

                # Don't take short positions in strong uptrends
                final_signals[strong_uptrend & (final_signals == -1)] = 0
                # Don't take long positions in strong downtrends
                final_signals[strong_downtrend & (final_signals == 1)] = 0

        # 3. SOL-specific momentum filter
        # SOL tends to have stronger momentum follow-through than other assets
        if len(df) > 14:
            momentum = df["close"].pct_change(3).rolling(5).sum()
            if len(momentum) >= len(final_signals):
                momentum = momentum.iloc[-len(final_signals) :]
                strong_up_momentum = momentum > 0.1  # 10% gain over 5 days
                strong_down_momentum = momentum < -0.1  # 10% loss over 5 days

                # Strengthen signals in direction of momentum
                final_signals[strong_up_momentum & (final_signals == 1)] = 1
                final_signals[strong_down_momentum & (final_signals == -1)] = -1

                # Weaken contrary signals
                final_signals[strong_up_momentum & (final_signals == -1)] = 0
                final_signals[strong_down_momentum & (final_signals == 1)] = 0

        # Track signal performance for this regime
        if len(df) > 1:
            future_returns = df["close"].pct_change().shift(-1)
            if len(future_returns) >= len(final_signals):
                matched_returns = future_returns.iloc[-(len(final_signals) + 1) : -1]
                matched_signals = final_signals.iloc[
                    :-1
                ]  # Exclude last signal (no future return yet)

                # Calculate if signals predicted direction correctly
                signal_quality = (matched_signals * matched_returns).mean()
                self.performance_history["regime_performance"][regime].append(
                    signal_quality
                )
                self.performance_history["signal_quality"].append(
                    {"regime": regime, "quality": signal_quality}
                )

        return final_signals

    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics for the SOL trading strategy.

        Returns:
            Dict: Performance metrics by regime, signal quality, etc.
        """
        regime_stats = super().get_regime_statistics()

        # Add SOL-specific performance metrics
        metrics = {
            "regime_statistics": regime_stats,
            "current_regime": self.get_current_regime(),
        }

        # Add regime-specific performance if available
        for regime, performances in self.performance_history[
            "regime_performance"
        ].items():
            if performances:
                metrics[f"{regime}_avg_quality"] = np.mean(performances)
                metrics[f"{regime}_samples"] = len(performances)

        # Overall signal quality
        all_qualities = [
            item["quality"]
            for item in self.performance_history["signal_quality"]
            if not pd.isna(item["quality"])
        ]
        if all_qualities:
            metrics["overall_signal_quality"] = np.mean(all_qualities)
            metrics["quality_samples"] = len(all_qualities)

        # Current weights
        metrics["current_weights"] = {
            "trend": self.trend_weights,
            "range": self.range_weights,
            "volatile": self.volatile_weights,
        }

        return metrics
