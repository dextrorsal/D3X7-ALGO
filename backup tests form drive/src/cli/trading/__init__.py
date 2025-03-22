"""
Trading CLI Package

Provides CLI components for trading operations:
- Drift trading (perpetual futures)
- Jupiter trading (token swaps)
"""

from .drift import DriftCLI
from .jupiter import JupiterCLI

__all__ = ['DriftCLI', 'JupiterCLI'] 