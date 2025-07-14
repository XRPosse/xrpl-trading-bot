from decimal import Decimal

# XRPL Constants
XRP_DECIMAL_PLACES = 6
DROPS_PER_XRP = 1_000_000

# Trading Constants
DEFAULT_SLIPPAGE_TOLERANCE = Decimal("0.01")  # 1%
MIN_XRP_BALANCE = Decimal("20")  # XRPL account reserve
DEFAULT_GAS_BUFFER = Decimal("10")  # XRP to keep for transaction fees

# Order Types
ORDER_TYPE_MARKET = "market"
ORDER_TYPE_LIMIT = "limit"
ORDER_TYPE_STOP_LOSS = "stop_loss"
ORDER_TYPE_TAKE_PROFIT = "take_profit"

# Order Status
ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_OPEN = "open"
ORDER_STATUS_FILLED = "filled"
ORDER_STATUS_PARTIALLY_FILLED = "partially_filled"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUS_FAILED = "failed"

# Trading Signals
SIGNAL_BUY = "buy"
SIGNAL_SELL = "sell"
SIGNAL_HOLD = "hold"

# Time Constants
CANDLE_INTERVALS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# Technical Indicators Default Parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

EMA_SHORT = 9
EMA_LONG = 21

BOLLINGER_PERIOD = 20
BOLLINGER_STD_DEV = 2

# Risk Management
DEFAULT_RISK_PER_TRADE = Decimal("0.02")  # 2% of capital
MAX_CORRELATION = 0.7  # Maximum correlation between positions
MIN_SHARPE_RATIO = 1.0  # Minimum acceptable Sharpe ratio

# API Rate Limits
XRPL_RATE_LIMIT = 60  # requests per minute
EXCHANGE_RATE_LIMIT = 100  # requests per minute

# Database
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30

# Monitoring
METRICS_UPDATE_INTERVAL = 30  # seconds
HEALTH_CHECK_INTERVAL = 60  # seconds