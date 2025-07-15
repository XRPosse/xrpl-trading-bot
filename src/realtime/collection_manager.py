"""
Collection manager - Coordinates real-time collection and backfill
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger

from ..database.storage import DataStorage
from ..data.full_history_collector import FullHistoryCollector
from .realtime_collector import RealtimeCollector


class CollectionManager:
    """Manages real-time collection with automatic backfill"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.realtime_collector = RealtimeCollector(storage)
        self.backfill_collector = FullHistoryCollector(storage, use_full_history=False)
        self.is_running = False
        self.backfill_task: Optional[asyncio.Task] = None
        self.realtime_task: Optional[asyncio.Task] = None
        
    async def check_collection_gaps(self, accounts: List[str]) -> Dict[str, Dict]:
        """Check for gaps in collected data"""
        gaps = {}
        
        try:
            await self.backfill_collector.connect()
            current_ledger = await self.realtime_collector.get_current_ledger()
            
            for account in accounts:
                # Get last collected data from database
                log = await self.storage.get_collection_log("realtime", account)
                
                if log:
                    last_ledger = log.get("last_processed_ledger", 0)
                    gap_size = current_ledger - last_ledger
                    
                    if gap_size > 100:  # More than ~6 minutes
                        gaps[account] = {
                            "last_ledger": last_ledger,
                            "current_ledger": current_ledger,
                            "gap_size": gap_size,
                            "estimated_time": gap_size * 4 / 60  # Minutes
                        }
                else:
                    # No previous collection, need full backfill
                    gaps[account] = {
                        "last_ledger": 0,
                        "current_ledger": current_ledger,
                        "gap_size": current_ledger,
                        "estimated_time": float('inf')
                    }
                    
        except Exception as e:
            logger.error(f"Error checking gaps: {e}")
        finally:
            await self.backfill_collector.disconnect()
            
        return gaps
        
    async def perform_backfill(self, accounts: List[str], max_days: int = 7):
        """Perform backfill for accounts with gaps"""
        logger.info(f"Starting backfill check for {len(accounts)} accounts")
        
        gaps = await self.check_collection_gaps(accounts)
        
        if not gaps:
            logger.info("No gaps found, all accounts up to date")
            return
            
        logger.warning(f"Found gaps in {len(gaps)} accounts")
        
        for account, gap_info in gaps.items():
            if gap_info["estimated_time"] == float('inf'):
                logger.info(f"Account {account} needs initial backfill (max {max_days} days)")
                days_to_collect = max_days
            else:
                logger.info(f"Account {account} is {gap_info['gap_size']} ledgers behind "
                          f"(~{gap_info['estimated_time']:.1f} minutes)")
                days_to_collect = min(max_days, gap_info['estimated_time'] / (60 * 24))
                
            try:
                await self.backfill_collector.connect()
                
                # Perform backfill
                stats = await self.backfill_collector.collect_amm_full_history(
                    amm_addresses=[account],
                    days_back=int(days_to_collect)
                )
                
                if stats['total_transactions'] > 0:
                    logger.success(f"Backfilled {stats['total_transactions']} transactions for {account}")
                    
                    # Update collection log
                    await self.storage.update_collection_progress(
                        "realtime",
                        account,
                        gap_info["current_ledger"],
                        stats['total_transactions']
                    )
                else:
                    logger.warning(f"No transactions found for {account} in backfill period")
                    
            except Exception as e:
                logger.error(f"Error backfilling {account}: {e}")
            finally:
                await self.backfill_collector.disconnect()
                
            # Small delay between accounts
            await asyncio.sleep(2)
            
    async def run_periodic_backfill(self, accounts: List[str], interval_hours: int = 1):
        """Run backfill checks periodically"""
        while self.is_running:
            try:
                logger.info("Running periodic backfill check")
                await self.perform_backfill(accounts, max_days=1)
                
                # Wait for next check
                await asyncio.sleep(interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic backfill: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def run_periodic_amm_snapshots(self, accounts: List[str], interval_minutes: int = 30):
        """Take periodic AMM snapshots"""
        while self.is_running:
            try:
                logger.info("Taking periodic AMM snapshots")
                
                # Use the AMM state tracker from realtime collector
                if self.realtime_collector.client and self.realtime_collector.client.is_open():
                    await self.realtime_collector.amm_state_tracker.periodic_snapshot(accounts)
                else:
                    logger.warning("Client not connected for AMM snapshots")
                    
                # Wait for next snapshot
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic AMM snapshots: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
                
    async def start(self, accounts: List[str]):
        """Start collection manager"""
        self.is_running = True
        logger.info(f"Starting collection manager for {len(accounts)} accounts")
        
        # Initial backfill check
        logger.info("Performing initial backfill check...")
        await self.perform_backfill(accounts, max_days=7)
        
        # Start real-time collection
        logger.info("Starting real-time collection...")
        self.realtime_task = asyncio.create_task(
            self.realtime_collector.run(accounts)
        )
        
        # Start periodic backfill
        logger.info("Starting periodic backfill checker...")
        self.backfill_task = asyncio.create_task(
            self.run_periodic_backfill(accounts, interval_hours=1)
        )
        
        # Start periodic AMM snapshots
        logger.info("Starting periodic AMM snapshot collector...")
        self.amm_snapshot_task = asyncio.create_task(
            self.run_periodic_amm_snapshots(accounts, interval_minutes=30)
        )
        
        # Wait for tasks
        try:
            await asyncio.gather(
                self.realtime_task,
                self.backfill_task,
                self.amm_snapshot_task
            )
        except asyncio.CancelledError:
            logger.info("Collection tasks cancelled")
            
    async def stop(self):
        """Stop collection manager"""
        logger.info("Stopping collection manager...")
        self.is_running = False
        
        # Stop collectors
        await self.realtime_collector.stop()
        
        # Cancel tasks
        if self.realtime_task and not self.realtime_task.done():
            self.realtime_task.cancel()
            
        if self.backfill_task and not self.backfill_task.done():
            self.backfill_task.cancel()
            
        if hasattr(self, 'amm_snapshot_task') and self.amm_snapshot_task and not self.amm_snapshot_task.done():
            self.amm_snapshot_task.cancel()
            
        logger.info("Collection manager stopped")
        
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "is_running": self.is_running,
            "realtime_connected": (
                self.realtime_collector.client and 
                self.realtime_collector.client.is_open()
            ),
            "monitored_accounts": len(self.realtime_collector.monitored_accounts),
            "last_processed_ledgers": self.realtime_collector.last_processed_ledger,
            "reconnect_attempts": self.realtime_collector.reconnect_attempts
        }


async def main():
    """Main entry point"""
    import json
    from pathlib import Path
    
    # Load tokens
    tokens_file = Path("src/config/tokens.json")
    with open(tokens_file) as f:
        tokens = json.load(f)
        
    # Get AMM addresses
    amm_addresses = [token_info["amm_address"] for token_info in tokens.values()]
    
    # Initialize manager
    storage = DataStorage()
    manager = CollectionManager(storage)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(manager.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start collection
        await manager.start(amm_addresses)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Setup logging
    logger.add(
        "logs/collection_manager_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    # Add console output with colors
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>"
    )
    
    asyncio.run(main())