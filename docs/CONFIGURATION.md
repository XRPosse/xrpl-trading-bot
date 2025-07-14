# Configuration Guide

This guide explains all configuration options available in the XRPL Trading Bot.

## Environment Variables

Configuration is managed through environment variables stored in a `.env` file. Copy `.env.example` to `.env` and modify as needed.

### XRPL Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `XRPL_NETWORK` | `mainnet` | Network to connect to: `mainnet`, `testnet`, or `custom` |
| `XRPL_WSS_URL` | `wss://s1.ripple.com:443` | WebSocket URL for XRPL connection |
| `XRPL_JSON_RPC_URL` | `https://s1.ripple.com:51234` | JSON-RPC URL for XRPL queries |

### Wallet Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WALLET_SEED` | None | Your XRPL wallet seed (NEVER share this!) |
| `WALLET_ADDRESS` | None | Your XRPL wallet address |

⚠️ **Security Warning**: Never commit your wallet credentials to version control!

### Trading Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_PAIR` | `XRP/USDT` | Trading pair to monitor and trade |
| `MIN_TRADE_AMOUNT` | `10` | Minimum trade size in quote currency |
| `MAX_TRADE_AMOUNT` | `1000` | Maximum trade size in quote currency |
| `STOP_LOSS_PERCENTAGE` | `5` | Default stop loss percentage (0-100) |
| `TAKE_PROFIT_PERCENTAGE` | `10` | Default take profit percentage (0-100) |

### Bot Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_MODE` | `paper_trading` | Trading mode: `paper_trading` or `live` |
| `STRATEGY` | `simple_momentum` | Trading strategy to use |
| `UPDATE_INTERVAL` | `60` | Market data update interval in seconds |

### Risk Management

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_OPEN_POSITIONS` | `3` | Maximum number of concurrent positions |
| `MAX_POSITION_SIZE_PCT` | `20` | Max percentage of balance per position |
| `DAILY_LOSS_LIMIT` | `100` | Daily loss limit in quote currency |

### Exchange Configuration (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `EXCHANGE_NAME` | None | Exchange name for CEX integration |
| `EXCHANGE_API_KEY` | None | Exchange API key |
| `EXCHANGE_API_SECRET` | None | Exchange API secret |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `logs/trading_bot.log` | Path to log file |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///trading_bot.db` | Database connection URL |

### Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_METRICS` | `true` | Enable Prometheus metrics |
| `METRICS_PORT` | `8000` | Port for metrics endpoint |

## Configuration Examples

### Minimal Configuration (Backtesting Only)
```bash
# .env
XRPL_NETWORK=mainnet
BOT_MODE=paper_trading
```

### Paper Trading Configuration
```bash
# .env
XRPL_NETWORK=mainnet
BOT_MODE=paper_trading
TRADING_PAIR=XRP/USDT
UPDATE_INTERVAL=60
MAX_OPEN_POSITIONS=3
DAILY_LOSS_LIMIT=100
```

### Live Trading Configuration
```bash
# .env
XRPL_NETWORK=mainnet
BOT_MODE=live
WALLET_SEED=s████████████████████████████  # Your actual seed
WALLET_ADDRESS=r████████████████████████████  # Your address
TRADING_PAIR=XRP/USDT
MIN_TRADE_AMOUNT=20
MAX_TRADE_AMOUNT=500
STOP_LOSS_PERCENTAGE=3
TAKE_PROFIT_PERCENTAGE=6
MAX_OPEN_POSITIONS=2
MAX_POSITION_SIZE_PCT=10
DAILY_LOSS_LIMIT=50
LOG_LEVEL=INFO
```

### Development Configuration
```bash
# .env
XRPL_NETWORK=testnet
XRPL_WSS_URL=wss://s.altnet.rippletest.net:51233
XRPL_JSON_RPC_URL=https://s.altnet.rippletest.net:51234
BOT_MODE=paper_trading
LOG_LEVEL=DEBUG
UPDATE_INTERVAL=30
```

## Strategy-Specific Configuration

### Simple Momentum Strategy

The momentum strategy can be configured by modifying parameters in the code:

```python
SimpleMomentumStrategy({
    "lookback_period": 20,      # Price history length
    "momentum_threshold": 0.02,  # 2% price change threshold
    "volume_factor": 1.5,        # Volume multiplier
    "stop_loss_pct": 2.0,       # Stop loss percentage
    "take_profit_pct": 5.0,     # Take profit percentage
    "min_confidence": 0.6,       # Minimum confidence to trade
})
```

## Advanced Configuration

### Using Different Networks

**Mainnet** (Production):
```bash
XRPL_NETWORK=mainnet
```

**Testnet** (Development):
```bash
XRPL_NETWORK=testnet
```

**Custom Network**:
```bash
XRPL_NETWORK=custom
XRPL_WSS_URL=wss://your-custom-node.com:443
XRPL_JSON_RPC_URL=https://your-custom-node.com:51234
```

### Database Options

**SQLite** (Default):
```bash
DATABASE_URL=sqlite:///trading_bot.db
```

**PostgreSQL**:
```bash
DATABASE_URL=postgresql://user:password@localhost/trading_bot
```

**MySQL**:
```bash
DATABASE_URL=mysql://user:password@localhost/trading_bot
```

## Best Practices

1. **Start Small**: Use small position sizes when testing
2. **Use Paper Trading**: Always test strategies without real funds first
3. **Monitor Logs**: Set appropriate log levels for your use case
4. **Secure Credentials**: Never share or commit wallet seeds
5. **Regular Backups**: Backup your database and configuration
6. **Update Intervals**: Balance between API limits and data freshness

## Troubleshooting Configuration

### Common Issues

**"Invalid wallet seed"**
- Ensure seed starts with 's' and is valid
- Check for extra spaces or characters

**"Connection refused"**
- Verify network URLs are correct
- Check firewall settings
- Ensure internet connectivity

**"Insufficient balance"**
- Check MIN_TRADE_AMOUNT setting
- Verify wallet has 20+ XRP (reserve)
- Review MAX_POSITION_SIZE_PCT

**"Rate limit exceeded"**
- Increase UPDATE_INTERVAL
- Reduce number of concurrent operations
- Check exchange-specific limits