#!/usr/bin/env python3
"""
Simple test script for DevnetCLI functionality.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.cli.trading.devnet import DevnetCLI
from src.core.config import Config

async def main():
    """Test the DevnetCLI functionality."""
    config = Config()
    devnet_cli = DevnetCLI(config)
    
    # Create a parser for testing
    parser = argparse.ArgumentParser(description='DevnetCLI Test')
    subparsers = parser.add_subparsers(dest='command')
    
    # Add DevnetCLI arguments
    devnet_cli.add_arguments(subparsers)
    
    # Parse command line arguments
    args = parser.parse_args()
    
    if not args.command or args.command != 'devnet':
        parser.print_help()
        return
    
    try:
        await devnet_cli.start()
        await devnet_cli.handle_command(args)
    finally:
        await devnet_cli.stop()

if __name__ == "__main__":
    asyncio.run(main()) 