#!/usr/bin/env python3
"""
Wrapper script for Drift CLI.
Makes it easier to run the drift management CLI from the root directory.
"""

from src.trading.drift.management.drift_cli import main

if __name__ == "__main__":
    main() 