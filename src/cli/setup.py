#!/usr/bin/env python3
"""
D3X7-ALGO CLI Setup Script
"""

from setuptools import setup, find_packages

setup(
    name="d3x7-cli",
    version="0.1.0",
    description="D3X7-ALGO Trading Platform CLI",
    author="D3X7 Team",
    packages=find_packages(),
    install_requires=[
        "asyncio>=3.4.3",
        "aiohttp>=3.8.0",
        "python-dotenv>=0.19.0",
        "solana>=0.30.0",
        "anchorpy>=0.17.0",
        "driftpy>=0.4.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "d3x7=src.cli.main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
) 