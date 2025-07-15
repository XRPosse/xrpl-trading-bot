"""
Real-time AMM state tracking
"""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from loguru import logger
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.models import AccountInfo, AMMInfo
from xrpl.utils import ripple_time_to_datetime

from src.database.storage import DataStorage
from src.database.models import AMMSnapshot


class AMMStateTracker:
    """Track AMM pool state changes in real-time"""
    
    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.amm_states: Dict[str, Dict[str, Any]] = {}
        self.client: Optional[AsyncWebsocketClient] = None
        
    async def set_client(self, client: AsyncWebsocketClient):
        """Set the XRPL client"""
        self.client = client
        
    async def get_amm_info(self, amm_address: str) -> Optional[Dict[str, Any]]:
        """Get current AMM state from XRPL"""
        if not self.client or not self.client.is_open():
            logger.error("Client not connected")
            return None
            
        try:
            # Get AMM info
            amm_info = AMMInfo(
                amm_account=amm_address,
                ledger_index="validated"
            )
            response = await self.client.request(amm_info)
            
            if response.is_successful():
                return response.result.get("amm", {})
            else:
                logger.error(f"Failed to get AMM info: {response.result}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting AMM info for {amm_address}: {e}")
            return None
            
    async def process_amm_transaction(self, tx_data: Dict[str, Any], amm_address: str):
        """Process transaction that affects AMM state"""
        try:
            tx = tx_data.get("transaction", tx_data)
            tx_type = tx.get("TransactionType")
            
            # Check if this is an AMM-related transaction
            if tx_type not in ["AMMDeposit", "AMMWithdraw", "AMMCreate", "AMMBid", "AMMVote"]:
                # Could also be a Payment or OfferCreate that affects the pool
                # Check if the account is the AMM
                if tx.get("Account") != amm_address and tx.get("Destination") != amm_address:
                    return
                    
            # Get current AMM state
            amm_info = await self.get_amm_info(amm_address)
            if not amm_info:
                return
                
            # Extract pool data
            amount = amm_info.get("Amount")
            amount2 = amm_info.get("Amount2")
            lp_token = amm_info.get("LPTokenBalance", {})
            trading_fee = amm_info.get("TradingFee", 0)
            
            if not amount or not amount2:
                logger.warning(f"Missing pool amounts for {amm_address}")
                return
                
            # Parse amounts
            asset1_amount = Decimal(amount) if isinstance(amount, str) else Decimal(amount.get("value", 0))
            asset1_currency = "XRP" if isinstance(amount, str) else amount.get("currency")
            asset1_issuer = None if isinstance(amount, str) else amount.get("issuer")
            
            asset2_amount = Decimal(amount2) if isinstance(amount2, str) else Decimal(amount2.get("value", 0))
            asset2_currency = "XRP" if isinstance(amount2, str) else amount2.get("currency")
            asset2_issuer = None if isinstance(amount2, str) else amount2.get("issuer")
            
            # Calculate metrics
            k_constant = asset1_amount * asset2_amount
            price = asset2_amount / asset1_amount if asset1_amount > 0 else 0
            
            # Estimate TVL in XRP
            if asset1_currency == "XRP":
                tvl_xrp = asset1_amount * 2  # Double the XRP amount
            else:
                # For non-XRP pairs, we'd need external price data
                tvl_xrp = 0
                
            # Create snapshot
            snapshot_data = {
                "timestamp": ripple_time_to_datetime(tx.get("date", 0)),
                "ledger_index": tx_data.get("ledger_index", tx.get("ledger_index")),
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
            
            # Update cached state
            self.amm_states[amm_address] = {
                "asset1_amount": asset1_amount,
                "asset2_amount": asset2_amount,
                "last_updated": datetime.utcnow(),
                "ledger_index": snapshot_data["ledger_index"]
            }
            
            logger.info(f"Updated AMM state for {amm_address}: {asset1_currency} {asset1_amount} / {asset2_currency} {asset2_amount}")
            
        except Exception as e:
            logger.error(f"Error processing AMM transaction: {e}")
            
    async def check_significant_change(self, amm_address: str, threshold: float = 0.01) -> bool:
        """Check if AMM state changed significantly (default 1%)"""
        if amm_address not in self.amm_states:
            return True  # First time seeing this AMM
            
        try:
            current_info = await self.get_amm_info(amm_address)
            if not current_info:
                return False
                
            amount = current_info.get("Amount")
            if isinstance(amount, str):
                current_amount = Decimal(amount)
            else:
                current_amount = Decimal(amount.get("value", 0))
                
            cached_amount = self.amm_states[amm_address]["asset1_amount"]
            
            # Calculate percentage change
            if cached_amount > 0:
                change = abs(current_amount - cached_amount) / cached_amount
                return change >= threshold
            else:
                return True
                
        except Exception as e:
            logger.error(f"Error checking AMM change: {e}")
            return False
            
    async def periodic_snapshot(self, amm_addresses: list):
        """Take periodic snapshots of all AMMs"""
        for amm_address in amm_addresses:
            try:
                # Check if there's been a significant change
                if await self.check_significant_change(amm_address):
                    amm_info = await self.get_amm_info(amm_address)
                    if amm_info:
                        # Create a dummy transaction data for snapshot
                        tx_data = {
                            "transaction": {
                                "TransactionType": "PeriodicSnapshot",
                                "date": 0  # Will use current time
                            },
                            "ledger_index": amm_info.get("ledger_index")
                        }
                        await self.process_amm_transaction(tx_data, amm_address)
                        
            except Exception as e:
                logger.error(f"Error taking periodic snapshot for {amm_address}: {e}")