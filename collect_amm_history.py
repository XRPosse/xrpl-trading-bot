"""
Collect 30-day historical AMM state changes
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models import AccountTx, AMMInfo
from xrpl.utils import ripple_time_to_datetime
from decimal import Decimal

from src.config.settings import get_settings
from src.database.storage import DataStorage
from src.database.models import init_database


class AMMHistoryCollector:
    """Collect historical AMM state changes"""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage = DataStorage()
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
            
    async def get_amm_affecting_transactions(self, amm_address: str, ledger_min: int, ledger_max: int):
        """Get all transactions that might affect AMM state"""
        transactions = []
        marker = None
        
        while True:
            try:
                request = AccountTx(
                    account=amm_address,
                    ledger_index_min=ledger_min,
                    ledger_index_max=ledger_max,
                    marker=marker
                )
                
                response = await self.client.request(request)
                
                if not response.is_successful():
                    logger.error(f"Failed to get transactions: {response.result}")
                    break
                    
                txs = response.result.get("transactions", [])
                transactions.extend(txs)
                
                marker = response.result.get("marker")
                if not marker:
                    break
                    
                logger.debug(f"Fetched {len(txs)} transactions, total: {len(transactions)}")
                
            except Exception as e:
                logger.error(f"Error fetching transactions: {e}")
                break
                
        return transactions
        
    async def get_amm_state_at_ledger(self, amm_address: str, ledger_index: int):
        """Get AMM state at specific ledger"""
        try:
            request = AMMInfo(
                amm_account=amm_address,
                ledger_index=ledger_index
            )
            
            response = await self.client.request(request)
            
            if response.is_successful():
                return response.result.get("amm", {})
            else:
                logger.error(f"Failed to get AMM info at ledger {ledger_index}: {response.result}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting AMM state: {e}")
            return None
            
    async def process_amm_transaction(self, tx_data: dict, amm_address: str):
        """Process a transaction and capture AMM state after it"""
        try:
            meta = tx_data.get("meta", {})
            tx = tx_data.get("tx", {})
            
            # Skip failed transactions
            if meta.get("TransactionResult") != "tesSUCCESS":
                return
                
            tx_type = tx.get("TransactionType")
            ledger_index = tx_data.get("ledger_index", tx.get("ledger_index"))
            
            # Check if this transaction affects AMM state
            affects_amm = False
            
            # Direct AMM transactions
            if tx_type in ["AMMDeposit", "AMMWithdraw", "AMMCreate", "AMMBid", "AMMVote"]:
                affects_amm = True
            
            # Payments and offers that go through AMM
            elif tx_type in ["Payment", "OfferCreate"]:
                # Check if AMM was involved by looking at affected nodes
                affected_nodes = meta.get("AffectedNodes", [])
                for node in affected_nodes:
                    if "ModifiedNode" in node:
                        modified = node["ModifiedNode"]
                        if modified.get("LedgerEntryType") == "AMM":
                            affects_amm = True
                            break
                            
            if not affects_amm:
                return
                
            # Get AMM state after this transaction
            amm_state = await self.get_amm_state_at_ledger(amm_address, ledger_index)
            if not amm_state:
                return
                
            # Extract pool data
            amount = amm_state.get("Amount")
            amount2 = amm_state.get("Amount2")
            lp_token = amm_state.get("LPTokenBalance", {})
            trading_fee = amm_state.get("TradingFee", 0)
            
            if not amount or not amount2:
                return
                
            # Parse amounts
            if isinstance(amount, str):
                asset1_amount = Decimal(amount) / Decimal(1000000)  # XRP drops to XRP
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
                
            # Calculate metrics
            k_constant = asset1_amount * asset2_amount
            price = asset2_amount / asset1_amount if asset1_amount > 0 else 0
            
            # Estimate TVL
            if asset1_currency == "XRP":
                tvl_xrp = asset1_amount * 2
            else:
                tvl_xrp = 0
                
            # Create snapshot
            snapshot_data = {
                "timestamp": ripple_time_to_datetime(tx.get("date", 0)),
                "ledger_index": ledger_index,
                "amm_address": amm_address,
                "asset1_currency": asset1_currency,
                "asset1_issuer": asset1_issuer,
                "asset1_amount": asset1_amount,
                "asset2_currency": asset2_currency,
                "asset2_issuer": asset2_issuer,
                "asset2_amount": asset2_amount,
                "lp_token_currency": lp_token.get("currency", ""),
                "lp_token_supply": Decimal(lp_token.get("value", 0)),
                "trading_fee": trading_fee,
                "k_constant": k_constant,
                "price_asset2_per_asset1": price,
                "tvl_xrp": tvl_xrp
            }
            
            # Store snapshot
            await self.storage.store_amm_snapshot(snapshot_data)
            self.processed_count += 1
            
            logger.info(f"Captured AMM state at ledger {ledger_index}: {asset1_currency} {asset1_amount:.2f} / {asset2_currency} {asset2_amount:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing AMM transaction: {e}")
            
    async def collect_amm_history(self, amm_address: str, token_name: str, days: int = 30):
        """Collect historical AMM state changes"""
        try:
            # Calculate ledger range (21,600 ledgers per day)
            ledgers_per_day = 21600
            current_ledger = 97478500  # Approximate current ledger
            start_ledger = current_ledger - (days * ledgers_per_day)
            
            logger.info(f"\nCollecting {days}-day AMM history for {token_name}")
            logger.info(f"AMM: {amm_address}")
            logger.info(f"Ledger range: {start_ledger:,} to {current_ledger:,}")
            
            # Process in chunks to avoid timeouts
            chunk_size = 5000
            total_transactions = 0
            
            for chunk_start in range(start_ledger, current_ledger, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, current_ledger)
                
                logger.info(f"Processing ledgers {chunk_start:,} to {chunk_end:,}")
                
                # Get transactions in this chunk
                transactions = await self.get_amm_affecting_transactions(
                    amm_address, chunk_start, chunk_end
                )
                
                total_transactions += len(transactions)
                
                # Process each transaction
                for tx in transactions:
                    await self.process_amm_transaction(tx, amm_address)
                    
                # Small delay between chunks
                await asyncio.sleep(0.5)
                
            logger.success(f"Completed {token_name}: {total_transactions} transactions, {self.processed_count} snapshots stored")
            
        except Exception as e:
            logger.error(f"Error collecting AMM history for {token_name}: {e}")
            
    async def run(self):
        """Collect AMM history for all tokens"""
        await self.connect()
        
        try:
            # Load token configuration
            tokens_file = Path("src/config/tokens.json")
            with open(tokens_file) as f:
                tokens = json.load(f)
                
            logger.info(f"Collecting 30-day AMM history for {len(tokens)} tokens")
            
            # Collect history for each token
            for token_name, token_info in tokens.items():
                self.processed_count = 0
                await self.collect_amm_history(
                    token_info["amm_address"],
                    token_name,
                    days=30
                )
                
                # Delay between tokens
                await asyncio.sleep(2)
                
            logger.success("AMM history collection complete!")
            
        finally:
            await self.disconnect()


async def main():
    """Main function"""
    # Initialize database
    settings = get_settings()
    init_database(settings.database_url)
    
    # Run collector
    collector = AMMHistoryCollector()
    await collector.run()


if __name__ == "__main__":
    print("="*60)
    print("AMM HISTORY COLLECTION")
    print("="*60)
    print("This will collect 30 days of AMM state changes")
    print("by processing all transactions that affected the pools.")
    print("\nThis may take several minutes...")
    print("="*60)
    
    asyncio.run(main())