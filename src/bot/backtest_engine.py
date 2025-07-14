import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from loguru import logger
from dataclasses import dataclass, field

from src.config.settings import Settings
from src.strategies.base import BaseStrategy
from src.config.constants import (
    SIGNAL_BUY, SIGNAL_SELL, ORDER_STATUS_FILLED,
    DEFAULT_SLIPPAGE_TOLERANCE
)


@dataclass
class BacktestResult:
    initial_balance: Decimal
    final_balance: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: Decimal
    total_pnl_percent: Decimal
    max_drawdown: Decimal
    max_drawdown_percent: Decimal
    sharpe_ratio: float
    win_rate: float
    average_win: Decimal
    average_loss: Decimal
    profit_factor: Decimal
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        settings: Settings,
        strategy: BaseStrategy,
        initial_balance: Decimal = Decimal("10000"),
        commission: Decimal = Decimal("0.001")  # 0.1% commission
    ):
        self.settings = settings
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.commission = commission
        
        # State tracking
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        
    async def run_backtest(
        self,
        historical_data: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestResult:
        """
        Run backtest on historical data
        
        Args:
            historical_data: DataFrame with columns: timestamp, open, high, low, close, volume
            start_date: Optional start date for backtest
            end_date: Optional end date for backtest
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Filter data by date range if specified
        if start_date:
            historical_data = historical_data[historical_data['timestamp'] >= start_date]
        if end_date:
            historical_data = historical_data[historical_data['timestamp'] <= end_date]
        
        # Reset state
        self._reset_state()
        
        # Process each candle
        for idx, row in historical_data.iterrows():
            await self._process_candle(row)
        
        # Close any open positions at the end
        await self._close_all_positions(historical_data.iloc[-1])
        
        # Calculate and return results
        return self._calculate_results()
    
    def _reset_state(self):
        """Reset engine state for new backtest"""
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.pending_orders = {}
        self.strategy.clear_history()
    
    async def _process_candle(self, candle: pd.Series):
        """Process a single candle"""
        # Check pending orders
        await self._check_pending_orders(candle)
        
        # Update position values
        self._update_positions(candle)
        
        # Create market data for strategy
        market_data = self._create_market_data(candle)
        
        # Get signal from strategy
        signal = await self.strategy.analyze(market_data)
        
        # Process signal
        await self._process_signal(signal, candle)
        
        # Record equity
        self._record_equity(candle)
    
    def _create_market_data(self, candle: pd.Series) -> Dict[str, Any]:
        """Create market data dict from candle"""
        # Simulate order book with small spread
        spread_percent = Decimal("0.001")  # 0.1% spread
        mid_price = Decimal(str(candle['close']))
        half_spread = mid_price * spread_percent / 2
        
        return {
            "timestamp": candle['timestamp'],
            "pair": self.settings.trading_pair,
            "best_bid": mid_price - half_spread,
            "best_ask": mid_price + half_spread,
            "mid_price": mid_price,
            "spread": half_spread * 2,
            "spread_percentage": spread_percent * 100,
            "volume_24h": Decimal(str(candle.get('volume', 0))),
            "order_book": {
                "bids": [{"price": float(mid_price - half_spread), "amount": 10000}],
                "asks": [{"price": float(mid_price + half_spread), "amount": 10000}]
            }
        }
    
    async def _process_signal(self, signal: Dict[str, Any], candle: pd.Series):
        """Process trading signal"""
        if signal["action"] == SIGNAL_BUY:
            await self._execute_buy(signal, candle)
        elif signal["action"] == SIGNAL_SELL:
            position_id = signal.get("position_id")
            if position_id and position_id in self.positions:
                await self._execute_sell(position_id, candle, "Signal")
    
    async def _execute_buy(self, signal: Dict[str, Any], candle: pd.Series):
        """Execute buy order"""
        # Check if we can open new position
        if len(self.positions) >= self.settings.max_open_positions:
            return
        
        # Calculate position size
        position_size = self._calculate_position_size(signal, candle)
        if position_size <= 0:
            return
        
        # Calculate cost with slippage and commission
        entry_price = Decimal(str(candle['close'])) * (1 + DEFAULT_SLIPPAGE_TOLERANCE)
        cost = position_size * entry_price
        commission_cost = cost * self.commission
        total_cost = cost + commission_cost
        
        # Check balance
        if total_cost > self.balance:
            return
        
        # Create position
        position_id = f"pos_{candle['timestamp']}_{len(self.positions)}"
        self.positions[position_id] = {
            "size": position_size,
            "entry_price": entry_price,
            "entry_time": candle['timestamp'],
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "commission_paid": commission_cost
        }
        
        # Update balance
        self.balance -= total_cost
        
        # Record trade
        self.trades.append({
            "id": position_id,
            "type": "buy",
            "time": candle['timestamp'],
            "price": entry_price,
            "size": position_size,
            "cost": total_cost,
            "commission": commission_cost,
            "balance": self.balance
        })
        
        logger.debug(f"Bought {position_size} at {entry_price}, balance: {self.balance}")
    
    async def _execute_sell(self, position_id: str, candle: pd.Series, reason: str = "Signal"):
        """Execute sell order"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Calculate exit with slippage
        exit_price = Decimal(str(candle['close'])) * (1 - DEFAULT_SLIPPAGE_TOLERANCE)
        proceeds = position["size"] * exit_price
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost
        
        # Calculate PnL
        entry_cost = position["size"] * position["entry_price"]
        pnl = net_proceeds - entry_cost - position["commission_paid"]
        pnl_percent = (pnl / entry_cost) * 100
        
        # Update balance
        self.balance += net_proceeds
        
        # Record trade
        self.trades.append({
            "id": position_id,
            "type": "sell",
            "time": candle['timestamp'],
            "price": exit_price,
            "size": position["size"],
            "proceeds": net_proceeds,
            "commission": commission_cost,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "reason": reason,
            "balance": self.balance,
            "hold_time": (candle['timestamp'] - position["entry_time"]).total_seconds()
        })
        
        # Remove position
        del self.positions[position_id]
        
        logger.debug(f"Sold {position['size']} at {exit_price}, PnL: {pnl:.2f} ({pnl_percent:.2f}%), balance: {self.balance}")
    
    async def _check_pending_orders(self, candle: pd.Series):
        """Check stop loss and take profit orders"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            current_price = Decimal(str(candle['close']))
            
            # Check stop loss
            if position.get("stop_loss") and current_price <= position["stop_loss"]:
                positions_to_close.append((position_id, "Stop Loss"))
            
            # Check take profit
            elif position.get("take_profit") and current_price >= position["take_profit"]:
                positions_to_close.append((position_id, "Take Profit"))
        
        # Execute closes
        for position_id, reason in positions_to_close:
            await self._execute_sell(position_id, candle, reason)
    
    def _calculate_position_size(self, signal: Dict[str, Any], candle: pd.Series) -> Decimal:
        """Calculate position size based on signal and risk management"""
        # Available balance for trading
        available = self.balance * (Decimal(str(self.settings.max_position_size_pct)) / 100)
        
        # Adjust by signal confidence
        confidence = Decimal(str(signal.get("confidence", 0.5)))
        base_size = available * confidence
        
        # Apply limits
        position_value = max(
            Decimal(str(self.settings.min_trade_amount)),
            min(base_size, Decimal(str(self.settings.max_trade_amount)))
        )
        
        # Convert to position size
        current_price = Decimal(str(candle['close']))
        position_size = position_value / current_price
        
        return position_size
    
    def _update_positions(self, candle: pd.Series):
        """Update position values with current price"""
        current_price = Decimal(str(candle['close']))
        
        for position in self.positions.values():
            position["current_price"] = current_price
            position["unrealized_pnl"] = (
                (current_price - position["entry_price"]) * position["size"]
            )
    
    def _record_equity(self, candle: pd.Series):
        """Record current equity value"""
        # Calculate total equity (balance + unrealized PnL)
        unrealized_pnl = sum(
            pos["unrealized_pnl"] for pos in self.positions.values()
        )
        total_equity = self.balance + unrealized_pnl
        
        self.equity_curve.append({
            "timestamp": candle['timestamp'],
            "balance": self.balance,
            "unrealized_pnl": unrealized_pnl,
            "total_equity": total_equity,
            "open_positions": len(self.positions)
        })
    
    async def _close_all_positions(self, last_candle: pd.Series):
        """Close all open positions at end of backtest"""
        position_ids = list(self.positions.keys())
        for position_id in position_ids:
            await self._execute_sell(position_id, last_candle, "End of Backtest")
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results"""
        # Filter sell trades
        sell_trades = [t for t in self.trades if t["type"] == "sell"]
        
        # Calculate basic metrics
        total_trades = len(sell_trades)
        winning_trades = [t for t in sell_trades if t["pnl"] > 0]
        losing_trades = [t for t in sell_trades if t["pnl"] <= 0]
        
        total_pnl = sum(t["pnl"] for t in sell_trades)
        total_pnl_percent = (total_pnl / self.initial_balance) * 100
        
        # Win rate
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # Average win/loss
        average_win = (
            sum(t["pnl"] for t in winning_trades) / len(winning_trades)
            if winning_trades else Decimal("0")
        )
        average_loss = (
            sum(abs(t["pnl"]) for t in losing_trades) / len(losing_trades)
            if losing_trades else Decimal("0")
        )
        
        # Profit factor
        gross_profit = sum(t["pnl"] for t in winning_trades)
        gross_loss = sum(abs(t["pnl"]) for t in losing_trades)
        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0 else Decimal("999")
        )
        
        # Calculate drawdown
        max_drawdown, max_drawdown_percent = self._calculate_max_drawdown()
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        return BacktestResult(
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
    
    def _calculate_max_drawdown(self) -> Tuple[Decimal, Decimal]:
        """Calculate maximum drawdown"""
        if not self.equity_curve:
            return Decimal("0"), Decimal("0")
        
        peak = self.initial_balance
        max_drawdown = Decimal("0")
        max_drawdown_percent = Decimal("0")
        
        for point in self.equity_curve:
            equity = point["total_equity"]
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_percent = (drawdown / peak * 100) if peak > 0 else Decimal("0")
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent
        
        return max_drawdown, max_drawdown_percent
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1]["total_equity"]
            curr_equity = self.equity_curve[i]["total_equity"]
            if prev_equity > 0:
                daily_return = float((curr_equity - prev_equity) / prev_equity)
                returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        # Calculate Sharpe ratio (assuming 0 risk-free rate)
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming daily data)
        sharpe = (avg_return / std_return) * (252 ** 0.5)
        
        return sharpe