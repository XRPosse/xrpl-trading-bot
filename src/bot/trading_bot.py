import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from loguru import logger

from src.config.settings import Settings, TradingMode
from src.config.constants import (
    SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD,
    ORDER_STATUS_FILLED, ORDER_STATUS_OPEN
)
from src.exchanges.xrpl_client import XRPLClient
from src.strategies.base import BaseStrategy
from src.utils.logger import setup_logger


class TradingBot:
    def __init__(self, settings: Settings, strategy: BaseStrategy):
        self.settings = settings
        self.strategy = strategy
        self.xrpl_client = XRPLClient(settings)
        self.logger = setup_logger()
        
        self._running = False
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._balance: Decimal = Decimal("0")
        self._last_update = datetime.now()
        
    async def start(self) -> None:
        try:
            logger.info("Starting trading bot...")
            
            # Connect to XRPL
            await self.xrpl_client.connect()
            
            # Initialize account
            if self.xrpl_client.wallet:
                await self._update_balance()
                logger.info(f"Initial balance: {self._balance} XRP")
            
            # Start main trading loop
            self._running = True
            await self._trading_loop()
            
        except Exception as e:
            logger.error(f"Error starting trading bot: {e}")
            raise
    
    async def stop(self) -> None:
        logger.info("Stopping trading bot...")
        self._running = False
        
        # Cancel all open orders
        await self._cancel_all_orders()
        
        # Disconnect from XRPL
        await self.xrpl_client.disconnect()
        
        logger.info("Trading bot stopped")
    
    async def _trading_loop(self) -> None:
        while self._running:
            try:
                # Update market data
                market_data = await self._get_market_data()
                
                # Get trading signal from strategy
                signal = await self.strategy.analyze(market_data)
                
                # Execute trading logic based on signal
                await self._process_signal(signal, market_data)
                
                # Update positions and orders
                await self._update_positions()
                await self._check_orders()
                
                # Risk management checks
                await self._check_risk_limits()
                
                # Log status
                self._log_status()
                
                # Wait for next update
                await asyncio.sleep(self.settings.update_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(self.settings.update_interval)
    
    async def _get_market_data(self) -> Dict[str, Any]:
        try:
            base, quote = self.settings.trading_pair.split("/")
            
            # Get order book
            order_book = await self.xrpl_client.get_order_book(base, quote)
            
            # Calculate mid price
            best_bid = Decimal(order_book["bids"][0]["price"]) if order_book["bids"] else Decimal("0")
            best_ask = Decimal(order_book["asks"][0]["price"]) if order_book["asks"] else Decimal("0")
            mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else Decimal("0")
            
            # Calculate spread
            spread = best_ask - best_bid if best_bid and best_ask else Decimal("0")
            spread_percentage = (spread / mid_price * 100) if mid_price > 0 else Decimal("0")
            
            return {
                "timestamp": datetime.now(),
                "pair": self.settings.trading_pair,
                "order_book": order_book,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid_price": mid_price,
                "spread": spread,
                "spread_percentage": spread_percentage,
                "volume_24h": Decimal("0"),  # Would need additional API call
            }
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    async def _process_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> None:
        if not signal or signal["action"] == SIGNAL_HOLD:
            return
        
        try:
            if signal["action"] == SIGNAL_BUY:
                await self._execute_buy(signal, market_data)
            elif signal["action"] == SIGNAL_SELL:
                await self._execute_sell(signal, market_data)
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _execute_buy(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> None:
        # Check if we can open new position
        if len(self._positions) >= self.settings.max_open_positions:
            logger.warning("Maximum open positions reached, skipping buy signal")
            return
        
        # Calculate position size
        position_size = await self._calculate_position_size(signal, market_data)
        if position_size <= 0:
            logger.warning("Invalid position size calculated, skipping buy")
            return
        
        # Check if we have enough balance
        required_balance = position_size * market_data["best_ask"]
        if required_balance > self._balance:
            logger.warning(f"Insufficient balance: {self._balance} < {required_balance}")
            return
        
        if self.settings.bot_mode == TradingMode.PAPER_TRADING:
            # Simulate order execution
            order_id = f"paper_{datetime.now().timestamp()}"
            self._orders[order_id] = {
                "id": order_id,
                "type": "buy",
                "size": position_size,
                "price": market_data["best_ask"],
                "status": ORDER_STATUS_FILLED,
                "timestamp": datetime.now()
            }
            
            # Create position
            self._positions[order_id] = {
                "size": position_size,
                "entry_price": market_data["best_ask"],
                "current_price": market_data["best_ask"],
                "unrealized_pnl": Decimal("0"),
                "stop_loss": signal.get("stop_loss"),
                "take_profit": signal.get("take_profit"),
                "timestamp": datetime.now()
            }
            
            # Update balance
            self._balance -= required_balance
            
            logger.info(f"Paper trading: Bought {position_size} at {market_data['best_ask']}")
            
        else:
            # Execute real order on XRPL
            # This would involve creating an offer on the DEX
            logger.warning("Live trading not fully implemented yet")
    
    async def _execute_sell(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> None:
        # Find position to close
        position_id = signal.get("position_id")
        if not position_id or position_id not in self._positions:
            logger.warning("No position to sell")
            return
        
        position = self._positions[position_id]
        
        if self.settings.bot_mode == TradingMode.PAPER_TRADING:
            # Calculate PnL
            exit_price = market_data["best_bid"]
            pnl = (exit_price - position["entry_price"]) * position["size"]
            
            # Update balance
            self._balance += position["size"] * exit_price
            
            # Remove position
            del self._positions[position_id]
            
            logger.info(
                f"Paper trading: Sold {position['size']} at {exit_price}, "
                f"PnL: {pnl:.2f}"
            )
            
        else:
            # Execute real order on XRPL
            logger.warning("Live trading not fully implemented yet")
    
    async def _calculate_position_size(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Decimal:
        # Get available balance for trading
        available_balance = self._balance * (
            Decimal(str(self.settings.max_position_size_pct)) / 100
        )
        
        # Calculate position size based on signal strength and risk
        confidence = Decimal(str(signal.get("confidence", 0.5)))
        base_size = available_balance * confidence
        
        # Apply min/max trade amount limits
        position_size = max(
            Decimal(str(self.settings.min_trade_amount)),
            min(base_size, Decimal(str(self.settings.max_trade_amount)))
        )
        
        # Convert to base currency units
        if market_data.get("best_ask"):
            position_size = position_size / market_data["best_ask"]
        
        return position_size
    
    async def _update_balance(self) -> None:
        if self.xrpl_client.wallet:
            self._balance = await self.xrpl_client.get_xrp_balance()
    
    async def _update_positions(self) -> None:
        # Update current prices and calculate unrealized PnL
        for position_id, position in self._positions.items():
            market_data = await self._get_market_data()
            if market_data:
                position["current_price"] = market_data["mid_price"]
                position["unrealized_pnl"] = (
                    position["current_price"] - position["entry_price"]
                ) * position["size"]
                
                # Check stop loss and take profit
                await self._check_position_limits(position_id, position, market_data)
    
    async def _check_position_limits(
        self,
        position_id: str,
        position: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> None:
        current_price = market_data["mid_price"]
        
        # Check stop loss
        if position.get("stop_loss") and current_price <= position["stop_loss"]:
            logger.info(f"Stop loss triggered for position {position_id}")
            await self._execute_sell(
                {"action": SIGNAL_SELL, "position_id": position_id},
                market_data
            )
        
        # Check take profit
        elif position.get("take_profit") and current_price >= position["take_profit"]:
            logger.info(f"Take profit triggered for position {position_id}")
            await self._execute_sell(
                {"action": SIGNAL_SELL, "position_id": position_id},
                market_data
            )
    
    async def _check_orders(self) -> None:
        # Check status of open orders
        # In real implementation, this would query the XRPL for order status
        pass
    
    async def _check_risk_limits(self) -> None:
        # Calculate total exposure
        total_exposure = sum(
            pos["size"] * pos["current_price"]
            for pos in self._positions.values()
        )
        
        # Check daily loss limit
        total_pnl = sum(
            pos["unrealized_pnl"]
            for pos in self._positions.values()
        )
        
        if abs(total_pnl) > Decimal(str(self.settings.daily_loss_limit)):
            logger.warning(f"Daily loss limit reached: {total_pnl}")
            self._running = False
    
    async def _cancel_all_orders(self) -> None:
        # Cancel all open orders
        for order_id, order in list(self._orders.items()):
            if order["status"] == ORDER_STATUS_OPEN:
                # In real implementation, would cancel order on XRPL
                del self._orders[order_id]
                logger.info(f"Cancelled order {order_id}")
    
    def _log_status(self) -> None:
        total_pnl = sum(
            pos["unrealized_pnl"]
            for pos in self._positions.values()
        )
        
        logger.info(
            f"Status - Balance: {self._balance:.2f} XRP, "
            f"Positions: {len(self._positions)}, "
            f"Open Orders: {len([o for o in self._orders.values() if o['status'] == ORDER_STATUS_OPEN])}, "
            f"Unrealized PnL: {total_pnl:.2f}"
        )