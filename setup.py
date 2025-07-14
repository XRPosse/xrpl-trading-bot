#!/usr/bin/env python3
"""
Setup script for XRPL Trading Bot
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="xrpl-trading-bot",
    version="0.1.0",
    author="XRPL Trading Bot Contributors",
    author_email="",
    description="An advanced automated trading bot for the XRP Ledger",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/xrpl-trading-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "xrpl-bot=main:main",
            "xrpl-backtest=backtest:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/xrpl-trading-bot/issues",
        "Source": "https://github.com/yourusername/xrpl-trading-bot",
        "Documentation": "https://github.com/yourusername/xrpl-trading-bot/tree/main/docs",
    },
)