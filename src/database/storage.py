"""
Data storage utilities for persisting collected data
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from loguru import logger

from src.database.models import (
    PriceData, AMMPoolState, OrderBookSnapshot,
    TradingSignal, BacktestResult, MLPrediction,
    Asset, DEXTrade, AMMSnapshot, TokenTransaction,
    AMMPosition, DataCollectionLog,
    get_engine, init_database, get_session
)
from src.config.settings import get_settings


class DataStorage:
    """Handles data persistence to PostgreSQL"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = get_engine(self.settings.database_url)
        init_database(self.settings.database_url)
    
    def store_price_data(self, df: pd.DataFrame, pair: str, token: str, issuer: Optional[str] = None):
        """Store price data to database"""
        session = get_session(self.engine)
        
        try:
            records = []
            for _, row in df.iterrows():
                record = PriceData(
                    timestamp=row["timestamp"],
                    pair=pair,
                    token=token,
                    issuer=issuer,
                    open=row.get("open", row.get("price", 0)),
                    high=row.get("high", row.get("price", 0)),
                    low=row.get("low", row.get("price", 0)),
                    close=row.get("close", row.get("price", 0)),
                    volume=row.get("volume", 0),
                    trades_count=row.get("trades_count"),
                    vwap=row.get("vwap")
                )
                records.append(record)
            
            session.bulk_save_objects(records)
            session.commit()
            logger.info(f"Stored {len(records)} price records for {pair}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing price data: {e}")
            raise
        finally:
            session.close()
    
    def store_amm_state(self, state_data: Dict[str, Any]):
        """Store AMM pool state"""
        session = get_session(self.engine)
        
        try:
            state = AMMPoolState(
                timestamp=state_data["timestamp"],
                amm_address=state_data["amm_address"],
                token=state_data["token"],
                xrp_reserve=state_data["xrp_reserve"],
                token_reserve=state_data["token_reserve"],
                price=state_data["price"],
                k_constant=state_data.get("k_constant"),
                tvl_xrp=state_data.get("tvl_xrp"),
                trading_fee=state_data.get("trading_fee"),
                lp_token_supply=state_data.get("lp_token_supply")
            )
            
            session.add(state)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing AMM state: {e}")
            raise
        finally:
            session.close()
    
    def store_amm_states_bulk(self, states: List[Dict[str, Any]]):
        """Store multiple AMM states efficiently"""
        session = get_session(self.engine)
        
        try:
            records = []
            for state_data in states:
                state = AMMPoolState(
                    timestamp=state_data["timestamp"],
                    amm_address=state_data.get("amm_address", ""),
                    token=state_data["token"],
                    xrp_reserve=state_data["xrp_reserve"],
                    token_reserve=state_data["token_reserve"],
                    price=state_data["price"],
                    k_constant=state_data.get("k_constant"),
                    tvl_xrp=state_data.get("tvl_xrp"),
                    trading_fee=state_data.get("trading_fee"),
                    lp_token_supply=state_data.get("lp_token_supply")
                )
                records.append(state)
            
            session.bulk_save_objects(records)
            session.commit()
            logger.info(f"Stored {len(records)} AMM states")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing AMM states: {e}")
            raise
        finally:
            session.close()
    
    def get_price_history(
        self,
        pair: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Retrieve price history from database"""
        session = get_session(self.engine)
        
        try:
            query = session.query(PriceData).filter(PriceData.pair == pair)
            
            if start_date:
                query = query.filter(PriceData.timestamp >= start_date)
            if end_date:
                query = query.filter(PriceData.timestamp <= end_date)
            
            query = query.order_by(PriceData.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for r in results:
                data.append({
                    "timestamp": r.timestamp,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": float(r.volume) if r.volume else 0
                })
            
            return pd.DataFrame(data)
            
        finally:
            session.close()
    
    def get_amm_history(
        self,
        amm_address: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Retrieve AMM state history"""
        session = get_session(self.engine)
        
        try:
            query = session.query(AMMPoolState).filter(
                AMMPoolState.amm_address == amm_address
            )
            
            if start_date:
                query = query.filter(AMMPoolState.timestamp >= start_date)
            if end_date:
                query = query.filter(AMMPoolState.timestamp <= end_date)
            
            query = query.order_by(AMMPoolState.timestamp)
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for r in results:
                data.append({
                    "timestamp": r.timestamp,
                    "xrp_reserve": float(r.xrp_reserve),
                    "token_reserve": float(r.token_reserve),
                    "price": float(r.price),
                    "tvl_xrp": float(r.tvl_xrp) if r.tvl_xrp else 0,
                    "k_constant": float(r.k_constant) if r.k_constant else 0
                })
            
            return pd.DataFrame(data)
            
        finally:
            session.close()
    
    def store_backtest_result(self, result_data: Dict[str, Any]):
        """Store backtest results"""
        session = get_session(self.engine)
        
        try:
            result = BacktestResult(
                strategy=result_data["strategy"],
                pair=result_data["pair"],
                start_date=result_data["start_date"],
                end_date=result_data["end_date"],
                initial_balance=result_data["initial_balance"],
                final_balance=result_data["final_balance"],
                total_trades=result_data["total_trades"],
                winning_trades=result_data["winning_trades"],
                losing_trades=result_data["losing_trades"],
                total_pnl=result_data["total_pnl"],
                total_pnl_percent=result_data["total_pnl_percent"],
                max_drawdown=result_data["max_drawdown"],
                max_drawdown_percent=result_data["max_drawdown_percent"],
                sharpe_ratio=result_data["sharpe_ratio"],
                win_rate=result_data["win_rate"],
                trades=result_data.get("trades", []),
                equity_curve=result_data.get("equity_curve", []),
                parameters=result_data.get("parameters", {})
            )
            
            session.add(result)
            session.commit()
            logger.info(f"Stored backtest result for {result_data['strategy']}")
            
            return result.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing backtest result: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_data_timestamp(self, pair: str) -> Optional[datetime]:
        """Get the most recent data timestamp for a pair"""
        session = get_session(self.engine)
        
        try:
            result = session.query(PriceData.timestamp)\
                .filter(PriceData.pair == pair)\
                .order_by(PriceData.timestamp.desc())\
                .first()
            
            return result[0] if result else None
            
        finally:
            session.close()
    
    async def store_asset(self, asset_data: Dict[str, Any]):
        """Store asset information including LP tokens"""
        session = get_session(self.engine)
        
        try:
            # Check if asset already exists
            existing = session.query(Asset).filter(
                Asset.currency_code == asset_data["currency_code"],
                Asset.issuer == asset_data.get("issuer")
            ).first()
            
            if existing:
                # Update existing asset
                for key, value in asset_data.items():
                    setattr(existing, key, value)
            else:
                # Create new asset
                asset = Asset(**asset_data)
                session.add(asset)
                
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing asset: {e}")
            raise
        finally:
            session.close()
            
    async def store_dex_trade(self, trade_data: Dict[str, Any]):
        """Store DEX trade"""
        session = get_session(self.engine)
        
        try:
            # Check if trade already exists
            existing = session.query(DEXTrade).filter(
                DEXTrade.transaction_hash == trade_data["transaction_hash"]
            ).first()
            
            if not existing:
                trade = DEXTrade(**trade_data)
                session.add(trade)
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing DEX trade: {e}")
            raise
        finally:
            session.close()
            
    async def store_amm_snapshot(self, snapshot_data: Dict[str, Any]):
        """Store AMM pool snapshot"""
        session = get_session(self.engine)
        
        try:
            # Check if snapshot already exists for this ledger
            existing = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == snapshot_data["amm_address"],
                AMMSnapshot.ledger_index == snapshot_data["ledger_index"]
            ).first()
            
            if not existing:
                snapshot = AMMSnapshot(**snapshot_data)
                session.add(snapshot)
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing AMM snapshot: {e}")
            raise
        finally:
            session.close()
            
    async def store_token_transaction(self, tx_data: Dict[str, Any]):
        """Store token transaction from metadata"""
        session = get_session(self.engine)
        
        try:
            transaction = TokenTransaction(**tx_data)
            session.add(transaction)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing token transaction: {e}")
            raise
        finally:
            session.close()
            
    async def store_amm_position(self, position_data: Dict[str, Any]):
        """Store or update AMM position"""
        session = get_session(self.engine)
        
        try:
            # Check if position exists
            existing = session.query(AMMPosition).filter(
                AMMPosition.wallet_address == position_data["wallet_address"],
                AMMPosition.amm_address == position_data["amm_address"],
                AMMPosition.deposit_tx_hash == position_data["deposit_tx_hash"]
            ).first()
            
            if existing:
                # Update existing position
                for key, value in position_data.items():
                    if key not in ["id", "created_at"]:
                        setattr(existing, key, value)
            else:
                # Create new position
                position = AMMPosition(**position_data)
                session.add(position)
                
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing AMM position: {e}")
            raise
        finally:
            session.close()
            
    async def create_collection_log(self, log_data: Dict[str, Any]):
        """Create data collection log entry"""
        session = get_session(self.engine)
        
        try:
            log = DataCollectionLog(**log_data)
            session.add(log)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating collection log: {e}")
            raise
        finally:
            session.close()
            
    async def get_collection_log(
        self, 
        collection_type: str, 
        target: str
    ) -> Optional[Dict[str, Any]]:
        """Get collection log for specific type and target"""
        session = get_session(self.engine)
        
        try:
            log = session.query(DataCollectionLog).filter(
                DataCollectionLog.collection_type == collection_type,
                DataCollectionLog.target == target
            ).first()
            
            if log:
                return {
                    "id": log.id,
                    "collection_type": log.collection_type,
                    "target": log.target,
                    "start_ledger": log.start_ledger,
                    "end_ledger": log.end_ledger,
                    "last_processed_ledger": log.last_processed_ledger,
                    "status": log.status,
                    "records_collected": log.records_collected
                }
                
            return None
            
        finally:
            session.close()
            
    async def update_collection_log(
        self,
        collection_type: str,
        target: str,
        last_processed_ledger: int,
        records_collected: int
    ):
        """Update collection progress"""
        session = get_session(self.engine)
        
        try:
            log = session.query(DataCollectionLog).filter(
                DataCollectionLog.collection_type == collection_type,
                DataCollectionLog.target == target
            ).first()
            
            if log:
                log.last_processed_ledger = last_processed_ledger
                log.records_collected = records_collected
                
                # Check if completed
                if log.end_ledger and last_processed_ledger >= log.end_ledger:
                    log.status = 'completed'
                    log.completed_at = datetime.utcnow()
                    
                session.commit()
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating collection log: {e}")
            raise
        finally:
            session.close()
            
    async def get_dex_trades(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currency_pair: Optional[Tuple[str, str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get DEX trades with filters"""
        session = get_session(self.engine)
        
        try:
            query = session.query(DEXTrade)
            
            if start_date:
                query = query.filter(DEXTrade.timestamp >= start_date)
            if end_date:
                query = query.filter(DEXTrade.timestamp <= end_date)
                
            if currency_pair:
                gets_currency, pays_currency = currency_pair
                query = query.filter(
                    DEXTrade.gets_currency == gets_currency,
                    DEXTrade.pays_currency == pays_currency
                )
                
            query = query.order_by(DEXTrade.timestamp.desc())
            
            if limit:
                query = query.limit(limit)
                
            trades = query.all()
            
            return [{
                "timestamp": t.timestamp,
                "ledger_index": t.ledger_index,
                "transaction_hash": t.transaction_hash,
                "account": t.account,
                "gets_currency": t.gets_currency,
                "gets_issuer": t.gets_issuer,
                "gets_amount": float(t.gets_amount),
                "pays_currency": t.pays_currency,
                "pays_issuer": t.pays_issuer,
                "pays_amount": float(t.pays_amount),
                "price": float(t.price) if t.price else None
            } for t in trades]
            
        finally:
            session.close()
            
    async def get_amm_snapshots(
        self,
        amm_address: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get AMM snapshots for analysis"""
        session = get_session(self.engine)
        
        try:
            query = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == amm_address
            )
            
            if start_date:
                query = query.filter(AMMSnapshot.timestamp >= start_date)
            if end_date:
                query = query.filter(AMMSnapshot.timestamp <= end_date)
                
            query = query.order_by(AMMSnapshot.timestamp)
            
            if limit:
                query = query.limit(limit)
                
            snapshots = query.all()
            
            return [{
                "timestamp": s.timestamp,
                "ledger_index": s.ledger_index,
                "asset1_amount": float(s.asset1_amount),
                "asset2_amount": float(s.asset2_amount),
                "lp_token_supply": float(s.lp_token_supply),
                "k_constant": float(s.k_constant) if s.k_constant else None,
                "price_asset2_per_asset1": float(s.price_asset2_per_asset1) if s.price_asset2_per_asset1 else None,
                "tvl_xrp": float(s.tvl_xrp) if s.tvl_xrp else None
            } for s in snapshots]
            
        finally:
            session.close()
            
    async def store_amm_activity(self, activity_data: Dict[str, Any]):
        """Store AMM activity (deposits, withdrawals, etc.)"""
        # This would store in a separate activity table or use the position tracking
        # For now, we'll use the position tracking system
        if activity_data.get('action') == 'deposit':
            position_data = {
                'wallet_address': activity_data['account'],
                'amm_address': activity_data['amm_account'],
                'deposit_tx_hash': activity_data.get('transaction_hash'),
                'deposit_timestamp': activity_data.get('timestamp'),
                'lp_tokens_received': activity_data.get('lp_tokens_received', 0),
                'is_active': True
            }
            await self.store_amm_position(position_data)
            
    def update_collection_progress(
        self,
        collection_type: str,
        target: str,
        last_ledger: int,
        status: str = "active",
        records_added: int = 0
    ):
        """Update data collection progress"""
        session = get_session(self.engine)
        
        try:
            # Get or create log entry
            log = session.query(DataCollectionLog).filter(
                DataCollectionLog.collection_type == collection_type,
                DataCollectionLog.target == target
            ).first()
            
            if not log:
                log = DataCollectionLog(
                    collection_type=collection_type,
                    target=target,
                    started_at=datetime.utcnow()
                )
                session.add(log)
                
            # Update fields
            log.last_processed_ledger = last_ledger
            log.status = status
            log.last_run = datetime.utcnow()
            log.records_collected = (log.records_collected or 0) + records_added
            
            if status == "completed":
                log.completed_at = datetime.utcnow()
                
            session.commit()
            
        except Exception as e:
            logger.error(f"Error updating collection progress: {e}")
            session.rollback()
        finally:
            session.close()
            
    async def store_amm_snapshot(self, snapshot_data: Dict[str, Any]):
        """Store AMM pool snapshot"""
        session = get_session(self.engine)
        
        try:
            # Check if we already have this snapshot (same AMM, same ledger)
            existing = session.query(AMMSnapshot).filter(
                AMMSnapshot.amm_address == snapshot_data["amm_address"],
                AMMSnapshot.ledger_index == snapshot_data["ledger_index"]
            ).first()
            
            if existing:
                logger.debug(f"AMM snapshot already exists for {snapshot_data['amm_address']} at ledger {snapshot_data['ledger_index']}")
                return
                
            snapshot = AMMSnapshot(
                timestamp=snapshot_data.get("timestamp", datetime.utcnow()),
                ledger_index=snapshot_data["ledger_index"],
                amm_address=snapshot_data["amm_address"],
                asset1_currency=snapshot_data["asset1_currency"],
                asset1_issuer=snapshot_data.get("asset1_issuer"),
                asset1_amount=snapshot_data["asset1_amount"],
                asset2_currency=snapshot_data["asset2_currency"],
                asset2_issuer=snapshot_data.get("asset2_issuer"),
                asset2_amount=snapshot_data["asset2_amount"],
                lp_token_currency=snapshot_data.get("lp_token_currency"),
                lp_token_supply=snapshot_data.get("lp_token_supply", 0),
                trading_fee=snapshot_data.get("trading_fee"),
                k_constant=snapshot_data.get("k_constant"),
                price_asset2_per_asset1=snapshot_data.get("price_asset2_per_asset1"),
                tvl_xrp=snapshot_data.get("tvl_xrp")
            )
            
            session.add(snapshot)
            session.commit()
            
            logger.debug(f"Stored AMM snapshot for {snapshot_data['amm_address']}")
            
        except Exception as e:
            logger.error(f"Error storing AMM snapshot: {e}")
            session.rollback()
        finally:
            session.close()