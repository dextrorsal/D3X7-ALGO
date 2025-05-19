#!/usr/bin/env python3
"""
Simple script to test UltimateDataFetcher initialization without using pytest
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

from src.core.config import Config
from src.core.models import TimeRange
from src.ultimate_fetcher import UltimateDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Testing UltimateDataFetcher initialization")
    
    try:
        # Initialize config from .env
        config = Config()
        logger.info("Config initialized")
        
        # Print available exchanges
        if hasattr(config, 'exchanges'):
            logger.info("Available exchanges:")
            for exchange_name, exchange_config in config.exchanges.items():
                enabled = "enabled" if exchange_config.enabled else "disabled"
                logger.info(f"  - {exchange_name} ({enabled})")
        else:
            logger.error("No exchanges configured in config")
        
        # Initialize fetcher but don't start it yet
        fetcher = UltimateDataFetcher(config)
        logger.info("UltimateDataFetcher initialized")
        
        # Start the fetcher - this initializes connections
        logger.info("Starting UltimateDataFetcher")
        await fetcher.start()
        logger.info("UltimateDataFetcher started")
        
        # Print exchange handlers
        logger.info("Initialized exchange handlers:")
        for name in fetcher.exchange_handlers:
            logger.info(f"  - {name}")
            
        # Stop the fetcher
        logger.info("Stopping UltimateDataFetcher")
        await fetcher.stop()
        logger.info("UltimateDataFetcher stopped successfully")
        
    except Exception as e:
        logger.error(f"Error testing UltimateDataFetcher: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 