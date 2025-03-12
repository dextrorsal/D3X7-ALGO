from setuptools import setup, find_packages

setup(
    name="crypto-data-fetcher",
    version="0.1.0",
    description="Ultimate Crypto Data Fetcher - Tool for fetching and storing cryptocurrency market data",
    author="Crypto Trader",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "asyncio",
        "pandas",
        "python-dotenv",
        "aiofiles",
    ],
    extras_require={
        "tensorflow": ["tensorflow>=2.6.0", "tensorflow-io>=0.21.0"],
        "pytorch": ["torch>=1.9.0", "torchvision>=0.10.0"],
        "solana": ["solana-py>=0.29.0", "anchorpy>=0.14.0"],
        "drift": ["driftpy>=0.5.0; python_version >= '3.10'"],
        "all": [
            "tensorflow>=2.6.0", 
            "tensorflow-io>=0.21.0",
            "torch>=1.9.0", 
            "torchvision>=0.10.0",
            "solana-py>=0.29.0", 
            "anchorpy>=0.14.0",
            "driftpy>=0.5.0; python_version >= '3.10'"
        ]
    },
    # Commenting out entry_points until we resolve module structure
    # entry_points={
    #     "console_scripts": [
    #         "crypto-fetch=src.crypto_cli:cli_entry",
    #     ],
    # },
    python_requires=">=3.8",
)