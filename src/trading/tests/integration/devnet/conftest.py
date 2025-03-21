#!/usr/bin/env python3
"""Configuration for devnet integration tests."""
import os
import logging
import pytest
from typing import Dict, List, Any
import asyncio
from dotenv import load_dotenv

from src.trading.drift.drift_adapter import DriftAdapter
from src.trading.tests.utils.drift_tools import DriftTools

load_dotenv()

logger = logging.getLogger(__name__)

# Use pytest-asyncio's auto mode instead of a custom event loop fixture
# This avoids the "event_loop fixture is deprecated" warnings
pytestmark = pytest.mark.asyncio

@pytest.fixture
async def drift_adapter():
    """Initialize DriftAdapter for testing."""
    adapter = None
    try:
        # Check if MAIN_KEY_PATH environment variable is set
        keypair_path = os.environ.get("MAIN_KEY_PATH")
        
        # Initialize adapter
        adapter = DriftAdapter(network="devnet", keypair_path=keypair_path)
        await adapter.connect()
        
        # Yield the adapter
        yield adapter
    finally:
        # Clean up resources
        if adapter and adapter.client:
            logger.info("Cleaning up adapter resources...")
            try:
                await adapter.client.unsubscribe()
                logger.info("Unsubscribed adapter client")
            except Exception as e:
                logger.error(f"Error unsubscribing adapter client: {e}")
                
        if adapter and adapter.connection:
            try:
                await adapter.connection.close()
                logger.info("Closed adapter connection")
            except Exception as e:
                logger.error(f"Error closing adapter connection: {e}")

@pytest.fixture
async def drift_tools(drift_adapter):
    """Initialize DriftTools for testing."""
    tools = None
    try:
        # Init DriftTools with adapter
        tools = DriftTools(rpc_url_or_adapter=drift_adapter)
        
        # Ensure connected
        await tools.connect()
        
        # Yield the tools
        yield tools
    finally:
        # Clean up resources if the tools have a separate client from the adapter
        if tools and tools.client and tools.client != drift_adapter.client:
            logger.info("Cleaning up tools resources...")
            try:
                await tools.client.unsubscribe()
                logger.info("Unsubscribed tools client")
            except Exception as e:
                logger.error(f"Error unsubscribing tools client: {e}")

# Any devnet-specific test fixtures can be added here