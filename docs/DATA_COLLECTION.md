# Data Collection Guide

## Overview

The XRPL Trading Bot includes comprehensive data collection capabilities for both DEX trading data and AMM pool information. This guide explains how to collect, store, and prepare data for backtesting and AI model training.

## Data Sources

### 1. Direct XRPL Data
- **AMM Pool States**: Real-time liquidity, reserves, and pricing
- **DEX Trades**: Historical trade data from order book transactions
- **Account Transactions**: Full transaction history including metadata
- **Order Books**: Current DEX order book snapshots
- **Account Information**: Token balances and trading history

### 2. External Data Providers
- **Bithomp API**: Historical price data
- **XRPScan**: Transaction and volume data
- **XRPLorer**: Additional market metrics

### 3. Real-time Collection
- **WebSocket Monitoring**: Live transaction stream from XRPL
- **AMM State Tracking**: Captures pool reserves after every trade
- **Automatic Backfill**: Gap detection and historical data recovery
- **Continuous Updates**: 24/7 data collection with systemd service

## Available Tokens

The bot tracks the following tokens (from `src/config/tokens.json`):

### Stablecoins
- **RLUSD**: Ripple's official USD stablecoin

### Meme/Community Tokens
- **BEAR**: Bear-themed meme token
- **FML**: Community token
- **CULT**: Cult-themed token
- **OBEY**: Meme token
- **POSSE**: Community token
- **XJOY**: Entertainment token

### Other Tokens
- **UGA**: Utility token
- **GNOSIS**: Prediction/oracle token
- **FARM**: DeFi/yield farming token

## Quick Start

### Real-time Collection (Recommended)
```bash
# Start real-time collection with automatic backfill
python start_realtime_collection.py

# Or install as systemd service for 24/7 operation
sudo ./setup_systemd_service.sh

# Monitor collection status
python monitor_collection.py
```

### Historical Data Collection
```bash
# Collect full transaction history (last 30 days)
python collect_full_history.py --days 30

# Collect specific token history
python collect_full_history.py --token RLUSD --days 30
```

### Legacy Collection Methods
```bash
# Get snapshot of all AMM pools
python scripts/collect_historical_data.py --mode amm

# Monitor AMMs for 24 hours (5-minute intervals)
python scripts/collect_historical_data.py --mode amm --amm-hours 24 --amm-interval 5
```

## Real-time Collection System

### Architecture
The real-time collection system consists of:

1. **RealtimeCollector** (`src/realtime/realtime_collector.py`)
   - WebSocket connection to XRPL
   - Subscribes to AMM pool accounts
   - Processes transactions in real-time
   - Tracks last processed ledger
   - Captures AMM state changes

2. **AMMStateTracker** (`src/realtime/amm_state_tracker.py`)
   - Monitors AMM pool state changes
   - Processes AMMDeposit, AMMWithdraw, and swap transactions
   - Stores pool reserves after each change
   - Takes periodic snapshots for trend analysis

3. **CollectionManager** (`src/realtime/collection_manager.py`)
   - Coordinates real-time and historical collectors
   - Performs gap detection and backfill
   - Runs periodic health checks
   - Manages AMM snapshot scheduling
   - Handles graceful shutdown

4. **Monitoring Dashboard** (`monitor_collection.py`)
   - Rich terminal UI
   - Shows collection status per token
   - Displays transaction rates
   - Shows AMM snapshot counts and latest timestamp
   - Identifies gaps in data

### Running as a Service

#### Install systemd service:
```bash
sudo ./setup_systemd_service.sh
```

#### Service management:
```bash
# Check status
sudo systemctl status xrpl-realtime-collector

# View logs
sudo journalctl -u xrpl-realtime-collector -f

# Stop/Start/Restart
sudo systemctl stop xrpl-realtime-collector
sudo systemctl start xrpl-realtime-collector
sudo systemctl restart xrpl-realtime-collector

# Disable autostart
sudo systemctl disable xrpl-realtime-collector
```

### Gap Detection and Backfill
The system automatically:
- Detects gaps when collector was offline
- Backfills missing transactions up to 30 days
- Handles XRPL's ~32,000 ledger history limit
- Works around websocket payload limits with batching

