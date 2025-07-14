#!/usr/bin/env python3
"""
Quick test script to verify AMM data collection works
"""

import asyncio
from src.config.settings import get_settings
from src.data.amm_fetcher import AMMDataFetcher
from src.utils.logger import setup_logger
from loguru import logger


async def test_amm_connection():
    """Test AMM data fetching"""
    settings = get_settings()
    setup_logger()
    
    fetcher = AMMDataFetcher(settings)
    
    try:
        logger.info("Connecting to XRPL...")
        await fetcher.connect()
        
        # Test with one token
        test_token = "POSSE"  # Using POSSE as example
        
        if test_token in fetcher.tokens:
            token_info = fetcher.tokens[test_token]
            logger.info(f"\nTesting {test_token} AMM:")
            logger.info(f"Token Address: {token_info['token_address']}")
            logger.info(f"AMM Address: {token_info['amm_address']}")
            
            # Get pool metrics
            metrics = await fetcher.calculate_pool_metrics(token_info['amm_address'])
            
            if metrics:
                logger.info(f"\nPool Metrics:")
                logger.info(f"XRP Reserve: {metrics['xrp_reserve']:,.2f}")
                logger.info(f"Token Reserve: {metrics['token_reserve']:,.2f}")
                logger.info(f"Price: {metrics['price']:.8f} XRP per {test_token}")
                logger.info(f"TVL: {metrics['tvl_xrp']:,.2f} XRP")
            else:
                logger.warning("No metrics returned")
        
        await fetcher.disconnect()
        logger.info("\nTest completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_amm_connection())