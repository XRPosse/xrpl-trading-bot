from typing import Dict, Any, List, Optional
from decimal import Decimal
from collections import deque
from loguru import logger

from src.strategies.base import BaseStrategy
from src.config.constants import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD


class SimpleMomentumStrategy(BaseStrategy):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        default_params = {
            "lookback_period": 20,  # Number of price points to consider
            "momentum_threshold": 0.02,  # 2% price change threshold
            "volume_factor": 1.5,  # Volume must be 1.5x average
            "stop_loss_pct": 2.0,  # 2% stop loss
            "take_profit_pct": 5.0,  # 5% take profit
            "min_confidence": 0.6,  # Minimum confidence to trade
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Simple Momentum", default_params)
        
        # Price history for momentum calculation
        self._price_history: deque = deque(maxlen=self.parameters["lookback_period"])
        self._volume_history: deque = deque(maxlen=self.parameters["lookback_period"])
        
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        # Validate market data
        if not self.validate_market_data(market_data):
            logger.warning("Invalid market data received")
            return self.get_hold_signal("Invalid market data")
        
        # Update price history
        current_price = market_data["mid_price"]
        self._price_history.append(current_price)
        
        # Need enough history
        if len(self._price_history) < self.parameters["lookback_period"]:
            return self.get_hold_signal("Insufficient price history")
        
        # Calculate momentum
        momentum = self._calculate_momentum()
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength()
        
        # Check volume (simplified for now)
        volume_signal = self._check_volume_signal(market_data)
        
        # Generate trading signal
        signal = self._generate_signal(
            momentum,
            trend_strength,
            volume_signal,
            current_price,
            market_data
        )
        
        return signal
    
    def _calculate_momentum(self) -> Decimal:
        if len(self._price_history) < 2:
            return Decimal("0")
        
        # Simple momentum: (current_price - old_price) / old_price
        current_price = self._price_history[-1]
        old_price = self._price_history[0]
        
        if old_price == 0:
            return Decimal("0")
        
        momentum = (current_price - old_price) / old_price
        return momentum
    
    def _calculate_trend_strength(self) -> Decimal:
        if len(self._price_history) < 3:
            return Decimal("0")
        
        # Count positive vs negative price changes
        positive_moves = 0
        negative_moves = 0
        
        for i in range(1, len(self._price_history)):
            if self._price_history[i] > self._price_history[i-1]:
                positive_moves += 1
            elif self._price_history[i] < self._price_history[i-1]:
                negative_moves += 1
        
        total_moves = positive_moves + negative_moves
        if total_moves == 0:
            return Decimal("0")
        
        # Trend strength from -1 to 1
        trend_strength = Decimal(str((positive_moves - negative_moves) / total_moves))
        return trend_strength
    
    def _check_volume_signal(self, market_data: Dict[str, Any]) -> bool:
        # Simplified volume check - in real implementation would check actual volume
        # For now, check order book depth
        order_book = market_data.get("order_book", {})
        
        bid_depth = sum(Decimal(str(bid["amount"])) for bid in order_book.get("bids", [])[:5])
        ask_depth = sum(Decimal(str(ask["amount"])) for ask in order_book.get("asks", [])[:5])
        
        # Good volume if balanced order book
        if bid_depth > 0 and ask_depth > 0:
            balance_ratio = min(bid_depth, ask_depth) / max(bid_depth, ask_depth)
            return balance_ratio > 0.5  # At least 50% balanced
        
        return False
    
    def _generate_signal(
        self,
        momentum: Decimal,
        trend_strength: Decimal,
        volume_signal: bool,
        current_price: Decimal,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Calculate confidence based on multiple factors
        confidence = self._calculate_confidence(momentum, trend_strength, volume_signal)
        
        # Check if confidence meets minimum threshold
        if confidence < self.parameters["min_confidence"]:
            return self.get_hold_signal(f"Low confidence: {confidence:.2f}")
        
        # Momentum threshold
        momentum_threshold = Decimal(str(self.parameters["momentum_threshold"]))
        
        # Buy signal
        if momentum > momentum_threshold and trend_strength > 0.3:
            stop_loss = self.calculate_stop_loss(
                current_price,
                Decimal(str(self.parameters["stop_loss_pct"]))
            )
            take_profit = self.calculate_take_profit(
                current_price,
                Decimal(str(self.parameters["take_profit_pct"]))
            )
            
            return self._create_signal(
                action=SIGNAL_BUY,
                confidence=float(confidence),
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Positive momentum: {momentum:.2%}, Trend: {trend_strength:.2f}"
            )
        
        # Sell signal
        elif momentum < -momentum_threshold and trend_strength < -0.3:
            # For existing positions (would need position tracking)
            return self._create_signal(
                action=SIGNAL_SELL,
                confidence=float(confidence),
                reason=f"Negative momentum: {momentum:.2%}, Trend: {trend_strength:.2f}"
            )
        
        # Hold signal
        else:
            return self.get_hold_signal(
                f"Momentum: {momentum:.2%}, Trend: {trend_strength:.2f}"
            )
    
    def _calculate_confidence(
        self,
        momentum: Decimal,
        trend_strength: Decimal,
        volume_signal: bool
    ) -> Decimal:
        # Base confidence from momentum strength
        momentum_confidence = min(abs(momentum) / Decimal("0.1"), Decimal("1"))  # Max 1.0 at 10% move
        
        # Trend contribution
        trend_confidence = abs(trend_strength)
        
        # Volume contribution
        volume_confidence = Decimal("0.2") if volume_signal else Decimal("0")
        
        # Weighted average
        confidence = (
            momentum_confidence * Decimal("0.5") +
            trend_confidence * Decimal("0.3") +
            volume_confidence * Decimal("0.2")
        )
        
        return min(confidence, Decimal("1"))  # Cap at 1.0