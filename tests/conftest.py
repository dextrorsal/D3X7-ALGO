#!/usr/bin/env python3
"""
Root-level pytest configuration for D3X7-ALGO.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure pytest-asyncio plugin
pytest_plugins = ["pytest_asyncio"]

# Configure pytest-asyncio to use module scope for the asyncio mark
def pytest_configure(config):
    """Configure pytest-asyncio to use module scope."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as using asyncio"
    ) 