#!/usr/bin/env python3
"""
Root-level pytest configuration.
"""

import pytest

# Configure pytest-asyncio plugin
pytest_plugins = ["pytest_asyncio"]

# Configure pytest-asyncio to use module scope for the asyncio mark
def pytest_configure(config):
    """Configure pytest-asyncio to use module scope."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as using asyncio"
    )