### AMM State Tracking
Real-time monitoring of AMM pool states:
- **Transaction-level tracking**: Captures pool state after every swap, deposit, or withdrawal
- **Periodic snapshots**: Regular snapshots every 30 minutes for trend analysis
- **State change detection**: Monitors for significant pool changes (>1% by default)
- **Complete history**: Tracks reserves, prices, TVL, and LP token supply over time
- **Efficient storage**: Deduplicates snapshots at same ledger index

## Data Collection Scripts

### 1. AMM Pool Monitoring
```python
from src.data.amm_fetcher import AMMDataFetcher

# Initialize fetcher
fetcher = AMMDataFetcher(settings)
await fetcher.connect()

# Get current pool state
metrics = await fetcher.calculate_pool_metrics(amm_address)
print(f"Price: {metrics['price']}")
print(f"TVL: {metrics['tvl_xrp']} XRP")

# Monitor pools
data = await fetcher.monitor_amm_pools(
    interval_seconds=300,  # 5 minutes
    duration_hours=24
)
```

### 2. Historical Data Collection
```python
from src.data.xrpl_dex_fetcher import XRPLDexDataFetcher

# Initialize fetcher
fetcher = XRPLDexDataFetcher(settings)
await fetcher.connect()

# Discover active pairs
pairs = await fetcher.discover_active_pairs()

# Fetch historical data
all_data = await fetcher.fetch_all_pairs_data(days=180)

# Create ML dataset
ml_dataset = await fetcher.create_ml_dataset(all_data)
```

### 3. External Data Sources
```python
from src.data.external_data_sources import DataAggregator

# Initialize aggregator
aggregator = DataAggregator()

# Prepare training data
training_data = await aggregator.prepare_training_data(
    tokens,
    lookback_days=180
)
```

## Data Storage

### Database Schema
The system uses PostgreSQL with the following main tables:

#### Core Tables
- **assets**: Token and LP token definitions
- **token_transactions**: All token transfers and trades
- **dex_trades**: DEX order book trades
- **amm_snapshots**: Historical AMM pool states
- **amm_positions**: LP token positions and P&L tracking
- **data_collection_logs**: Collection progress and health

#### Data Fields
- **TokenTransaction**:
  - `transaction_hash`: Unique XRPL transaction ID
  - `ledger_index`: XRPL ledger number
  - `timestamp`: Transaction time
  - `wallet_address`: Account involved
  - `currency`, `issuer`: Token identification
  - `amount`: Transaction amount
  - `transaction_type`: payment, dex_trade, amm_deposit, etc.
  - `is_receive`: Direction of transfer
  - `xrp_price`, `xrp_value`: Price data if available

- **AMMSnapshot** (NEW):
  - `timestamp`: When the snapshot was taken
  - `ledger_index`: XRPL ledger number  
  - `amm_address`: AMM pool account
  - `asset1_amount`, `asset2_amount`: Current pool reserves
  - `price_asset2_per_asset1`: Current exchange rate
  - `k_constant`: Product of reserves (x*y=k)
  - `tvl_xrp`: Total value locked in XRP
  - `lp_token_supply`: Total LP tokens
  - Real-time capture of every pool state change

### Directory Structure
```
data/
├── xrpl_dex/          # DEX trading data exports
│   ├── XRP_USD.csv
│   ├── BEAR_XRP.csv
│   └── ml_dataset.parquet
├── amm/               # AMM pool data exports
│   ├── BEAR_amm_data.csv
│   ├── RLUSD_amm_data.csv
│   └── *.parquet
└── training/          # Prepared ML datasets
    ├── BEAR_training_data.csv
    └── features/
```

### File Formats
- **Database**: PostgreSQL for real-time data
- **CSV**: Exported data for analysis
- **Parquet**: Compressed exports for large datasets
- **JSON**: Configuration and metadata

## Data Fields

### AMM Pool Data
- `timestamp`: Data collection time
- `xrp_reserve`: XRP in the pool
- `token_reserve`: Token amount in pool
- `price`: Current token price in XRP
- `k_constant`: Constant product (x*y=k)
- `tvl_xrp`: Total value locked in XRP

### Trading Data
- `timestamp`: Trade/candle time
- `open`, `high`, `low`, `close`: OHLC data
- `volume`: Trading volume
- `base_volume`: Volume in base currency
- `quote_volume`: Volume in quote currency

