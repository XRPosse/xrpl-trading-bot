"""
Database models for storing XRPL trading data
"""

from sqlalchemy import create_engine, Column, String, DateTime, Numeric, Integer, JSON, Index, Float, Boolean, ForeignKey, UniqueConstraint, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Asset(Base):
    """Assets including tokens and LP tokens"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True)
    currency_code = Column(String(40), nullable=False)
    issuer = Column(String(34))
    name = Column(String(255))
    symbol = Column(String(40))
    decimals = Column(Integer, default=15)
    amm_address = Column(String(34))
    asset_type = Column(String(20), default='token')  # 'token', 'lp_token'
    pool_asset1_id = Column(Integer, ForeignKey('assets.id'))  # For LP tokens
    pool_asset2_id = Column(Integer, ForeignKey('assets.id'))  # For LP tokens
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships for LP tokens
    pool_asset1 = relationship("Asset", foreign_keys=[pool_asset1_id], remote_side=[id])
    pool_asset2 = relationship("Asset", foreign_keys=[pool_asset2_id], remote_side=[id])
    
    __table_args__ = (
        UniqueConstraint('currency_code', 'issuer', name='_currency_issuer_uc'),
    )


class DEXTrade(Base):
    """DEX trade history"""
    __tablename__ = "dex_trades"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    ledger_index = Column(Integer, nullable=False, index=True)
    transaction_hash = Column(String(64), nullable=False, unique=True)
    
    # Trade details
    account = Column(String(34), nullable=False)
    offer_sequence = Column(Integer)
    
    # Assets traded
    gets_currency = Column(String(40), nullable=False)
    gets_issuer = Column(String(34))
    gets_amount = Column(Numeric(40, 20), nullable=False)
    
    pays_currency = Column(String(40), nullable=False)
    pays_issuer = Column(String(34))
    pays_amount = Column(Numeric(40, 20), nullable=False)
    
    # Calculated fields
    price = Column(Numeric(20, 8))
    quality = Column(Numeric(20, 8))
    
    # Metadata
    flags = Column(Integer)
    fee_xrp = Column(Numeric(20, 6))
    
    __table_args__ = (
        Index("idx_dex_timestamp", "timestamp"),
        Index("idx_dex_pair", "gets_currency", "pays_currency", "timestamp"),
    )


class AMMSnapshot(Base):
    """Historical AMM pool snapshots"""
    __tablename__ = "amm_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    ledger_index = Column(Integer, nullable=False)
    amm_address = Column(String(34), nullable=False, index=True)
    
    # Pool assets
    asset1_currency = Column(String(40), nullable=False)
    asset1_issuer = Column(String(34))
    asset1_amount = Column(Numeric(40, 20), nullable=False)
    
    asset2_currency = Column(String(40), nullable=False)
    asset2_issuer = Column(String(34))
    asset2_amount = Column(Numeric(40, 20), nullable=False)
    
    # LP token info
    lp_token_currency = Column(String(40), nullable=False)
    lp_token_supply = Column(Numeric(40, 20), nullable=False)
    
    # Pool metrics
    trading_fee = Column(Integer)  # In basis points
    k_constant = Column(Numeric(80, 20))
    price_asset2_per_asset1 = Column(Numeric(20, 8))
    tvl_xrp = Column(Numeric(20, 6))
    
    __table_args__ = (
        Index("idx_amm_snapshot", "amm_address", "timestamp"),
        UniqueConstraint('amm_address', 'ledger_index', name='_amm_ledger_uc'),
    )


class TokenTransaction(Base):
    """Token transfers extracted from transaction metadata"""
    __tablename__ = "token_transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_hash = Column(String(64), nullable=False)
    ledger_index = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Transaction parties
    wallet_address = Column(String(34), nullable=False, index=True)
    counterparty = Column(String(34))
    
    # Token details
    currency = Column(String(40), nullable=False)
    issuer = Column(String(34))
    amount = Column(Numeric(40, 20), nullable=False)
    
    # Transaction type and direction
    transaction_type = Column(String(20), nullable=False)  # payment, dex_trade, amm_deposit, etc.
    is_receive = Column(Boolean, nullable=False)
    
    # Price data (if available)
    xrp_price = Column(Numeric(20, 8))
    xrp_value = Column(Numeric(20, 8))
    
    # Metadata
    fee_xrp = Column(Numeric(20, 6))
    
    __table_args__ = (
        Index("idx_token_tx_wallet", "wallet_address", "timestamp"),
        Index("idx_token_tx_currency", "currency", "issuer", "timestamp"),
    )


class AMMPosition(Base):
    """LP token positions and tracking"""
    __tablename__ = "amm_positions"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(34), nullable=False, index=True)
    amm_address = Column(String(34), nullable=False, index=True)
    
    # Initial deposit
    deposit_tx_hash = Column(String(64), nullable=False)
    deposit_timestamp = Column(DateTime, nullable=False)
    initial_xrp = Column(Numeric(20, 6))
    initial_token = Column(Numeric(40, 20))
    initial_token_currency = Column(String(40), nullable=False)
    initial_token_issuer = Column(String(34))
    
    # LP token details
    lp_tokens_received = Column(Numeric(40, 20), nullable=False)
    initial_pool_share = Column(Numeric(10, 8))
    current_lp_tokens = Column(Numeric(40, 20), nullable=False)
    
    # P&L tracking
    fees_earned_xrp = Column(Numeric(20, 6), default=0)
    impermanent_loss_xrp = Column(Numeric(20, 6), default=0)
    realized_pnl_xrp = Column(Numeric(20, 6), default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_update_timestamp = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('wallet_address', 'amm_address', 'deposit_tx_hash', name='_position_uc'),
    )


class DataCollectionLog(Base):
    """Track data collection progress"""
    __tablename__ = "data_collection_logs"
    
    id = Column(Integer, primary_key=True)
    collection_type = Column(String(50), nullable=False)  # 'historical', 'realtime', etc.
    target = Column(String(100), nullable=False)  # AMM address, trading pair, etc.
    
    # Progress tracking
    start_ledger = Column(Integer)
    end_ledger = Column(Integer)
    last_processed_ledger = Column(Integer)
    
    # Status
    status = Column(String(20), nullable=False, default='pending')  # 'running', 'completed', 'failed', 'active', 'stopped'
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime)
    last_run = Column(DateTime)  # Last time the collector ran
    
    # Metrics
    records_collected = Column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint('collection_type', 'target', name='_collection_target_uc'),
        Index("idx_collection_target", "collection_type", "target"),
    )


class PriceData(Base):
    """Historical price data for trading pairs"""
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    pair = Column(String(50), nullable=False, index=True)
    token = Column(String(20), nullable=False)
    issuer = Column(String(64))
    
    # OHLCV data
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8))
    
    # Additional metrics
    trades_count = Column(Integer)
    vwap = Column(Numeric(20, 8))  # Volume weighted average price
    
    __table_args__ = (
        Index("idx_pair_timestamp", "pair", "timestamp"),
    )


class AMMPoolState(Base):
    """AMM pool state snapshots"""
    __tablename__ = "amm_pool_states"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    amm_address = Column(String(64), nullable=False, index=True)
    token = Column(String(20), nullable=False)
    
    # Pool reserves
    xrp_reserve = Column(Numeric(20, 6), nullable=False)
    token_reserve = Column(Numeric(20, 6), nullable=False)
    
    # Calculated metrics
    price = Column(Numeric(20, 8), nullable=False)
    k_constant = Column(Numeric(40, 6))
    tvl_xrp = Column(Numeric(20, 6))
    
    # Pool parameters
    trading_fee = Column(Float)
    lp_token_supply = Column(Numeric(20, 6))
    
    __table_args__ = (
        Index("idx_amm_timestamp", "amm_address", "timestamp"),
    )


class OrderBookSnapshot(Base):
    """Order book snapshots"""
    __tablename__ = "orderbook_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    pair = Column(String(50), nullable=False, index=True)
    
    # Aggregated data
    best_bid = Column(Numeric(20, 8))
    best_ask = Column(Numeric(20, 8))
    bid_volume = Column(Numeric(20, 8))
    ask_volume = Column(Numeric(20, 8))
    spread = Column(Numeric(20, 8))
    
    # Full order book (JSON)
    bids = Column(JSON)
    asks = Column(JSON)
    
    __table_args__ = (
        Index("idx_orderbook_pair_time", "pair", "timestamp"),
    )


class TradingSignal(Base):
    """Trading signals generated by strategies"""
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    strategy = Column(String(50), nullable=False)
    pair = Column(String(50), nullable=False)
    
    # Signal details
    action = Column(String(10), nullable=False)  # buy, sell, hold
    confidence = Column(Float)
    price = Column(Numeric(20, 8))
    
    # Risk parameters
    stop_loss = Column(Numeric(20, 8))
    take_profit = Column(Numeric(20, 8))
    position_size = Column(Numeric(20, 8))
    
    # Additional context
    indicators = Column(JSON)
    reason = Column(String(500))


class BacktestResult(Base):
    """Backtest results storage"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, nullable=False, default=datetime.now)
    strategy = Column(String(50), nullable=False)
    pair = Column(String(50), nullable=False)
    
    # Test parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Numeric(20, 8))
    
    # Results
    final_balance = Column(Numeric(20, 8))
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    
    # Performance metrics
    total_pnl = Column(Numeric(20, 8))
    total_pnl_percent = Column(Float)
    max_drawdown = Column(Numeric(20, 8))
    max_drawdown_percent = Column(Float)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    
    # Detailed results
    trades = Column(JSON)
    equity_curve = Column(JSON)
    parameters = Column(JSON)


class MLPrediction(Base):
    """Machine learning predictions"""
    __tablename__ = "ml_predictions"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    pair = Column(String(50), nullable=False)
    
    # Predictions
    predicted_price = Column(Numeric(20, 8))
    predicted_direction = Column(String(10))  # up, down
    confidence = Column(Float)
    
    # Actual outcomes (filled later)
    actual_price = Column(Numeric(20, 8))
    actual_direction = Column(String(10))
    error = Column(Float)
    
    # Features used
    features = Column(JSON)


# Database connection management
def get_engine(database_url: str):
    """Create database engine"""
    return create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )


def init_database(database_url: str):
    """Initialize database tables"""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()