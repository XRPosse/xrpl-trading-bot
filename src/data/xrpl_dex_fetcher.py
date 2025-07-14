import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import json
from loguru import logger
from xrpl.asyncio.clients import AsyncWebsocketClient, AsyncJsonRpcClient
from xrpl.models.requests import Ledger, AccountOffers, BookOffers
from xrpl.models import LedgerClosed, Subscribe, Unsubscribe
import aiohttp

from src.config.settings import Settings
import os


class XRPLDexDataFetcher:
    """Fetches historical DEX and AMM data from XRPL"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ws_url, self.json_rpc_url = settings.get_network_urls()
        self.ws_client: Optional[AsyncWebsocketClient] = None
        self.json_client: Optional[AsyncJsonRpcClient] = None
        
        # Load token configuration
        self.tokens = self._load_token_config()
        
        # Additional known tokens (stablecoins, etc.)
        self.additional_tokens = {
            # Stablecoins
            "USD": {
                "Bitstamp": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                "Gatehub": "rhub8VRN55s94qWKDv6jmDy1pUykJzF3wq"
            },
            "USDT": {
                "Gatehub": "rcxJwBnv3sGxmnwGg1upoTvGMuwonqMcn"
            },
            # Other popular tokens
            "SOLO": {
                "issuer": "rsoLo2S1kiGeCcn6hCUXVrCpGMWLrRrLZz"
            },
            "CSC": {
                "issuer": "rCSCManTZ8ME9EoLrSHHYKW8PPwWMgkwr"
            },
            "CORE": {
                "issuer": "rcoreNywaoz2ZCQ8Lg2EbSLnGuRBmun6D"
            }
        }
    
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
            
            logger.info(f"Connected to XRPL DEX data fetcher: {self.ws_url}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from XRPL"""
        if self.ws_client and self.ws_client.is_open():
            await self.ws_client.close()
    
    async def fetch_dex_trades(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical DEX trades for a specific pair
        
        Note: XRPL doesn't provide historical trade data directly,
        so we use external data providers or parse transactions
        """
        logger.info(f"Fetching DEX trades for {base_currency}/{quote_currency}")
        
        # For now, we'll use XRPL Data API or similar service
        # In production, you'd want to use services like:
        # - Bithomp API
        # - XRPScan API
        # - XRPL.org Data API v2
        # - Run your own XRPL node with full history
        
        trades = await self._fetch_from_data_api(
            base_currency, base_issuer,
            quote_currency, quote_issuer,
            start_time, end_time
        )
        
        return trades
    
    async def _fetch_from_data_api(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Fetch data from XRPL Data API"""
        # Example using a hypothetical XRPL data service
        # Replace with actual API endpoints
        
        async with aiohttp.ClientSession() as session:
            # Construct API request
            base = f"{base_currency}+{base_issuer}" if base_issuer else "XRP"
            quote = f"{quote_currency}+{quote_issuer}" if quote_issuer else "XRP"
            
            url = f"https://data.xrpl.org/v2/exchanges/{base}/{quote}"
            params = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "interval": "1hour",
                "descending": False
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_exchange_data(data)
                    else:
                        logger.warning(f"API returned status {response.status}")
                        return pd.DataFrame()
            except Exception as e:
                logger.error(f"Error fetching from data API: {e}")
                return pd.DataFrame()
    
    def _parse_exchange_data(self, data: Dict) -> pd.DataFrame:
        """Parse exchange data from API response"""
        if "exchanges" not in data:
            return pd.DataFrame()
        
        exchanges = data["exchanges"]
        
        df = pd.DataFrame(exchanges)
        
        # Rename columns to match our format
        column_mapping = {
            "close_time": "timestamp",
            "base_volume": "base_volume",
            "quote_volume": "quote_volume",
            "exchange_rate": "price",
            "high": "high",
            "low": "low",
            "open": "open",
            "close": "close"
        }
        
        df = df.rename(columns=column_mapping)
        
        # Convert timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        return df
    
    async def fetch_order_book_history(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        num_snapshots: int = 100,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical order book snapshots
        
        This captures current order book state at intervals
        """
        logger.info(f"Fetching order book history for {base_currency}/{quote_currency}")
        
        snapshots = []
        
        for i in range(num_snapshots):
            try:
                # Get current order book
                taker_gets = {"currency": "XRP"} if base_currency == "XRP" else {
                    "currency": base_currency,
                    "issuer": base_issuer
                }
                
                taker_pays = {"currency": "XRP"} if quote_currency == "XRP" else {
                    "currency": quote_currency,
                    "issuer": quote_issuer
                }
                
                request = BookOffers(
                    taker_gets=taker_gets,
                    taker_pays=taker_pays,
                    limit=50
                )
                
                response = await self.json_client.request(request)
                
                if response.is_successful():
                    snapshot = {
                        "timestamp": datetime.now(),
                        "offers": response.result.get("offers", []),
                        "pair": f"{base_currency}/{quote_currency}"
                    }
                    snapshots.append(snapshot)
                
                # Wait for next interval
                if i < num_snapshots - 1:
                    await asyncio.sleep(interval_minutes * 60)
                    
            except Exception as e:
                logger.error(f"Error fetching order book: {e}")
        
        return snapshots
    
    async def fetch_amm_pool_data(
        self,
        pool_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Fetch AMM pool data including liquidity, volume, and fees
        
        AMM pools were introduced in XRPL in 2024
        """
        logger.info(f"Fetching AMM pool data for {pool_id}")
        
        # AMM-specific data fetching would go here
        # This requires specific AMM endpoints or transaction parsing
        
        # Placeholder for AMM data structure
        amm_data = {
            "timestamp": [],
            "liquidity_xrp": [],
            "liquidity_token": [],
            "volume_24h": [],
            "fees_24h": [],
            "price": [],
            "pool_share": []
        }
        
        return pd.DataFrame(amm_data)
    
    async def discover_active_pairs(self) -> List[Dict[str, Any]]:
        """Discover active trading pairs on XRPL DEX"""
        active_pairs = []
        
        # Add pairs from tokens.json (all AMM pools with XRP)
        for token_name, token_info in self.tokens.items():
            pair_info = {
                "symbol": token_name,
                "base": token_name,
                "base_currency": token_info["token_code"],
                "base_issuer": token_info["token_address"],
                "quote": "XRP",
                "amm_address": token_info["amm_address"],
                "amm_code": token_info["amm_code"],
                "type": self._classify_token(token_name)
            }
            active_pairs.append(pair_info)
        
        # Add stablecoin pairs
        for token, issuers in self.additional_tokens.items():
            if token in ["USD", "USDT"]:  # Stablecoins
                for issuer_name, issuer_address in issuers.items():
                    pair_info = {
                        "symbol": f"{token}-{issuer_name}",
                        "base": "XRP",
                        "quote": token,
                        "quote_issuer": issuer_address,
                        "issuer_name": issuer_name,
                        "type": "stablecoin"
                    }
                    active_pairs.append(pair_info)
        
        return active_pairs
    
    def _classify_token(self, token_name: str) -> str:
        """Classify token type based on name"""
        meme_tokens = ["BEAR", "FML", "CULT", "OBEY", "POSSE", "XJOY"]
        stablecoins = ["RLUSD", "USD", "USDT"]
        
        if token_name in meme_tokens:
            return "meme"
        elif token_name in stablecoins:
            return "stablecoin"
        else:
            return "token"
    
    async def fetch_all_pairs_data(
        self,
        days: int = 180,  # 6 months
        pairs: Optional[List[Dict]] = None
    ) -> Dict[str, pd.DataFrame]:
        """Fetch data for all specified pairs"""
        if pairs is None:
            pairs = await self.discover_active_pairs()
        
        all_data = {}
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        for pair in pairs:
            try:
                base = pair.get("base", "XRP")
                base_issuer = pair.get("base_issuer")
                quote = pair.get("quote", "XRP")
                quote_issuer = pair.get("quote_issuer")
                
                pair_key = f"{base}/{quote}"
                if base_issuer:
                    pair_key = f"{base}:{base_issuer[-8:]}/{quote}"
                if quote_issuer:
                    pair_key = f"{base}/{quote}:{quote_issuer[-8:]}"
                
                logger.info(f"Fetching data for {pair_key}")
                
                df = await self.fetch_dex_trades(
                    base, base_issuer,
                    quote, quote_issuer,
                    start_time, end_time
                )
                
                if not df.empty:
                    all_data[pair_key] = df
                    logger.info(f"Fetched {len(df)} records for {pair_key}")
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching pair {pair}: {e}")
        
        return all_data
    
    async def save_historical_data(
        self,
        data: Dict[str, pd.DataFrame],
        base_path: str = "data/xrpl_dex"
    ):
        """Save historical data to files"""
        import os
        os.makedirs(base_path, exist_ok=True)
        
        for pair_key, df in data.items():
            # Clean pair key for filename
            filename = pair_key.replace("/", "_").replace(":", "-")
            filepath = os.path.join(base_path, f"{filename}.csv")
            
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {len(df)} records to {filepath}")
            
            # Also save in parquet for better compression
            parquet_path = os.path.join(base_path, f"{filename}.parquet")
            df.to_parquet(parquet_path, index=False)
    
    async def create_ml_dataset(
        self,
        data: Dict[str, pd.DataFrame],
        features: List[str] = None
    ) -> pd.DataFrame:
        """Create dataset suitable for ML training"""
        if features is None:
            features = [
                "returns_1h", "returns_24h", "returns_7d",
                "volume_ratio", "price_momentum",
                "volatility_1d", "volatility_7d",
                "rsi", "macd", "bollinger_position"
            ]
        
        ml_data = []
        
        for pair_key, df in data.items():
            if df.empty:
                continue
            
            # Add technical indicators
            df = self._add_technical_indicators(df)
            
            # Add pair identifier
            df["pair"] = pair_key
            
            # Add features for ML
            df = self._create_ml_features(df)
            
            ml_data.append(df)
        
        # Combine all pairs
        if ml_data:
            combined_df = pd.concat(ml_data, ignore_index=True)
            return combined_df
        else:
            return pd.DataFrame()
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        # Ensure we have OHLCV data
        if "close" not in df.columns:
            return df
        
        # Simple Moving Averages
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        
        # Exponential Moving Averages
        df["ema_12"] = df["close"].ewm(span=12).mean()
        df["ema_26"] = df["close"].ewm(span=26).mean()
        
        # MACD
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        
        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
        
        # Volume indicators
        df["volume_sma"] = df["base_volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["base_volume"] / df["volume_sma"]
        
        return df
    
    def _create_ml_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for machine learning"""
        # Price returns
        df["returns_1h"] = df["close"].pct_change(1)
        df["returns_24h"] = df["close"].pct_change(24)
        df["returns_7d"] = df["close"].pct_change(24 * 7)
        
        # Volatility
        df["volatility_1d"] = df["returns_1h"].rolling(window=24).std()
        df["volatility_7d"] = df["returns_1h"].rolling(window=24*7).std()
        
        # Price momentum
        df["price_momentum"] = df["close"] / df["close"].shift(24) - 1
        
        # Target variable (next hour return)
        df["target"] = df["returns_1h"].shift(-1)
        
        # Classification target (up/down)
        df["target_class"] = (df["target"] > 0).astype(int)
        
        return df