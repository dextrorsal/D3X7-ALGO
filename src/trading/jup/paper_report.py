#!/usr/bin/env python3
import json
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def load_all_trade_logs(logs_dir: str = "data/trade_logs") -> pd.DataFrame:
    """
    Loads all JSON trade log files from the specified directory and combines them into a single DataFrame.
    Assumes each file is a list of trade objects.
    """
    trades = []
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print(f"Directory {logs_path} does not exist. No logs to load.")
        return pd.DataFrame()

    for file in logs_path.glob("*.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                # If the log is just a single trade dict, wrap it in a list
                if isinstance(data, dict):
                    data = [data]
                trades.extend(data)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    df = pd.DataFrame(trades)
    # Convert timestamps to datetime if column exists
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

def calculate_performance_metrics(df: pd.DataFrame, starting_capital: float = 10000.0) -> dict:
    """
    Calculate and return a dictionary of performance metrics from the trades DataFrame.
    Expects 'profit_loss' to exist for closed trades. 
    """
    metrics = {}
    total_trades = len(df)
    metrics["total_trades"] = total_trades
    
    # Profitable trades
    if "profit_loss" in df.columns:
        df_filled = df.fillna({"profit_loss": 0})
        profitable_trades = df_filled[df_filled["profit_loss"] > 0]
        metrics["profitable_trades"] = len(profitable_trades)
        metrics["percent_profitable"] = (
            len(profitable_trades) / total_trades * 100 if total_trades else 0
        )

        # Net PnL
        net_pnl = df_filled["profit_loss"].sum()
        metrics["net_pnl"] = net_pnl
        
        # Build an equity curve by summing profit_loss in chronological order
        df_filled = df_filled.sort_values("timestamp")
        df_filled["cumulative_pnl"] = df_filled["profit_loss"].cumsum()
        df_filled["equity"] = starting_capital + df_filled["cumulative_pnl"]
        
        # Max drawdown calculation
        df_filled["rolling_max"] = df_filled["equity"].cummax()
        df_filled["drawdown"] = (df_filled["equity"] - df_filled["rolling_max"]) / df_filled["rolling_max"]
        max_drawdown = df_filled["drawdown"].min()
        metrics["max_drawdown_pct"] = max_drawdown
        
        # For convenience, return the final DataFrame so we can plot
        metrics["df_equity"] = df_filled
    else:
        # If 'profit_loss' is missing, we can't compute PnL-based metrics
        metrics["profitable_trades"] = 0
        metrics["percent_profitable"] = 0
        metrics["net_pnl"] = 0
        metrics["max_drawdown_pct"] = None
        metrics["df_equity"] = None

    return metrics

def plot_equity_curve(df_equity: pd.DataFrame):
    """
    Plots the equity curve from the 'df_equity' DataFrame, which is
    expected to have 'timestamp' and 'equity' columns.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df_equity["timestamp"], df_equity["equity"], label="Equity")
    plt.title("Paper Trading Equity Curve")
    plt.xlabel("Time")
    plt.ylabel("Equity (USD)")
    plt.legend()
    plt.grid(True)
    plt.show()

def main():
    # 1. Load all trade logs
    df_trades = load_all_trade_logs("data/trade_logs")
    if df_trades.empty:
        print("No trades found. Exiting.")
        return
    
    # 2. Calculate metrics
    metrics = calculate_performance_metrics(df_trades, starting_capital=10000.0)
    
    # 3. Print summary
    print("=== Paper Trading Summary ===")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Profitable Trades: {metrics['profitable_trades']} ({metrics['percent_profitable']:.2f}%)")
    print(f"Net PnL: ${metrics['net_pnl']:.2f}")
    if metrics['max_drawdown_pct'] is not None:
        print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2%}")
    else:
        print("Max Drawdown: N/A (No 'profit_loss' data)")
    
    # 4. Optional: Plot the equity curve if available
    if metrics["df_equity"] is not None:
        plot_equity_curve(metrics["df_equity"])

if __name__ == "__main__":
    main()
