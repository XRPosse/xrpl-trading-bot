"""
Script to collect historical AMM and DEX data
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from src.database.storage import DataStorage
from src.data.historical_collector import HistoricalDataCollector
from src.data.dex_fetcher import DEXDataFetcher
from src.data.amm_fetcher import AMMDataFetcher


async def load_tokens():
    """Load token configuration"""
    tokens_file = Path("src/config/tokens.json")
    with open(tokens_file) as f:
        return json.load(f)


async def collect_lp_token_info(storage: DataStorage, tokens: dict):
    """Collect and store LP token information"""
    logger.info("Collecting LP token information...")
    
    for token_name, token_info in tokens.items():
        amm_address = token_info.get("amm_address")
        if not amm_address:
            continue
            
        # Store the base token asset
        await storage.store_asset({
            "currency_code": token_info["token_code"],
            "issuer": token_info["token_address"],
            "name": token_name,
            "symbol": token_name,
            "amm_address": amm_address,
            "asset_type": "token"
        })
        
        # Store XRP asset if not already stored
        await storage.store_asset({
            "currency_code": "XRP",
            "issuer": None,
            "name": "XRP",
            "symbol": "XRP",
            "asset_type": "token"
        })
        
        # Store LP token asset
        lp_token_code = token_info.get("amm_code")
        if lp_token_code:
            await storage.store_asset({
                "currency_code": lp_token_code,
                "issuer": amm_address,
                "name": f"{token_name}/XRP LP Token",
                "symbol": f"{token_name}-XRP-LP",
                "amm_address": amm_address,
                "asset_type": "lp_token",
                "pool_asset1_id": 2,  # XRP (assuming it's ID 2)
                "pool_asset2_id": None  # Will be updated later
            })
            
    logger.info("LP token information stored")


async def collect_historical_amm_data(
    storage: DataStorage,
    tokens: dict,
    start_date: datetime,
    end_date: datetime
):
    """Collect historical AMM snapshots"""
    collector = HistoricalDataCollector(storage)
    
    try:
        await collector.connect()
        
        # Get AMM addresses
        amm_addresses = [
            token_info["amm_address"] 
            for token_info in tokens.values() 
            if token_info.get("amm_address")
        ]
        
        logger.info(f"Collecting AMM snapshots for {len(amm_addresses)} pools")
        
        # Collect snapshots every 4 hours
        snapshot_count = await collector.collect_amm_snapshots(
            amm_addresses=amm_addresses,
            start_date=start_date,
            end_date=end_date,
            interval_hours=4
        )
        
        logger.info(f"Collected {snapshot_count} AMM snapshots")
        
    finally:
        await collector.disconnect()


async def collect_historical_dex_data(
    storage: DataStorage,
    tokens: dict,
    start_date: datetime,
    end_date: datetime
):
    """Collect historical DEX trades"""
    fetcher = DEXDataFetcher(storage)
    
    try:
        await fetcher.connect()
        
        # Get unique token issuers (accounts to monitor)
        accounts = list(set(
            token_info["token_address"] 
            for token_info in tokens.values()
        ))
        
        # Add some major XRPL DEX traders/market makers
        accounts.extend([
            "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY",  # Popular DEX trader
            "rKiCet8SdvWxPXnAgYarFUXMh1zCPz432Y",  # Another active trader
            "r9cZA1mLK5R5Am25ArfXFmqgNwjZgnfk59"   # Gateway account
        ])
        
        logger.info(f"Collecting DEX trades for {len(accounts)} accounts")
        
        # Collect trades
        trade_count = await fetcher.collect_historical_trades(
            accounts=accounts,
            start_date=start_date,
            end_date=end_date,
            batch_size=1000
        )
        
        logger.info(f"Collected {trade_count} DEX trades")
        
    finally:
        await fetcher.disconnect()


async def collect_transaction_metadata(
    storage: DataStorage,
    tokens: dict,
    start_date: datetime,
    end_date: datetime
):
    """Collect and process transaction metadata"""
    collector = HistoricalDataCollector(storage)
    
    try:
        await collector.connect()
        
        # Collect from AMM addresses
        amm_addresses = [
            token_info["amm_address"] 
            for token_info in tokens.values() 
            if token_info.get("amm_address")
        ]
        
        logger.info(f"Processing transaction metadata for {len(amm_addresses)} AMM pools")
        
        # Collect AMM transactions
        tx_count = await collector.collect_historical_transactions(
            accounts=amm_addresses,
            start_date=start_date,
            end_date=end_date,
            tx_types=["AMMDeposit", "AMMWithdraw", "AMMCreate"]
        )
        
        logger.info(f"Processed {tx_count} AMM transactions")
        
        # Also collect Payment and OfferCreate transactions for token issuers
        token_issuers = list(set(
            token_info["token_address"] 
            for token_info in tokens.values()
        ))
        
        tx_count = await collector.collect_historical_transactions(
            accounts=token_issuers,
            start_date=start_date,
            end_date=end_date,
            tx_types=["Payment", "OfferCreate"]
        )
        
        logger.info(f"Processed {tx_count} token transactions")
        
    finally:
        await collector.disconnect()


async def main():
    """Main collection process"""
    # Initialize storage
    storage = DataStorage()
    
    # Load tokens
    tokens = await load_tokens()
    
    # Set date range (6 months of data)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=180)
    
    logger.info(f"Collecting data from {start_date} to {end_date}")
    
    # Step 1: Store LP token information
    await collect_lp_token_info(storage, tokens)
    
    # Step 2: Collect historical AMM snapshots
    await collect_historical_amm_data(storage, tokens, start_date, end_date)
    
    # Step 3: Collect DEX trades
    await collect_historical_dex_data(storage, tokens, start_date, end_date)
    
    # Step 4: Process transaction metadata
    await collect_transaction_metadata(storage, tokens, start_date, end_date)
    
    logger.info("Historical data collection complete!")
    
    # Show summary
    logger.info("\n=== Data Collection Summary ===")
    
    # Get some stats
    amm_addresses = [t["amm_address"] for t in tokens.values() if t.get("amm_address")]
    
    for amm_address in amm_addresses[:3]:  # Show first 3 AMMs
        snapshots = await storage.get_amm_snapshots(
            amm_address=amm_address,
            start_date=start_date,
            limit=10
        )
        
        if snapshots:
            logger.info(f"\nAMM {amm_address}:")
            logger.info(f"  Snapshots: {len(snapshots)}")
            logger.info(f"  Latest TVL: {snapshots[-1]['tvl_xrp']:.2f} XRP")
            logger.info(f"  Latest Price: {snapshots[-1]['price_asset2_per_asset1']:.6f}")
    
    # Show DEX trades
    trades = await storage.get_dex_trades(limit=10)
    logger.info(f"\nTotal DEX trades collected: {len(trades)}")
    
    if trades:
        logger.info("Sample trades:")
        for trade in trades[:3]:
            logger.info(f"  {trade['timestamp']}: {trade['gets_amount']:.2f} {trade['gets_currency']} <-> {trade['pays_amount']:.2f} {trade['pays_currency']}")


if __name__ == "__main__":
    asyncio.run(main())