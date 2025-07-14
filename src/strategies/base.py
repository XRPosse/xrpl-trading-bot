from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from src.config.constants import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD


class BaseStrategy(ABC):
    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.parameters = parameters or {}
        self._history: List[Dict[str, Any]] = []
        
    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def _create_signal(
        self,
        action: str,
        confidence: float = 0.5,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        position_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        signal = {
            "timestamp": datetime.now(),
            "action": action,
            "confidence": confidence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_id": position_id,
            "reason": reason,
            "strategy": self.name
        }
        
        # Store in history
        self._history.append(signal)
        
        return signal
    
    def get_hold_signal(self, reason: str = "No clear signal") -> Dict[str, Any]:
        return self._create_signal(SIGNAL_HOLD, reason=reason)
    
    def calculate_stop_loss(
        self,
        entry_price: Decimal,
        percentage: Decimal,
        is_long: bool = True
    ) -> Decimal:
        if is_long:
            return entry_price * (1 - percentage / 100)
        else:
            return entry_price * (1 + percentage / 100)
    
    def calculate_take_profit(
        self,
        entry_price: Decimal,
        percentage: Decimal,
        is_long: bool = True
    ) -> Decimal:
        if is_long:
            return entry_price * (1 + percentage / 100)
        else:
            return entry_price * (1 - percentage / 100)
    
    def get_signal_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if limit:
            return self._history[-limit:]
        return self._history
    
    def clear_history(self) -> None:
        self._history.clear()
    
    def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        required_fields = ["timestamp", "best_bid", "best_ask", "mid_price"]
        
        for field in required_fields:
            if field not in market_data:
                return False
            
        # Check for valid prices
        if (
            market_data["best_bid"] <= 0 or
            market_data["best_ask"] <= 0 or
            market_data["mid_price"] <= 0
        ):
            return False
        
        # Check spread is reasonable
        if market_data["spread_percentage"] > 10:  # More than 10% spread
            return False
        
        return True