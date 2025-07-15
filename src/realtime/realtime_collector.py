"""
Real-time XRPL transaction collector with automatic backfill
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from loguru import logger

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models import Subscribe, Unsubscribe, ServerInfo, AccountTx
from xrpl.utils import ripple_time_to_datetime

from ..database.storage import DataStorage
from ..database.models import DataCollectionLog
from ..data.metadata_processor import MetadataProcessor
from ..config.settings import get_settings
from .amm_state_tracker import AMMStateTracker


class RealtimeCollector:
    """Collects real-time transactions with automatic backfill"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.settings = get_settings()
        self.client: Optional[AsyncWebsocketClient] = None
        self.metadata_processor = MetadataProcessor()
        self.amm_state_tracker = AMMStateTracker(storage)
        self.monitored_accounts: Set[str] = set()
        self.is_running = False
        self.last_processed_ledger: Dict[str, int] = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
    async def connect(self) -> bool:
        """Connect to XRPL websocket"""
        try:
            self.client = AsyncWebsocketClient(self.settings.xrpl_wss_url)
            await self.client.open()
            logger.info(f"Connected to XRPL at {self.settings.xrpl_wss_url}")
            self.reconnect_attempts = 0
            
            # Set client for AMM state tracker
            await self.amm_state_tracker.set_client(self.client)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from XRPL"""
        if self.client and self.client.is_open():
            try:
                await self.client.close()
                logger.info("Disconnected from XRPL")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                
    async def get_current_ledger(self) -> int:
        """Get current validated ledger"""
        if not self.client or not self.client.is_open():
            raise Exception("Not connected to XRPL")
            
        response = await self.client.request(ServerInfo())
        if response.is_successful():
            return response.result['info']['validated_ledger']['seq']
        raise Exception(f"Failed to get current ledger: {response.result}")
        
    async def subscribe_to_accounts(self, accounts: List[str]):
        """Subscribe to real-time updates for accounts"""
        if not self.client or not self.client.is_open():
            raise Exception("Not connected to XRPL")
            
        # Subscribe to transactions for these accounts
        request = Subscribe(
            accounts=accounts,
            streams=["ledger"]  # Also subscribe to ledger stream for sync
        )
        
        response = await self.client.request(request)
        if response.is_successful():
            self.monitored_accounts.update(accounts)
            logger.info(f"Subscribed to {len(accounts)} accounts")
            
            # Initialize last processed ledger for each account
            current_ledger = await self.get_current_ledger()
            for account in accounts:
                if account not in self.last_processed_ledger:
                    # Check database for last processed ledger
                    log = await self.storage.get_collection_log("realtime", account)
                    if log and log.get("last_processed_ledger"):
                        self.last_processed_ledger[account] = log["last_processed_ledger"]
                    else:
                        self.last_processed_ledger[account] = current_ledger
                        
            return True
        else:
            logger.error(f"Failed to subscribe: {response.result}")
            return False
            
    async def process_transaction(self, tx_data: Dict[str, Any], account: str):
        """Process a single transaction"""
        try:
            # Extract transaction details
            tx = tx_data.get("transaction", tx_data)
            ledger_index = tx_data.get("ledger_index", tx.get("ledger_index"))
            
            # Skip if we've already processed this ledger for this account
            if ledger_index and ledger_index <= self.last_processed_ledger.get(account, 0):
                return
                
            # Extract token transfers
            transfers = self.metadata_processor.extract_token_transfers(tx_data)
            
            stored_count = 0
            for transfer in transfers:
                transfer_data = {
                    "transaction_hash": tx.get("hash"),
                    "ledger_index": ledger_index,
                    "timestamp": ripple_time_to_datetime(tx.get("date", 0)),
                    "wallet_address": account,
                    "currency": transfer["currency"],
                    "issuer": transfer.get("issuer"),
                    "amount": transfer["amount"],
                    "is_receive": transfer["is_receive"],
                    "counterparty": transfer.get("counterparty"),
                    "transaction_type": tx.get("TransactionType", "").lower()
                }
                
                await self.storage.store_token_transaction(transfer_data)
                stored_count += 1
                
            if stored_count > 0:
                logger.debug(f"Stored {stored_count} transfers from tx {tx.get('hash')[:8]}...")
                
            # Check for AMM state changes
            await self.amm_state_tracker.process_amm_transaction(tx_data, account)
                
            # Update last processed ledger
            if ledger_index:
                self.last_processed_ledger[account] = max(
                    self.last_processed_ledger.get(account, 0),
                    ledger_index
                )
                
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            
    async def check_and_backfill(self, account: str):
        """Check for gaps and backfill if needed"""
        try:
            current_ledger = await self.get_current_ledger()
            last_processed = self.last_processed_ledger.get(account, current_ledger)
            
            # Check if we have a gap
            gap = current_ledger - last_processed
            
            if gap > 100:  # More than ~6 minutes of data
                logger.warning(f"Gap detected for {account}: {gap} ledgers behind")
                
                # Backfill in chunks
                chunk_size = 1000
                backfilled = 0
                
                while last_processed < current_ledger - 10:  # Leave small buffer
                    end_ledger = min(last_processed + chunk_size, current_ledger)
                    
                    logger.info(f"Backfilling {account} ledgers {last_processed} to {end_ledger}")
                    
                    # Fetch transactions for this range
                    try:
                        request = AccountTx(
                            account=account,
                            ledger_index_min=last_processed,
                            ledger_index_max=end_ledger,
                            limit=200
                        )
                        
                        response = await self.client.request(request)
                        
                        if response.is_successful():
                            transactions = response.result.get("transactions", [])
                            
                            for tx_wrapper in transactions:
                                await self.process_transaction(tx_wrapper, account)
                                backfilled += 1
                                
                            logger.info(f"Backfilled {len(transactions)} transactions")
                        else:
                            logger.error(f"Backfill failed: {response.result}")
                            break
                            
                    except Exception as e:
                        logger.error(f"Error during backfill: {e}")
                        break
                        
                    last_processed = end_ledger
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                if backfilled > 0:
                    logger.info(f"Backfill complete: {backfilled} transactions")
                    
        except Exception as e:
            logger.error(f"Error checking backfill: {e}")
            
    async def save_state(self):
        """Save current state to database"""
        for account, ledger in self.last_processed_ledger.items():
            try:
                log_data = {
                    "collection_type": "realtime",
                    "target": account,
                    "last_processed_ledger": ledger,
                    "last_run": datetime.utcnow(),
                    "status": "active" if self.is_running else "stopped",
                    "records_collected": 0  # Will be updated separately
                }
                
                # Check if log exists
                existing = await self.storage.get_collection_log("realtime", account)
                if existing:
                    await self.storage.update_collection_progress(
                        "realtime", account, ledger, 0
                    )
                else:
                    await self.storage.create_collection_log(log_data)
                    
            except Exception as e:
                logger.error(f"Error saving state for {account}: {e}")
                
    async def run(self, accounts: List[str]):
        """Main collection loop"""
        self.is_running = True
        logger.info(f"Starting real-time collection for {len(accounts)} accounts")
        
        while self.is_running:
            try:
                # Connect if not connected
                if not self.client or not self.client.is_open():
                    if not await self.connect():
                        await asyncio.sleep(5)
                        continue
                        
                # Subscribe to accounts
                if not self.monitored_accounts:
                    await self.subscribe_to_accounts(accounts)
                    
                # Check for backfill needs periodically
                for account in accounts:
                    await self.check_and_backfill(account)
                    
                # Process incoming messages
                message_count = 0
                async for message in self.client:
                    try:
                        if message.get("type") == "transaction":
                            # Process transaction
                            account = message.get("account")
                            if account in self.monitored_accounts:
                                await self.process_transaction(message, account)
                                message_count += 1
                                
                                # Save state periodically
                                if message_count % 100 == 0:
                                    await self.save_state()
                                    
                        elif message.get("type") == "ledgerClosed":
                            # New ledger closed, check for gaps
                            if message_count > 0:
                                logger.debug(f"Processed {message_count} messages in ledger")
                                message_count = 0
                                
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached, stopping")
                    break
                    
                # Exponential backoff
                wait_time = min(2 ** self.reconnect_attempts, 60)
                logger.info(f"Reconnecting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
        # Final state save
        await self.save_state()
        logger.info("Real-time collection stopped")
        
    async def stop(self):
        """Stop the collector"""
        logger.info("Stopping real-time collector...")
        self.is_running = False
        await self.disconnect()


async def main():
    """Run real-time collector"""
    # Load configuration
    tokens_file = Path("src/config/tokens.json")
    with open(tokens_file) as f:
        tokens = json.load(f)
        
    # Get AMM addresses
    amm_addresses = [token_info["amm_address"] for token_info in tokens.values()]
    
    # Initialize collector
    storage = DataStorage()
    collector = RealtimeCollector(storage)
    
    try:
        # Run collector
        await collector.run(amm_addresses)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await collector.stop()


if __name__ == "__main__":
    # Setup logging
    logger.add(
        "logs/realtime_collector_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    asyncio.run(main())