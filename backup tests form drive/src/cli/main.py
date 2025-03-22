#!/usr/bin/env python3
"""
D3X7-ALGO CLI - Main entry point for all platform operations.
"""

import asyncio
import logging
import argparse
from typing import Optional

from .trading.jupiter import JupiterCLI
from .trading.drift import DriftCLI
from .wallet.wallet_commands import WalletCLI
from ..core.config import Config

logger = logging.getLogger(__name__)

class D3X7CLI:
    """Main CLI orchestrator for D3X7-ALGO platform."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the CLI components."""
        self.config = config or Config()
        self.jupiter_cli = JupiterCLI(self.config)
        self.drift_cli = DriftCLI(self.config)
        self.wallet_cli = WalletCLI(self.config)

    async def start(self):
        """Initialize all CLI components."""
        await asyncio.gather(
            self.jupiter_cli.start(),
            self.drift_cli.start(),
            self.wallet_cli.start()
        )

    async def stop(self):
        """Cleanup all CLI components."""
        await asyncio.gather(
            self.jupiter_cli.stop(),
            self.drift_cli.stop(),
            self.wallet_cli.stop()
        )

    def create_parser(self):
        """Create argument parser for all CLI commands."""
        parser = argparse.ArgumentParser(description='D3X7-ALGO Trading Platform CLI')
        subparsers = parser.add_subparsers(dest='command')

        # Add component-specific arguments
        self.jupiter_cli.add_arguments(subparsers)
        self.drift_cli.add_arguments(subparsers)
        self.wallet_cli.add_arguments(subparsers)

        return parser

    async def handle_command(self, args):
        """Route commands to appropriate handlers."""
        try:
            if args.command == 'jupiter':
                await self.jupiter_cli.handle_command(args)
            elif args.command == 'drift':
                await self.drift_cli.handle_command(args)
            elif args.command == 'wallet':
                await self.wallet_cli.handle_command(args)
            else:
                logger.error("Unknown command")
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            raise

async def main():
    """Main entry point for the CLI."""
    cli = D3X7CLI()
    parser = cli.create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        await cli.start()
        await cli.handle_command(args)
    finally:
        await cli.stop()

if __name__ == "__main__":
    asyncio.run(main()) 