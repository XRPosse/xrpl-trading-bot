# Data Collection Improvements

This document describes the improvements made to address the three major issues identified with the data collection system.

## Issues Addressed

### 1. LP Token Asset Tracking

**Problem**: The assets table was missing LP token assets.

**Solution**: 
- Enhanced the `Asset` model with:
  - `asset_type` field to distinguish between regular tokens and LP tokens
  - `pool_asset1_id` and `pool_asset2_id` foreign keys to link LP tokens to their underlying assets
  - Relationships to track the pool composition

- Added LP token storage in the collection process
- LP tokens are now properly identified and stored with their AMM pool relationships

### 2. DEX Data Collection

**Problem**: Only AMM data was being collected, no DEX (order book) data.

**Solution**:
- Created `DEXDataFetcher` class that:
  - Fetches historical OfferCreate transactions
  - Extracts trade details from transaction metadata
  - Captures both maker and taker sides of trades
  - Stores price, volume, and participant information

- Added `DEXTrade` model to store:
  - Trade timestamps and ledger indices
  - Assets traded (gets/pays currencies and amounts)
  - Calculated prices
  - Transaction metadata

- Implemented orderbook snapshot functionality for current market depth

### 3. Historical Data Collection

**Problem**: No historical AMM data was being collected.

**Solution**:
- Implemented snapshot-based approach (inspired by UGA wallet):
  - `HistoricalDataCollector` class that takes AMM snapshots at regular intervals
  - Estimates historical ledger indices based on timestamps
  - Fetches pool states at specific ledgers going back in time

- Created `AMMSnapshot` model to store historical states:
  - Pool reserves at each snapshot
  - LP token supply
  - Calculated metrics (K constant, price, TVL)
  - Ledger index for exact temporal ordering

- Added transaction metadata processing:
  - `MetadataProcessor` extracts token transfers from transaction metadata
  - Identifies trades, AMM deposits/withdrawals, and balance changes
  - Stores in `TokenTransaction` table for comprehensive tracking

## Key Components

### 1. Database Models

```python
# Asset tracking with LP token support
class Asset:
    - currency_code
    - issuer
    - asset_type ('token' or 'lp_token')
    - pool_asset1_id (for LP tokens)
    - pool_asset2_id (for LP tokens)

# DEX trade history
class DEXTrade:
    - timestamp, ledger_index
    - gets/pays currencies and amounts
    - calculated price
    - transaction details

# Historical AMM snapshots
class AMMSnapshot:
    - timestamp, ledger_index
    - asset reserves
    - LP token supply
    - calculated metrics (K, price, TVL)

# Token transfers from metadata
class TokenTransaction:
    - wallet_address, counterparty
    - currency, amount
    - transaction type
    - is_receive flag
```

### 2. Data Collection Process

1. **LP Token Discovery**:
   - Identifies LP tokens from AMM pool data
   - Links them to underlying assets
   - Stores with proper relationships

2. **DEX Trade Collection**:
   - Fetches account transactions
   - Filters for OfferCreate types
   - Extracts execution details from metadata
   - Calculates prices and volumes

3. **Historical AMM Snapshots**:
   - Estimates ledger indices for past dates
   - Fetches pool states at regular intervals
   - Stores complete pool information
   - Tracks changes over time

4. **Metadata Processing**:
   - Processes all transaction types
   - Extracts balance changes
   - Identifies token transfers
   - Tracks AMM activity

## Usage

```python
# Run historical data collection
python src/collect_historical_data.py

# The script will:
# 1. Load token configuration
# 2. Store LP token information
# 3. Collect 6 months of AMM snapshots (every 4 hours)
# 4. Collect DEX trades from relevant accounts
# 5. Process transaction metadata for transfers
```

## Benefits

1. **Complete Asset Tracking**: All assets including LP tokens are properly tracked with relationships
2. **Comprehensive Trade Data**: Both AMM and DEX trades are captured for full market view
3. **Historical Analysis**: 6 months of snapshots enable backtesting and trend analysis
4. **Transaction-Level Detail**: Metadata processing captures all token movements
5. **Efficient Storage**: Deduplication and indexing for fast queries

## Next Steps

1. Implement real-time monitoring for live updates
2. Add data validation and cleaning
3. Create aggregation views for faster analysis
4. Build export functionality for AI training datasets
5. Add support for more complex AMM operations (voting, auction)