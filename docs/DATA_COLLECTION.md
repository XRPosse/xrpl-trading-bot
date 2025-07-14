# Data Collection Guide

## Overview

The XRPL Trading Bot includes comprehensive data collection capabilities for both DEX trading data and AMM pool information. This guide explains how to collect, store, and prepare data for backtesting and AI model training.

## Data Sources

### 1. Direct XRPL Data
- **AMM Pool States**: Real-time liquidity, reserves, and pricing
- **Order Books**: Current DEX order book snapshots
- **Account Information**: Token balances and trading history

### 2. External Data Providers
- **Bithomp API**: Historical price data
- **XRPScan**: Transaction and volume data
- **XRPLorer**: Additional market metrics

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

### Collect Current AMM Data
```bash
# Get snapshot of all AMM pools
python scripts/collect_historical_data.py --mode amm

# Monitor AMMs for 24 hours (5-minute intervals)
python scripts/collect_historical_data.py --mode amm --amm-hours 24 --amm-interval 5
```

### Collect Historical Data
```bash
# Collect all available historical data
python scripts/collect_historical_data.py --mode all --dex-days 180
```

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

### Directory Structure
```
data/
├── xrpl_dex/          # DEX trading data
│   ├── XRP_USD.csv
│   ├── BEAR_XRP.csv
│   └── ml_dataset.parquet
├── amm/               # AMM pool data
│   ├── BEAR_amm_data.csv
│   ├── RLUSD_amm_data.csv
│   └── *.parquet
└── training/          # Prepared ML datasets
    ├── BEAR_training_data.csv
    └── features/
```

### File Formats
- **CSV**: Human-readable, good for analysis
- **Parquet**: Compressed, efficient for large datasets
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
# Monitor specific token
async def monitor_token(token_name):
    fetcher = AMMDataFetcher(settings)
    await fetcher.connect()
    
    while True:
        metrics = await fetcher.calculate_pool_metrics(
            tokens[token_name]["amm_address"]
        )
        print(f"{token_name}: {metrics['price']:.6f} XRP")
        await asyncio.sleep(60)
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
# Collect specific metrics
async def collect_liquidity_events():
    # Monitor for large liquidity changes
    # Track impermanent loss
    # Analyze fee generation
    pass

# High-frequency data
async def collect_hf_data():
    # 1-minute candles
    # Order book snapshots
    # Trade-by-trade data
    pass
```

### Data Pipeline
1. **Collection**: Raw data from various sources
2. **Validation**: Check completeness and accuracy
3. **Transformation**: Add features and indicators
4. **Storage**: Efficient storage formats
5. **Analysis**: Statistical analysis and visualization

## Next Steps

1. **Start collecting data immediately** - Historical data accumulates over time
2. **Set up automated collection** - Use cron jobs or systemd timers
3. **Monitor data quality** - Regular validation checks
4. **Optimize storage** - Compress old data, use appropriate formats
5. **Prepare for AI** - Create feature-rich datasets for model training