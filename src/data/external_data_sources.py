"""
External data sources for XRPL historical data

Since XRPL doesn't provide extensive historical data through standard APIs,
this module interfaces with various third-party services.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import aiohttp
from loguru import logger
import json


class XRPLDataSources:
    """Interface to various XRPL data providers"""
    
    def __init__(self):
        # Available data sources
        self.sources = {
            "bithomp": {
                "base_url": "https://api.bithomp.com/api/v2",
                "requires_auth": False
            },
            "xrpscan": {
                "base_url": "https://api.xrpscan.com/api/v1",
                "requires_auth": False
            },
            "xrplorer": {
                "base_url": "https://api.xrplorer.com",
                "requires_auth": False
            }
        }
        
        # Rate limiting
        self.rate_limits = {
            "bithomp": {"calls": 10, "period": 60},  # 10 calls per minute
            "xrpscan": {"calls": 30, "period": 60},  # 30 calls per minute
            "xrplorer": {"calls": 60, "period": 60}   # 60 calls per minute
        }
    
    async def fetch_bithomp_data(
        self,
        token_currency: str,
        token_issuer: str,
        days: int = 30
    ) -> pd.DataFrame:
        """Fetch data from Bithomp API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get price history
                url = f"{self.sources['bithomp']['base_url']}/price"
                params = {
                    "currency": token_currency,
                    "issuer": token_issuer,
                    "days": days
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_bithomp_data(data)
                    else:
                        logger.warning(f"Bithomp API returned {response.status}")
                        return pd.DataFrame()
                        
        except Exception as e:
            logger.error(f"Error fetching Bithomp data: {e}")
            return pd.DataFrame()
    
    def _parse_bithomp_data(self, data: Dict) -> pd.DataFrame:
        """Parse Bithomp response into DataFrame"""
        if "price" not in data:
            return pd.DataFrame()
        
        prices = []
        for point in data["price"]:
            prices.append({
                "timestamp": datetime.fromtimestamp(point["t"]),
                "price": float(point["v"]),
                "volume": float(point.get("vol", 0))
            })
        
        return pd.DataFrame(prices)
    
    async def fetch_xrpl_orderbook_data(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str]
    ) -> Dict[str, Any]:
        """Fetch current orderbook data"""
        try:
            # Use XRP Toolkit API or similar
            async with aiohttp.ClientSession() as session:
                # Construct pair identifier
                base = f"{base_currency}+{base_issuer}" if base_issuer else "XRP"
                quote = f"{quote_currency}+{quote_issuer}" if quote_issuer else "XRP"
                
                # This is a placeholder - actual implementation would use real endpoints
                url = f"https://api.xrptoolkit.com/v1/orderbook/{base}/{quote}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {}
                        
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}
    
    async def fetch_onchain_metrics(
        self,
        token_address: str,
        amm_address: str
    ) -> Dict[str, Any]:
        """Fetch on-chain metrics for analysis"""
        metrics = {
            "holder_count": 0,
            "total_supply": 0,
            "circulating_supply": 0,
            "amm_tvl": 0,
            "24h_volume": 0,
            "7d_volume": 0
        }
        
        # This would query various endpoints to gather metrics
        # Implementation depends on available APIs
        
        return metrics
    
    async def create_comprehensive_dataset(
        self,
        tokens: Dict[str, Any],
        days: int = 180
    ) -> pd.DataFrame:
        """Create comprehensive dataset from multiple sources"""
        all_data = []
        
        for token_name, token_info in tokens.items():
            logger.info(f"Fetching data for {token_name}")
            
            # Fetch from different sources
            token_data = {
                "token": token_name,
                "issuer": token_info["token_address"],
                "amm_address": token_info["amm_address"]
            }
            
            # Get price data
            price_data = await self.fetch_bithomp_data(
                token_info["token_code"],
                token_info["token_address"],
                days
            )
            
            if not price_data.empty:
                token_data["price_history"] = price_data
            
            # Get on-chain metrics
            metrics = await self.fetch_onchain_metrics(
                token_info["token_address"],
                token_info["amm_address"]
            )
            token_data.update(metrics)
            
            all_data.append(token_data)
            
            # Rate limiting
            await asyncio.sleep(6)  # 10 requests per minute for Bithomp
        
        return self._combine_data(all_data)
    
    def _combine_data(self, data_list: List[Dict]) -> pd.DataFrame:
        """Combine data from multiple sources into single DataFrame"""
        combined = []
        
        for token_data in data_list:
            if "price_history" in token_data and isinstance(token_data["price_history"], pd.DataFrame):
                df = token_data["price_history"].copy()
                df["token"] = token_data["token"]
                df["issuer"] = token_data["issuer"]
                df["amm_address"] = token_data["amm_address"]
                
                # Add metrics
                for key, value in token_data.items():
                    if key not in ["price_history", "token", "issuer", "amm_address"]:
                        df[key] = value
                
                combined.append(df)
        
        if combined:
            return pd.concat(combined, ignore_index=True)
        else:
            return pd.DataFrame()


