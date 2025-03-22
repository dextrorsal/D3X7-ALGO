"""
Base exchange handler providing common functionality for all exchanges.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Dict, Optional, Union
import aiohttp
import asyncio

from core.models import StandardizedCandle, ExchangeCredentials, TimeRange
from core.exceptions import ValidationError, ExchangeError, RateLimitError, ApiError
from core.config import ExchangeConfig

# ... existing code ... 