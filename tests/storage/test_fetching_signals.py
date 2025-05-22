"""
Test script for fetching data and generating signals from different indicators.
This allows testing the integration between the data fetching and signal generation components.
"""

import asyncio
import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import pytest
import pytest_asyncio
from pathlib import Path

from src.core.config import Config, ExchangeConfig, ExchangeCredentials
from src.core.models import TimeRange
from src.exchanges import BinanceHandler
from src.utils.indicators.rsi import RsiIndicator
from src.utils.indicators.supertrend import SupertrendIndicator
from src.utils.indicators.knn import KNNIndicator
from src.utils.indicators.logistic import LogisticRegressionIndicator
from src.utils.indicators.lorentzian import LorentzianIndicator

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("reports/signal_test_results")
# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Fixture: Binance Exchange Handler
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def binance_handler():
    """Create a Binance handler with test configuration."""
    config = ExchangeConfig(
        name="binance",
        credentials=None,  # Public endpoints require no credentials
        rate_limit=10,
        markets=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        base_url="https://api.binance.com",
        enabled=True,
    )
    handler = BinanceHandler(config)

    try:
        # Connect to Binance
        await handler.start()
        yield handler
    finally:
        # Disconnect when done
        await handler.stop()


# ---------------------------------------------------------------------------
# Fixture: Time Range (last 5 days)
# ---------------------------------------------------------------------------
@pytest.fixture
def time_range():
    """Provide a time range for the last 5 days."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=5)
    return TimeRange(start=start_time, end=end_time)


# ---------------------------------------------------------------------------
# Test data fetching and signal generation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fetch_and_generate_signals(binance_handler, time_range):
    """Test fetching data and generating signals."""
    # Fetch data
    market = "BTCUSDT"
    resolution = "1h"  # 1-hour candles

    logger.info(
        f"Fetching {market} data for the last 5 days with {resolution} resolution..."
    )
    candles = await binance_handler.fetch_historical_candles(
        market=market, time_range=time_range, resolution=resolution
    )

    logger.info(f"Fetched {len(candles)} candles")

    # Convert to DataFrame
    data = []
    for candle in candles:
        data.append(
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
        )

    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)

    # Show data sample
    logger.info(f"Data sample:\n{df.head()}")

    # Generate signals using different indicators
    indicators = {
        "RSI": RsiIndicator(),
        "Supertrend": SupertrendIndicator(),
        "KNN": KNNIndicator(),
        "Logistic": LogisticRegressionIndicator(),
        "Lorentzian": LorentzianIndicator(),
    }

    # Create a plot with price data
    plt.figure(figsize=(12, 8))
    plt.subplot(len(indicators) + 1, 1, 1)
    plt.plot(df.index, df["close"], label=f"{market} Close Price")
    plt.title(f"{market} Price and Indicator Signals (Last 5 Days)")
    plt.legend()
    plt.grid(True)

    # Generate and plot signals for each indicator
    results = {}
    for i, (name, indicator) in enumerate(indicators.items(), 2):
        logger.info(f"Generating {name} signals...")
        try:
            # Prepare data in the format expected by indicators
            indicator_data = df.copy()

            # Generate signals
            signals = indicator.generate_signals(indicator_data)

            # Count signals of each type
            buy_count = len(signals[signals == 1])
            sell_count = len(signals[signals == -1])
            neutral_count = len(signals[signals == 0])

            logger.info(
                f"{name} signal counts: Buy={buy_count}, Sell={sell_count}, Neutral={neutral_count}"
            )

            # Plot signals
            plt.subplot(len(indicators) + 1, 1, i)

            # Plot buy signals as green markers
            buy_indices = signals[signals == 1].index
            if not buy_indices.empty:
                buy_prices = df.loc[buy_indices, "close"]
                plt.scatter(
                    buy_indices,
                    buy_prices,
                    color="green",
                    marker="^",
                    s=50,
                    label="Buy",
                )

            # Plot sell signals as red markers
            sell_indices = signals[signals == -1].index
            if not sell_indices.empty:
                sell_prices = df.loc[sell_indices, "close"]
                plt.scatter(
                    sell_indices,
                    sell_prices,
                    color="red",
                    marker="v",
                    s=50,
                    label="Sell",
                )

            plt.plot(df.index, df["close"], color="blue", alpha=0.3)
            plt.title(f"{name} Signals")
            plt.legend()
            plt.grid(True)

            # Save results
            results[name] = {
                "signals": signals,
                "buy_count": buy_count,
                "sell_count": sell_count,
                "neutral_count": neutral_count,
            }

        except Exception as e:
            logger.error(f"Error generating {name} signals: {str(e)}")

    # Save plot
    plot_path = OUTPUT_DIR / f"{market.lower()}_signals.png"
    plt.tight_layout()
    plt.savefig(plot_path)
    logger.info(f"Saved signals plot to {plot_path}")

    # Save signal data
    signal_data = pd.DataFrame()
    signal_data["price"] = df["close"]

    for name, result in results.items():
        if "signals" in result:
            signal_data[name] = result["signals"]

    csv_path = OUTPUT_DIR / f"{market.lower()}_signals.csv"
    signal_data.to_csv(csv_path)
    logger.info(f"Saved signal data to {csv_path}")

    # Save analysis summary
    summary_path = OUTPUT_DIR / f"{market.lower()}_analysis.txt"
    with open(summary_path, "w") as f:
        f.write(f"Signal Analysis for {market} (Last 5 Days)\n")
        f.write("=" * 50 + "\n\n")

        for name, result in results.items():
            if all(k in result for k in ["buy_count", "sell_count", "neutral_count"]):
                f.write(f"{name} Indicator:\n")
                f.write(f"  Buy Signals:     {result['buy_count']}\n")
                f.write(f"  Sell Signals:    {result['sell_count']}\n")
                f.write(f"  Neutral Signals: {result['neutral_count']}\n")
                f.write("\n")

    logger.info(f"Saved analysis summary to {summary_path}")

    # Verify at least one indicator produced signals
    assert any(len(result.get("signals", [])) > 0 for result in results.values())


# ---------------------------------------------------------------------------
# Run tests directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main(["-v", __file__])
