import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import json
from loguru import logger
from xrpl.asyncio.clients import AsyncWebsocketClient, AsyncJsonRpcClient
from xrpl.models.requests import AccountInfo, AccountLines, LedgerEntry
from xrpl.models import Subscribe, Unsubscribe
import os

from src.config.settings import Settings


class AMMDataFetcher:
    """Specialized fetcher for XRPL AMM pool data"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ws_url, self.json_rpc_url = settings.get_network_urls()
        self.ws_client: Optional[AsyncWebsocketClient] = None
        self.json_client: Optional[AsyncJsonRpcClient] = None
        
        # Load token configuration
        self.tokens = self._load_token_config()
        
    def _load_token_config(self) -> Dict[str, Any]:
        """Load token configuration from JSON file"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config", "tokens.json"
        )
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load token config: {e}")
            return {}
    
    async def connect(self):
        """Connect to XRPL"""
        try:
            self.ws_client = AsyncWebsocketClient(self.ws_url)
            await self.ws_client.open()
            
            self.json_client = AsyncJsonRpcClient(self.json_rpc_url)
            
            logger.info(f"Connected to XRPL AMM data fetcher")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from XRPL"""
        if self.ws_client and self.ws_client.is_open():
            await self.ws_client.close()
    
    async def get_amm_info(self, amm_address: str) -> Dict[str, Any]:
        """Get current AMM pool information"""
        try:
            # Get account info
            account_request = AccountInfo(account=amm_address)
            account_response = await self.json_client.request(account_request)
            
            if not account_response.is_successful():
                logger.error(f"Failed to get AMM account info: {account_response.result}")
                return {}
            
            account_data = account_response.result["account_data"]
            
            # Get AMM object from ledger
            amm_id = account_data.get("AMMID")
            if amm_id:
                ledger_request = LedgerEntry(amm=amm_id)
                ledger_response = await self.json_client.request(ledger_request)
                
                if ledger_response.is_successful():
                    amm_object = ledger_response.result.get("node", {})
                    return self._parse_amm_object(amm_object, account_data)
            
            return {
                "address": amm_address,
                "balance": account_data.get("Balance", "0"),
                "owner_count": account_data.get("OwnerCount", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting AMM info: {e}")
            return {}
    
    def _parse_amm_object(self, amm_object: Dict, account_data: Dict) -> Dict[str, Any]:
        """Parse AMM object from ledger"""
        return {
            "address": account_data.get("Account"),
            "trading_fee": amm_object.get("TradingFee", 0) / 1000,  # Convert to percentage
            "asset1": amm_object.get("Asset"),
            "asset2": amm_object.get("Asset2"),
            "lp_token": amm_object.get("LPTokenBalance"),
            "auction_slot": amm_object.get("AuctionSlot"),
            "vote_slots": amm_object.get("VoteSlots", [])
        }
    
    async def get_pool_reserves(self, amm_address: str) -> Tuple[Decimal, Decimal]:
        """Get current pool reserves"""
        try:
            # Get XRP balance
            account_info = await self.get_amm_info(amm_address)
            xrp_balance = Decimal(account_info.get("balance", "0")) / Decimal("1000000")
            
            # Get token balance
            lines_request = AccountLines(account=amm_address)
            lines_response = await self.json_client.request(lines_request)
            
            if lines_response.is_successful():
                lines = lines_response.result.get("lines", [])
                if lines:
                    token_balance = Decimal(lines[0].get("balance", "0"))
                    return xrp_balance, abs(token_balance)
            
            return xrp_balance, Decimal("0")
            
        except Exception as e:
            logger.error(f"Error getting pool reserves: {e}")
            return Decimal("0"), Decimal("0")
    
    async def calculate_pool_metrics(self, amm_address: str) -> Dict[str, Any]:
        """Calculate various pool metrics"""
        xrp_reserve, token_reserve = await self.get_pool_reserves(amm_address)
        
        if xrp_reserve == 0 or token_reserve == 0:
            return {}
        
        # Calculate price
        price = token_reserve / xrp_reserve
        
        # Calculate k (constant product)
        k = xrp_reserve * token_reserve
        
        # Calculate total value locked (TVL) in XRP
        tvl_xrp = xrp_reserve * 2  # Assuming equal value
        
        return {
            "xrp_reserve": float(xrp_reserve),
            "token_reserve": float(token_reserve),
            "price": float(price),
            "k_constant": float(k),
            "tvl_xrp": float(tvl_xrp),
            "timestamp": datetime.now()
        }
    
    async def monitor_amm_pools(
        self,
        interval_seconds: int = 300,  # 5 minutes
        duration_hours: int = 24
    ) -> Dict[str, pd.DataFrame]:
        """Monitor all AMM pools for a specified duration"""
        all_data = {}
        end_time = datetime.now() + timedelta(hours=duration_hours)
        
        while datetime.now() < end_time:
            for token_name, token_info in self.tokens.items():
                amm_address = token_info["amm_address"]
                
                try:
                    metrics = await self.calculate_pool_metrics(amm_address)
                    
                    if metrics:
                        if token_name not in all_data:
                            all_data[token_name] = []
                        
                        metrics["token"] = token_name
                        all_data[token_name].append(metrics)
                        
                        logger.info(
                            f"{token_name} AMM - Price: {metrics['price']:.6f}, "
                            f"TVL: {metrics['tvl_xrp']:.2f} XRP"
                        )
                
                except Exception as e:
                    logger.error(f"Error monitoring {token_name}: {e}")
            
            await asyncio.sleep(interval_seconds)
        
        # Convert to DataFrames
        result = {}
        for token_name, data_list in all_data.items():
            if data_list:
                result[token_name] = pd.DataFrame(data_list)
        
        return result
    
    async def get_historical_snapshots(
        self,
        token_name: str,
        num_snapshots: int = 100,
        interval_minutes: int = 60
    ) -> pd.DataFrame:
        """Get historical snapshots of AMM pool state"""
        if token_name not in self.tokens:
            logger.error(f"Token {token_name} not found in configuration")
            return pd.DataFrame()
        
        amm_address = self.tokens[token_name]["amm_address"]
        snapshots = []
        
        for i in range(num_snapshots):
            try:
                metrics = await self.calculate_pool_metrics(amm_address)
                if metrics:
                    metrics["snapshot_num"] = i
                    snapshots.append(metrics)
                
                if i < num_snapshots - 1:
                    await asyncio.sleep(interval_minutes * 60)
                    
            except Exception as e:
                logger.error(f"Error in snapshot {i}: {e}")
        
        return pd.DataFrame(snapshots)
    
    async def analyze_liquidity_changes(
        self,
        token_name: str,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze liquidity changes over time"""
        # This would require historical data or real-time monitoring
        # For now, return current state
        if token_name not in self.tokens:
            return {}
        
        amm_address = self.tokens[token_name]["amm_address"]
        current_metrics = await self.calculate_pool_metrics(amm_address)
        
        return {
            "current_metrics": current_metrics,
            "liquidity_trend": "stable",  # Would calculate from historical data
            "volume_estimate": 0,  # Would estimate from reserve changes
            "fee_apr": 0  # Would calculate from trading volume and fees
        }
    
    async def find_arbitrage_opportunities(
        self,
        min_profit_xrp: Decimal = Decimal("10")
    ) -> List[Dict[str, Any]]:
        """Find potential arbitrage opportunities between AMMs and CEX"""
        opportunities = []
        
        # Get all AMM prices
        amm_prices = {}
        for token_name, token_info in self.tokens.items():
            try:
                metrics = await self.calculate_pool_metrics(token_info["amm_address"])
                if metrics:
                    amm_prices[token_name] = metrics["price"]
            except:
                continue
        
        # Here you would compare with CEX prices
        # For demonstration, we'll just log the AMM prices
        logger.info(f"Current AMM prices: {amm_prices}")
        
        return opportunities
    
    async def export_amm_data(
        self,
        data: Dict[str, pd.DataFrame],
        base_path: str = "data/amm"
    ):
        """Export AMM data to files"""
        os.makedirs(base_path, exist_ok=True)
        
        for token_name, df in data.items():
            if df.empty:
                continue
            
            # CSV export
            csv_path = os.path.join(base_path, f"{token_name}_amm_data.csv")
            df.to_csv(csv_path, index=False)
            
            # Parquet export for better compression
            parquet_path = os.path.join(base_path, f"{token_name}_amm_data.parquet")
            df.to_parquet(parquet_path, index=False)
            
            logger.info(f"Exported {token_name} AMM data: {len(df)} records")