### ML Features
- `returns_1h`, `returns_24h`: Price returns
- `volatility_7d`: 7-day volatility
- `volume_ratio`: Current vs average volume
- `rsi`, `macd`: Technical indicators
- `ma_ratios`: Price to moving average ratios

## Data Quality Considerations

### XRPL Limitations
1. **No Native Historical API**: XRPL doesn't provide extensive historical data
2. **Limited Aggregation**: Must collect data over time or use third-party services
3. **Rate Limits**: External APIs have usage limits

### Best Practices
1. **Start Collection Early**: Begin collecting data as soon as possible
2. **Use Multiple Sources**: Combine data from different providers
3. **Validate Data**: Check for gaps and anomalies
4. **Store Raw Data**: Keep original data before processing
5. **Incremental Updates**: Append new data rather than re-fetching

## Example Workflows

### 1. Prepare Backtesting Data
```bash
# Collect current state
python scripts/collect_historical_data.py --mode amm

# Run backtest with collected data
python backtest.py --use-cache --days 30
```

### 2. Prepare AI Training Data
```bash
# Collect comprehensive dataset
python scripts/collect_historical_data.py --mode all

# Process for ML
python -c "
from src.data.external_data_sources import DataAggregator
import asyncio

async def prepare():
    aggregator = DataAggregator()
    data = await aggregator.prepare_training_data(tokens, 180)
    return data

asyncio.run(prepare())
"
```

### 3. Real-time Monitoring
```python
# Real-time collection is now handled by the service
# To programmatically access real-time data:

from src.database.models import TokenTransaction, get_session
from sqlalchemy import select, func
from datetime import datetime, timedelta

# Get recent transactions
session = get_session(engine)
since = datetime.utcnow() - timedelta(hours=1)

recent_txs = session.execute(
    select(TokenTransaction)
    .where(TokenTransaction.timestamp >= since)
    .order_by(TokenTransaction.timestamp.desc())
).scalars().all()

# Get transaction rates
rates = session.execute(
    select(
        TokenTransaction.wallet_address,
        func.count(TokenTransaction.id).label('count')
    )
    .where(TokenTransaction.timestamp >= since)
    .group_by(TokenTransaction.wallet_address)
).all()
```

## Troubleshooting

### "No historical data available"
- XRPL doesn't provide historical DEX data natively
- Use external providers or collect data over time
- Start with AMM monitoring for current data

### "Rate limit exceeded"
- Reduce request frequency
- Use caching for repeated queries
- Implement exponential backoff

### "Connection timeout"
- Check network connectivity
- Verify XRPL node URLs
- Try alternative nodes

## Advanced Usage

### Custom Data Collection
```python
# Access collected data for analysis
from src.database.storage import DataStorage

storage = DataStorage()

# Get token transactions
transactions = storage.get_token_transactions(
    currency="RLUSD",
    start_date=datetime.now() - timedelta(days=7)
)

# Get AMM snapshots
snapshots = storage.get_amm_snapshots(
    amm_address=tokens["RLUSD"]["amm_address"],
    start_date=datetime.now() - timedelta(days=30)
)
```

### Data Pipeline
1. **Real-time Collection**: WebSocket subscription to XRPL
2. **Transaction Processing**: Extract balance changes from metadata
3. **Gap Detection**: Identify missing ledgers
4. **Backfill**: Fetch missing historical data
5. **Storage**: PostgreSQL with indexed queries
6. **Export**: Generate CSV/Parquet for analysis

### Performance Considerations
- **Batch Processing**: Handles high-volume tokens like RLUSD
- **Concurrent Collection**: Multiple tokens monitored in parallel
- **Automatic Reconnection**: Handles network interruptions
- **Resource Limits**: Configurable memory and connection limits

## Next Steps

1. **Install Real-time Collector** - Set up the systemd service for 24/7 collection
2. **Monitor Collection Health** - Use the monitoring dashboard to track progress
3. **Export Historical Data** - Generate datasets for backtesting and ML training
4. **Optimize Queries** - Add database indexes for your specific use cases
5. **Prepare for AI** - Create feature-rich datasets from collected transactions

## Collected Data Statistics

As of the latest collection:
- **Total Transactions**: 66,000+ across all tokens
- **Most Active Token**: RLUSD with 31,000+ transactions
- **Collection Rate**: ~1-10 transactions per minute per token
- **Historical Depth**: Up to 30 days (XRPL limit: ~32,000 ledgers)