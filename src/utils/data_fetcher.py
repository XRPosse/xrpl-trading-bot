import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import ccxt.async_support as ccxt
from loguru import logger
import aiohttp
import json
from decimal import Decimal

from src.config.settings import Settings


class DataFetcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.exchange = None
        self._init_exchange()
    
    def _init_exchange(self):
        """Initialize exchange for historical data"""
        # Using Binance as it has good XRP/USDT historical data
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
    
    async def fetch_ohlcv(
        self,
        symbol: str = "XRP/USDT",
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from exchange
        
        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            since: Start datetime
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            if since:
                since_ms = int(since.timestamp() * 1000)
            else:
                since_ms = None
            
            logger.info(f"Fetching {symbol} {timeframe} data")
            
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe,
                since=since_ms,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Fetched {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise
    
    async def fetch_historical_data(
        self,
        symbol: str = "XRP/USDT",
        timeframe: str = "1h",
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """
        Fetch historical data for a date range
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_date: Start date
            end_date: End date
        
        Returns:
            Complete DataFrame for the date range
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        all_data = []
        current_date = start_date
        
        # Calculate candle duration
        timeframe_minutes = self._timeframe_to_minutes(timeframe)
        batch_size = 1000  # Max candles per request
        
        while current_date < end_date:
            try:
                # Fetch batch
                df = await self.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_date,
                    limit=batch_size
                )
                
                if df.empty:
                    break
                
                # Filter by end date
                df = df[df['timestamp'] <= end_date]
                
                if not df.empty:
                    all_data.append(df)
                
                # Move to next batch
                last_timestamp = df['timestamp'].max()
                current_date = last_timestamp + timedelta(minutes=timeframe_minutes)
                
                # Rate limit
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching batch at {current_date}: {e}")
                await asyncio.sleep(5)  # Wait before retry
                continue
        
        if all_data:
            # Combine all data
            result = pd.concat(all_data, ignore_index=True)
            
            # Remove duplicates
            result = result.drop_duplicates(subset=['timestamp'])
            
            # Sort by timestamp
            result = result.sort_values('timestamp')
            
            logger.info(f"Fetched total {len(result)} candles from {result['timestamp'].min()} to {result['timestamp'].max()}")
            
            return result
        else:
            return pd.DataFrame()
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        return mapping.get(timeframe, 60)
    
    async def fetch_xrpl_dex_data(
        self,
        base: str = "XRP",
        quote: str = "USD",
        interval: str = "hour",
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch data directly from XRPL DEX
        Note: This is a placeholder - would need XRPL data service API
        """
        logger.warning("Direct XRPL DEX historical data not implemented - using exchange data")
        # In production, you'd use XRPL data services like:
        # - XRPL Data API
        # - Bithomp API
        # - XRPScan API
        return pd.DataFrame()
    
    async def save_data(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file"""
        data_dir = "data"
        import os
        os.makedirs(data_dir, exist_ok=True)
        
        filepath = os.path.join(data_dir, filename)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} rows to {filepath}")
    
    async def load_data(self, filename: str) -> pd.DataFrame:
        """Load DataFrame from CSV file"""
        import os
        filepath = os.path.join("data", filename)
        
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Loaded {len(df)} rows from {filepath}")
            return df
        else:
            logger.warning(f"File not found: {filepath}")
            return pd.DataFrame()
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()