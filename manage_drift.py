#!/usr/bin/env python3
"""
Wrapper script for Drift Account Manager.
Makes it easier to run from the root directory.
"""

import asyncio
from src.trading.drift.account_manager import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise 