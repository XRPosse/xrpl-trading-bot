#!/usr/bin/env python3
"""
Script to collect historical DEX and AMM data from XRPL
"""

import asyncio
import argparse
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings
from src.data.xrpl_dex_fetcher import XRPLDexDataFetcher
from src.data.amm_fetcher import AMMDataFetcher
from src.utils.logger import setup_logger
from loguru import logger


async def collect_dex_data(days: int = 180):
    """Collect historical DEX trading data"""
    settings = get_settings()
    fetcher = XRPLDexDataFetcher(settings)
    
    try:
        await fetcher.connect()
        
        # Discover all active pairs
        logger.info("Discovering active trading pairs...")
        pairs = await fetcher.discover_active_pairs()
        logger.info(f"Found {len(pairs)} active pairs")
        
        # Log pairs we'll fetch
        for pair in pairs:
            logger.info(f"  - {pair['symbol']}: {pair['type']}")
        
        # Fetch historical data for all pairs
        logger.info(f"Fetching {days} days of historical data...")
        all_data = await fetcher.fetch_all_pairs_data(days=days, pairs=pairs)
        
        # Save the data
        if all_data:
            await fetcher.save_historical_data(all_data)
            
            # Create ML dataset
            logger.info("Creating ML dataset...")
            ml_dataset = await fetcher.create_ml_dataset(all_data)
            
            if not ml_dataset.empty:
                ml_dataset.to_csv("data/xrpl_dex/ml_dataset.csv", index=False)
                ml_dataset.to_parquet("data/xrpl_dex/ml_dataset.parquet", index=False)
                logger.info(f"Saved ML dataset with {len(ml_dataset)} records")
        
        await fetcher.disconnect()
        
    except Exception as e:
        logger.error(f"Error collecting DEX data: {e}")
        raise


async def collect_amm_data(hours: int = 24, interval_minutes: int = 5):
    """Collect AMM pool data"""
    settings = get_settings()
    fetcher = AMMDataFetcher(settings)
    
    try:
        await fetcher.connect()
        
        # Get current state of all AMM pools
        logger.info("Fetching current AMM pool states...")
        
        for token_name, token_info in fetcher.tokens.items():
            logger.info(f"\n{token_name} AMM Pool:")
            
            # Get pool info
            amm_info = await fetcher.get_amm_info(token_info["amm_address"])
            logger.info(f"  AMM Address: {token_info['amm_address']}")
            
            # Get pool metrics
            metrics = await fetcher.calculate_pool_metrics(token_info["amm_address"])
            if metrics:
                logger.info(f"  Price: {metrics['price']:.6f} XRP per {token_name}")
                logger.info(f"  XRP Reserve: {metrics['xrp_reserve']:,.2f}")
                logger.info(f"  Token Reserve: {metrics['token_reserve']:,.2f}")
                logger.info(f"  TVL: {metrics['tvl_xrp']:,.2f} XRP")
        
        # Monitor pools for specified duration
        if hours > 0:
            logger.info(f"\nMonitoring AMM pools for {hours} hours...")
            interval_seconds = interval_minutes * 60
            amm_data = await fetcher.monitor_amm_pools(
                interval_seconds=interval_seconds,
                duration_hours=hours
            )
            
            # Export the data
            if amm_data:
                await fetcher.export_amm_data(amm_data)
        
        await fetcher.disconnect()
        
    except Exception as e:
        logger.error(f"Error collecting AMM data: {e}")
        raise


async def collect_all_data(dex_days: int = 180, amm_hours: int = 0):
    """Collect both DEX and AMM data"""
    logger.info("=== XRPL Data Collection Starting ===")
    
    # Note: XRPL doesn't provide extensive historical data through standard APIs
    # For production use, consider:
    # 1. Running your own full-history XRPL node
    # 2. Using third-party data services (Bithomp, XRPScan, etc.)
    # 3. Collecting data over time through continuous monitoring
    
    logger.warning(
        "Note: XRPL doesn't provide extensive historical DEX data through standard APIs. "
        "This script will collect available data and set up monitoring."
    )
    
    # Collect current AMM data
    logger.info("\n--- Collecting AMM Data ---")
    await collect_amm_data(hours=amm_hours)
    
    # Set up DEX monitoring (limited historical data available)
    logger.info("\n--- Setting up DEX Monitoring ---")
    # await collect_dex_data(days=dex_days)
    
    logger.info("\n=== Data Collection Complete ===")


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical XRPL DEX and AMM data"
    )
    
    parser.add_argument(
        "--dex-days",
        type=int,
        default=180,
        help="Days of DEX data to collect (default: 180)"
    )
    
    parser.add_argument(
        "--amm-hours",
        type=int,
        default=0,
        help="Hours to monitor AMM pools (default: 0 - snapshot only)"
    )
    
    parser.add_argument(
        "--amm-interval",
        type=int,
        default=5,
        help="AMM monitoring interval in minutes (default: 5)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["all", "dex", "amm"],
        default="all",
        help="Data collection mode"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger()
    
    # Run collection
    if args.mode == "dex":
        asyncio.run(collect_dex_data(days=args.dex_days))
    elif args.mode == "amm":
        asyncio.run(collect_amm_data(
            hours=args.amm_hours,
            interval_minutes=args.amm_interval
        ))
    else:
        asyncio.run(collect_all_data(
            dex_days=args.dex_days,
            amm_hours=args.amm_hours
        ))


if __name__ == "__main__":
    main()