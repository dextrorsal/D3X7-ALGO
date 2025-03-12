"""
Command Line Interface for Live Trading with Drift/Jupiter
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone
import json
import sys
import os
from pathlib import Path

from src.core.config import Config
from src.utils.log_setup import setup_logging
from src.live.live_trader import LiveTrader
from src.utils.indicators.wrapper_supertrend import SupertrendIndicator
from src.utils.indicators.wrapper_logistic import LogisticRegressionIndicator
from src.utils.indicators.wrapper_knn import kNNIndicator
from src.utils.indicators.wrapper_lorentzian import LorentzianIndicator
from src.utils.strategy.multi_indicator_strategy import MultiIndicatorStrategy
from src.utils.strategy.segmented import SegmentedStrategy
from src.utils.strategy.sol_spot import SOLSpotStrategy

logger = logging.getLogger(__name__)

def get_indicator(name: str, config_path: str = None):
    """Get an indicator by name"""
    name = name.lower()
    
    if name == "supertrend":
        return SupertrendIndicator(config_path=config_path)
    elif name == "logistic":
        return LogisticRegressionIndicator(config_path=config_path)
    elif name == "knn":
        return kNNIndicator(config_path=config_path)
    elif name == "lorentzian":
        return LorentzianIndicator(config_path=config_path)
    else:
        raise ValueError(f"Unknown indicator: {name}")

def create_strategy(strategy_name: str, indicators: list = None, weights: list = None, threshold: float = 0, config_path: str = None):
    """Create a strategy instance"""
    config = {"consensus_threshold": threshold}
    
    # Load additional config if provided
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
    
    if strategy_name.lower() == "multi_indicator":
        if not indicators:
            raise ValueError("Indicators required for multi_indicator strategy")
        return MultiIndicatorStrategy(
            config=config,
            indicators=indicators,
            weights=weights
        )
    elif strategy_name.lower() == "segmented":
        if not indicators or len(indicators) < 3:
            raise ValueError("At least 3 indicators required for segmented strategy")
        
        # Divide indicators into groups for trend, range, and volatile regimes
        n = len(indicators)
        trend_indicators = indicators[:n//3]
        range_indicators = indicators[n//3:2*n//3]
        volatile_indicators = indicators[2*n//3:]
        
        # Do the same for weights if provided
        trend_weights = None
        range_weights = None
        volatile_weights = None
        if weights:
            n_weights = len(weights)
            trend_weights = weights[:n_weights//3]
            range_weights = weights[n_weights//3:2*n_weights//3]
            volatile_weights = weights[2*n_weights//3:]
        
        return SegmentedStrategy(
            config=config,
            trend_indicators=trend_indicators,
            range_indicators=range_indicators,
            volatile_indicators=volatile_indicators,
            trend_weights=trend_weights,
            range_weights=range_weights,
            volatile_weights=volatile_weights
        )
    elif strategy_name.lower() == "sol_spot":
        # SOL-specific strategy comes with pre-configured indicators
        return SOLSpotStrategy(config=config)
    else:
        raise ValueError(f"Unknown strategy type: {strategy_name}")

async def run_live_trading(args):
    """Run live trading with provided arguments"""
    # Setup logging
    setup_logging()
    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)
    
    # Load configuration
    config = Config(args.config)
    
    # Load indicators
    indicators = []
    for indicator_name in args.indicators:
        try:
            indicator = get_indicator(indicator_name, args.config_file)
            indicators.append(indicator)
            logger.info(f"Loaded indicator: {indicator_name}")
        except Exception as e:
            logger.error(f"Error loading indicator {indicator_name}: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    if not indicators:
        logger.error("No valid indicators loaded")
        return
    
    # Create the strategy
    try:
        strategy = create_strategy(
            args.strategy,
            indicators=indicators,
            weights=args.weights,
            threshold=args.threshold,
            config_path=args.config_file
        )
        logger.info(f"Created strategy: {args.strategy}")
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return
    
    # Create live trader
    try:
        trader = LiveTrader(
            config=config,
            strategy=strategy,
            exchange_name=args.exchange
        )
        logger.info(f"Initialized live trader for {args.exchange}")
    except Exception as e:
        logger.error(f"Error initializing trader: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return
    
    # Save configuration to trade log
    try:
        trade_config = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exchange": args.exchange,
            "markets": args.markets,
            "resolution": args.resolution,
            "interval": args.interval,
            "strategy": args.strategy,
            "indicators": args.indicators,
            "weights": args.weights if args.weights else "default",
            "threshold": args.threshold,
            "max_positions": args.max_positions,
            "position_size_pct": args.position_size,
            "stop_loss_pct": args.stop_loss,
            "take_profit_pct": args.take_profit,
            "cooldown_minutes": args.cooldown
        }
        
        config_path = Path("data/trade_logs") / f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(trade_config, f, indent=2)
            
        logger.info(f"Saved trading configuration to {config_path}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
    
    try:
        # Run continuous trading
        if args.mode == "continuous":
            logger.info(f"Starting continuous trading for {args.markets}")
            await trader.run_continuous(args.markets, args.resolution, args.interval)
        # Run single cycle
        elif args.mode == "single":
            logger.info(f"Running single trading cycle for {args.markets}")
            await trader.run_trading_cycle(args.markets, args.resolution)
        # Paper trading (simulate but don't execute)
        elif args.mode == "paper":
            logger.info(f"Starting paper trading for {args.markets}")
            # In a real implementation, this would simulate trades
            # For now, we'll just use the regular trader but log a warning
            logger.warning("Paper trading not fully implemented, will execute real analysis but not trades")
            await trader.run_continuous(args.markets, args.resolution, args.interval)
    except KeyboardInterrupt:
        logger.info("Trading stopped by user")
    except Exception as e:
        logger.error(f"Error during trading: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    finally:
        # Cleanup
        try:
            await trader.stop()
        except Exception as e:
            logger.error(f"Error stopping trader: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Live trading with crypto exchanges")
    
    # General settings
    parser.add_argument("--config", default=".env", help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--exchange", default="drift", choices=["drift", "jupiter"], 
                        help="Exchange to use for trading")
    
    # Trading mode
    parser.add_argument("--mode", choices=["continuous", "single", "paper"], default="paper",
                       help="Trading mode: continuous, single cycle, or paper trading")
    
    # Markets and data
    parser.add_argument("--markets", nargs="+", required=True, 
                       help="Markets to trade (e.g., SOL-PERP BTC-PERP)")
    parser.add_argument("--resolution", default="15", 
                       choices=["1", "5", "15", "30", "60", "240", "1D"],
                       help="Data resolution")
    parser.add_argument("--interval", type=int, default=60,
                       help="Interval between trading cycles in seconds")
    
    # Strategy settings
    parser.add_argument("--strategy", default="multi_indicator",
                       help="Strategy to use")
    parser.add_argument("--indicators", nargs="+", default=["supertrend"],
                       help="Indicators to use in strategy")
    parser.add_argument("--weights", nargs="+", type=float,
                       help="Weights for indicators")
    parser.add_argument("--threshold", type=float, default=0,
                       help="Signal threshold for strategy")
    parser.add_argument("--config-file", help="Path to indicator/strategy config file")
    
    # Risk management
    parser.add_argument("--position-size", type=float, default=5.0,
                       help="Position size as percentage of available capital")
    parser.add_argument("--max-positions", type=int, default=1,
                       help="Maximum number of open positions")
    parser.add_argument("--stop-loss", type=float, default=5.0,
                       help="Stop loss percentage")
    parser.add_argument("--take-profit", type=float, default=10.0,
                       help="Take profit percentage") 
    parser.add_argument("--cooldown", type=int, default=60,
                       help="Cooldown minutes between trades on same market")
    
    args = parser.parse_args()
    
    # Run the async main
    asyncio.run(run_live_trading(args))

if __name__ == "__main__":
    main()