"""
Test script for Coinbase data fetching functionality.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.logging import RichHandler

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.core.models import TimeRange
from src.exchanges.base import ExchangeConfig
from src.exchanges.coinbase.coinbase import CoinbaseHandler
from src.utils.indicators.rsi import RSI

# Set up rich console
console = Console()

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)

async def main():
    """Run Coinbase data fetching and indicator tests."""
    
    # Print header
    console.print("\n[bold cyan]🚀 Coinbase Data Fetching Test[/bold cyan]", justify="center")
    console.print("[dim]" + "="*50 + "[/dim]\n")

    try:
        # Initialize exchange handler
        config = ExchangeConfig(
            name="coinbase",
            credentials={},  # No credentials needed for public data
            rate_limit=3,  # 3 requests per second for public endpoints
            markets=["BTC-USD", "ETH-USD"],  # Example markets
            base_url="https://api.exchange.coinbase.com"
        )
        
        handler = CoinbaseHandler(config)
        await handler.start()
        
        console.print("[green]✓[/green] Connected to Coinbase\n")

        # Set up time range for historical data
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=5)
        time_range = TimeRange(start=start_time, end=end_time)

        # Fetch historical data
        market = "BTC-USD"
        resolution = "60"  # 1-hour candles
        
        with console.status("[bold yellow]Fetching historical data...[/bold yellow]"):
            candles = await handler.fetch_historical_candles(market, time_range, resolution)
        
        console.print(f"[green]✓[/green] Successfully fetched [bold]{len(candles)}[/bold] candles\n")

        # Display sample data
        if candles:
            sample_candle = candles[0]
            
            # Create a table for the sample candle
            table = Table(
                title=f"[bold]Sample Candle Data[/bold] ({sample_candle.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC)",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            
            table.add_column("Metric", style="dim")
            table.add_column("Value", justify="right")
            
            table.add_row("Open", f"${sample_candle.open:,.2f}")
            table.add_row("High", f"${sample_candle.high:,.2f}")
            table.add_row("Low", f"${sample_candle.low:,.2f}")
            table.add_row("Close", f"${sample_candle.close:,.2f}")
            table.add_row("Volume", f"{sample_candle.volume:,.8f} BTC")
            
            console.print(table)
            console.print()

            # Calculate and display RSI signals
            rsi = RSI(period=14, overbought=70, oversold=30)
            signals = []
            
            for candle in candles:
                rsi_value = rsi.update(candle.close)
                if rsi_value is not None:
                    if rsi_value < 30:
                        signals.append('buy')
                    elif rsi_value > 70:
                        signals.append('sell')
                    else:
                        signals.append('neutral')

            # Create RSI analysis table
            if signals:  # Only create table if we have signals
                rsi_table = Table(
                    title="[bold]RSI Signal Analysis[/bold]",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold magenta"
                )
                
                rsi_table.add_column("Signal Type", style="dim")
                rsi_table.add_column("Count", justify="right")
                rsi_table.add_column("Percentage", justify="right")
                
                buy_count = signals.count('buy')
                sell_count = signals.count('sell')
                neutral_count = signals.count('neutral')
                total_signals = len(signals)
                
                if total_signals > 0:  # Avoid division by zero
                    rsi_table.add_row(
                        "🟢 Buy (RSI < 30)", 
                        str(buy_count),
                        f"{(buy_count/total_signals)*100:.1f}%"
                    )
                    rsi_table.add_row(
                        "🔴 Sell (RSI > 70)", 
                        str(sell_count),
                        f"{(sell_count/total_signals)*100:.1f}%"
                    )
                    rsi_table.add_row(
                        "⚪ Neutral", 
                        str(neutral_count),
                        f"{(neutral_count/total_signals)*100:.1f}%"
                    )
                    
                    console.print(rsi_table)
                    console.print()

        # Clean up
        await handler.stop()
        console.print("[green]✓[/green] Test completed successfully!\n")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {str(e)}", style="bold red")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 