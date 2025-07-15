"""
Efficiently collect AMM state changes by monitoring balance changes
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models import AccountTx, ServerInfo
from xrpl.utils import ripple_time_to_datetime

from src.config.settings import get_settings
from src.database.storage import DataStorage
from src.database.models import init_database, AMMSnapshot, get_session
from src.data.metadata_processor import MetadataProcessor
from sqlalchemy import select, func


class EfficientAMMCollector:
    """Efficiently collect AMM state changes"""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage = DataStorage()
        self.metadata_processor = MetadataProcessor()
        self.client = None
        self.processed_count = 0
        
    async def connect(self):
        """Connect to XRPL"""
        self.client = AsyncWebsocketClient(self.settings.xrpl_wss_url)
        await self.client.open()
        logger.info(f"Connected to XRPL at {self.settings.xrpl_wss_url}")
        
    async def disconnect(self):
        """Disconnect from XRPL"""
        if self.client:
            await self.client.close()
            
    async def get_current_ledger(self):
        """Get current ledger index"""
        response = await self.client.request(ServerInfo())
        if response.is_successful():
            return response.result["info"]["validated_ledger"]["seq"]
        return None
        
    async def get_existing_snapshots(self, amm_address: str):
        """Get existing snapshot ledgers to avoid duplicates"""
        session = get_session(self.storage.engine)
        try:
            results = session.execute(
                select(AMMSnapshot.ledger_index)
                .where(AMMSnapshot.amm_address == amm_address)
            ).scalars().all()
            return set(results)
        finally:
            session.close()
            
    async def process_transactions_batch(self, amm_address: str, transactions: list, existing_ledgers: set):
        """Process a batch of transactions and extract AMM state changes"""
        state_changes = []
        
        for tx_data in transactions:
            try:
                meta = tx_data.get("meta", {})
                tx = tx_data.get("tx", {})
                
                # Skip failed transactions
                if meta.get("TransactionResult") != "tesSUCCESS":
                    continue
                    
                ledger_index = tx_data.get("ledger_index", tx.get("ledger_index"))
                
                # Skip if we already have this snapshot
                if ledger_index in existing_ledgers:
                    continue
                    
                # Look for AMM balance changes in metadata
                affected_nodes = meta.get("AffectedNodes", [])
                amm_changed = False
                asset1_amount = None
                asset2_amount = None
                lp_token_amount = None
                
                for node in affected_nodes:
                    if "ModifiedNode" in node:
                        modified = node["ModifiedNode"]
                        if modified.get("LedgerEntryType") == "AMM" and modified.get("LedgerIndex"):
                            # Found AMM modification
                            final_fields = modified.get("FinalFields", {})
                            
                            # Extract amounts
                            amount = final_fields.get("Amount")
                            amount2 = final_fields.get("Amount2")
                            lp_token = final_fields.get("LPTokenBalance", {})
                            
                            if amount and amount2:
                                amm_changed = True
                                
                                # Parse amounts
                                if isinstance(amount, str):
                                    asset1_amount = Decimal(amount) / Decimal(1000000)
                                    asset1_currency = "XRP"
                                    asset1_issuer = None
                                else:
                                    asset1_amount = Decimal(amount.get("value", 0))
                                    asset1_currency = amount.get("currency")
                                    asset1_issuer = amount.get("issuer")
                                    
                                if isinstance(amount2, str):
                                    asset2_amount = Decimal(amount2) / Decimal(1000000)
                                    asset2_currency = "XRP"
                                    asset2_issuer = None
                                else:
                                    asset2_amount = Decimal(amount2.get("value", 0))
                                    asset2_currency = amount2.get("currency")
                                    asset2_issuer = amount2.get("issuer")
                                    
                                lp_token_amount = Decimal(lp_token.get("value", 0))
                                trading_fee = final_fields.get("TradingFee", 0)
                                
                                break
                                
                if amm_changed and asset1_amount and asset2_amount:
                    # Calculate metrics
                    k_constant = asset1_amount * asset2_amount
                    price = asset2_amount / asset1_amount if asset1_amount > 0 else 0
                    
                    # Estimate TVL
                    if asset1_currency == "XRP":
                        tvl_xrp = asset1_amount * 2
                    else:
                        tvl_xrp = 0
                        
                    state_changes.append({
                        "timestamp": ripple_time_to_datetime(tx.get("date", 0)),
                        "ledger_index": ledger_index,
                        "amm_address": amm_address,
                        "asset1_currency": asset1_currency,
                        "asset1_issuer": asset1_issuer,
                        "asset1_amount": asset1_amount,
                        "asset2_currency": asset2_currency,
                        "asset2_issuer": asset2_issuer,
                        "asset2_amount": asset2_amount,
                        "lp_token_currency": lp_token.get("currency", "") if lp_token else "",
                        "lp_token_supply": lp_token_amount,
                        "trading_fee": trading_fee,
                        "k_constant": k_constant,
                        "price_asset2_per_asset1": price,
                        "tvl_xrp": tvl_xrp,
                        "transaction_hash": tx.get("hash"),
                        "transaction_type": tx.get("TransactionType")
                    })
                    
            except Exception as e:
                logger.error(f"Error processing transaction: {e}")
                continue
                
        return state_changes
        
    async def collect_amm_state_changes(self, amm_address: str, token_name: str, days: int = 30):
        """Collect AMM state changes efficiently"""
        try:
            # Get current ledger
            current_ledger = await self.get_current_ledger()
            if not current_ledger:
                logger.error("Could not get current ledger")
                return
                
            # Calculate ledger range
            ledgers_per_day = 21600
            start_ledger = current_ledger - (days * ledgers_per_day)
            
            logger.info(f"\nCollecting {days}-day AMM state changes for {token_name}")
            logger.info(f"AMM: {amm_address}")
            logger.info(f"Ledger range: {start_ledger:,} to {current_ledger:,}")
            
            # Get existing snapshots to avoid duplicates
            existing_ledgers = await self.get_existing_snapshots(amm_address)
            logger.info(f"Found {len(existing_ledgers)} existing snapshots")
            
            # Collect all transactions
            all_transactions = []
            marker = None
            
            while True:
                try:
                    request = AccountTx(
                        account=amm_address,
                        ledger_index_min=start_ledger,
                        ledger_index_max=current_ledger,
                        marker=marker,
                        limit=200  # Max allowed
                    )
                    
                    response = await self.client.request(request)
                    
                    if not response.is_successful():
                        logger.error(f"Failed to get transactions: {response.result}")
                        break
                        
                    txs = response.result.get("transactions", [])
                    all_transactions.extend(txs)
                    
                    logger.info(f"Fetched {len(txs)} transactions, total: {len(all_transactions)}")
                    
                    marker = response.result.get("marker")
                    if not marker:
                        break
                        
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error fetching transactions: {e}")
                    break
                    
            # Process transactions in batches
            logger.info(f"Processing {len(all_transactions)} transactions...")
            
            batch_size = 100
            total_changes = 0
            
            for i in range(0, len(all_transactions), batch_size):
                batch = all_transactions[i:i+batch_size]
                state_changes = await self.process_transactions_batch(amm_address, batch, existing_ledgers)
                
                # Store state changes
                for change in state_changes:
                    await self.storage.store_amm_snapshot(change)
                    total_changes += 1
                    
                    if total_changes % 10 == 0:
                        logger.info(f"Stored {total_changes} state changes...")
                        
            logger.success(f"Completed {token_name}: Found {total_changes} AMM state changes from {len(all_transactions)} transactions")
            self.processed_count += total_changes
            
        except Exception as e:
            logger.error(f"Error collecting AMM state changes for {token_name}: {e}")
            
    async def run(self, specific_token: str = None):
        """Collect AMM state changes for all tokens or specific token"""
        await self.connect()
        
        try:
            # Load token configuration
            tokens_file = Path("src/config/tokens.json")
            with open(tokens_file) as f:
                tokens = json.load(f)
                
            if specific_token:
                if specific_token in tokens:
                    tokens = {specific_token: tokens[specific_token]}
                else:
                    logger.error(f"Token {specific_token} not found")
                    return
                    
            logger.info(f"Collecting 30-day AMM state changes for {len(tokens)} tokens")
            
            # Collect state changes for each token
            for token_name, token_info in tokens.items():
                self.processed_count = 0
                await self.collect_amm_state_changes(
                    token_info["amm_address"],
                    token_name,
                    days=30
                )
                
                # Delay between tokens
                await asyncio.sleep(1)
                
            logger.success("AMM state change collection complete!")
            
            # Show summary
            await self.show_summary()
            
        finally:
            await self.disconnect()
            
    async def show_summary(self):
        """Show collection summary"""
        session = get_session(self.storage.engine)
        try:
            # Get snapshot counts by AMM
            results = session.execute(
                select(
                    AMMSnapshot.amm_address,
                    func.count(AMMSnapshot.id).label('count'),
                    func.min(AMMSnapshot.timestamp).label('earliest'),
                    func.max(AMMSnapshot.timestamp).label('latest')
                )
                .group_by(AMMSnapshot.amm_address)
            ).all()
            
            print("\n=== Collection Summary ===")
            total = 0
            for row in results:
                count = row.count
                total += count
                print(f"{row.amm_address[:10]}...: {count} snapshots, {row.earliest} to {row.latest}")
                
            print(f"\nTotal AMM snapshots: {total}")
            
        finally:
            session.close()


async def main():
    """Main function"""
    import sys
    
    # Initialize database
    settings = get_settings()
    init_database(settings.database_url)
    
    # Check for specific token argument
    specific_token = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run collector
    collector = EfficientAMMCollector()
    await collector.run(specific_token)


if __name__ == "__main__":
    print("="*60)
    print("EFFICIENT AMM STATE CHANGE COLLECTION")
    print("="*60)
    print("This will collect 30 days of AMM state changes")
    print("by efficiently processing transaction metadata.")
    print("\nUsage: python collect_amm_state_changes.py [TOKEN]")
    print("Example: python collect_amm_state_changes.py RLUSD")
    print("="*60)
    
    asyncio.run(main())