class DataAggregator:
    """Aggregates data from multiple sources for comprehensive analysis"""
    
    def __init__(self):
        self.external_sources = XRPLDataSources()
    
    async def prepare_training_data(
        self,
        tokens: Dict[str, Any],
        lookback_days: int = 180
    ) -> Dict[str, pd.DataFrame]:
        """Prepare data for AI/ML training"""
        
        logger.info("Preparing training data...")
        
        # Fetch comprehensive dataset
        raw_data = await self.external_sources.create_comprehensive_dataset(
            tokens, lookback_days
        )
        
        if raw_data.empty:
            logger.warning("No data fetched")
            return {}
        
        # Process data for each token
        training_data = {}
        
        for token in tokens.keys():
            token_data = raw_data[raw_data["token"] == token].copy()
            
            if token_data.empty:
                continue
            
            # Add technical indicators
            token_data = self._add_features(token_data)
            
            # Create sequences for time series models
            token_data = self._create_sequences(token_data)
            
            training_data[token] = token_data
        
        return training_data
    
    def _add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features for ML models"""
        if "price" not in df.columns:
            return df
        
        # Price-based features
        df["returns"] = df["price"].pct_change()
        df["log_returns"] = df["price"].apply(lambda x: pd.np.log(x) if x > 0 else 0).diff()
        
        # Moving averages
        for window in [7, 14, 30]:
            df[f"ma_{window}"] = df["price"].rolling(window=window).mean()
            df[f"ma_{window}_ratio"] = df["price"] / df[f"ma_{window}"]
        
        # Volatility
        df["volatility_7d"] = df["returns"].rolling(window=7).std()
        df["volatility_30d"] = df["returns"].rolling(window=30).std()
        
        # Volume features
        if "volume" in df.columns:
            df["volume_ma_7"] = df["volume"].rolling(window=7).mean()
            df["volume_ratio"] = df["volume"] / df["volume_ma_7"]
        
        # Time features
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month
        
        return df
    
    def _create_sequences(
        self,
        df: pd.DataFrame,
        sequence_length: int = 24
    ) -> pd.DataFrame:
        """Create sequences for time series prediction"""
        # This would create sequences for LSTM/GRU models
        # For now, just return the dataframe with forward-looking targets
        
        # Create prediction targets
        for horizon in [1, 6, 24]:  # 1h, 6h, 24h
            df[f"target_{horizon}h"] = df["price"].shift(-horizon)
            df[f"target_return_{horizon}h"] = df["returns"].shift(-horizon)
        
        return df


# Example usage for documentation
async def example_usage():
    """Example of how to use the data sources"""
    
    # Load token configuration
    with open("src/config/tokens.json", "r") as f:
        tokens = json.load(f)
    
    # Initialize aggregator
    aggregator = DataAggregator()
    
    # Prepare training data
    training_data = await aggregator.prepare_training_data(
        tokens,
        lookback_days=30  # Start with 30 days for testing
    )
    
    # Save training data
    for token_name, df in training_data.items():
        if not df.empty:
            df.to_csv(f"data/training/{token_name}_training_data.csv", index=False)
            logger.info(f"Saved {len(df)} records for {token_name}")


if __name__ == "__main__":
    asyncio.run(example_usage())