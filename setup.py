from setuptools import setup, find_packages

setup(
    name="d3x7-algo",
    version="0.1.0",
    description="D3X7-ALGO Trading Platform - Advanced crypto trading and data analysis tools",
    author="D3X7 Team",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "asyncio>=3.4.3",
        "pandas>=1.3.0",
        "python-dotenv>=0.19.0",
        "aiofiles>=0.8.0",
        "rich>=10.0.0",
        "click>=8.0.0",
        "solders>=0.9.0",
        "anchorpy>=0.14.0",
        "driftpy>=0.5.0",
    ],
    extras_require={
        "tensorflow": ["tensorflow>=2.6.0", "tensorflow-io>=0.21.0"],
        "pytorch": ["torch>=1.9.0", "torchvision>=0.10.0"],
        "gui": ["PyQt6>=6.0.0"],
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.0.0",
            "isort>=5.0.0",
            "mypy>=0.900"
        ],
        "all": [
            "tensorflow>=2.6.0", 
            "tensorflow-io>=0.21.0",
            "torch>=1.9.0", 
            "torchvision>=0.10.0",
            "PyQt6>=6.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "d3x7=src.cli.main:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)