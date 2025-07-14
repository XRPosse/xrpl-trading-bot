import pytest
from decimal import Decimal
from src.strategies.simple_momentum import SimpleMomentumStrategy
from src.config.constants import SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD


@pytest.fixture
def strategy():
    return SimpleMomentumStrategy()


@pytest.fixture
def sample_market_data():
    return {
        "timestamp": "2024-01-14T10:00:00",
        "pair": "XRP/USDT",
        "best_bid": Decimal("0.55"),
        "best_ask": Decimal("0.56"),
        "mid_price": Decimal("0.555"),
        "spread": Decimal("0.01"),
        "spread_percentage": Decimal("1.8"),
        "order_book": {
            "bids": [{"price": 0.55, "amount": 1000}],
            "asks": [{"price": 0.56, "amount": 1000}]
        }
    }


@pytest.mark.asyncio
async def test_strategy_initialization(strategy):
    assert strategy.name == "Simple Momentum"
    assert strategy.parameters["lookback_period"] == 20
    assert strategy.parameters["momentum_threshold"] == 0.02


@pytest.mark.asyncio
async def test_insufficient_history(strategy, sample_market_data):
    # Test with insufficient price history
    signal = await strategy.analyze(sample_market_data)
    
    assert signal["action"] == SIGNAL_HOLD
    assert "Insufficient price history" in signal["reason"]


@pytest.mark.asyncio
async def test_momentum_calculation(strategy, sample_market_data):
    # Fill price history with upward trend
    for i in range(20):
        price = Decimal("0.50") + Decimal("0.01") * i
        strategy._price_history.append(price)
    
    momentum = strategy._calculate_momentum()
    assert momentum > 0  # Positive momentum for upward trend


@pytest.mark.asyncio
async def test_buy_signal(strategy, sample_market_data):
    # Create strong upward momentum
    for i in range(20):
        price = Decimal("0.50") + Decimal("0.002") * i
        strategy._price_history.append(price)
    
    signal = await strategy.analyze(sample_market_data)
    
    # Should generate buy signal with strong upward momentum
    assert signal["action"] == SIGNAL_BUY
    assert signal["stop_loss"] is not None
    assert signal["take_profit"] is not None
    assert signal["confidence"] >= 0.6