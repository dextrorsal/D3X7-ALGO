"""
Standalone test runner for Drift functionality.
This can be run directly without pytest to verify core functionality.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchanges.drift import DriftHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_tests():
    """Run the Drift self-test."""
    print("Running Drift self-test...")
    success = await DriftHandler.self_test()
    if success:
        print("✅ Drift test passed successfully!")
        return 0
    else:
        print("❌ Drift test failed!")
        return 1

if __name__ == "__main__":
    print("Starting Drift functionality test...")
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code) 