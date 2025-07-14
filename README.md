# XRPL Trading Bot

An advanced Python-based automated trading bot for the XRP Ledger (XRPL) with backtesting capabilities, multiple trading strategies, and support for both paper and live trading modes.

## Features

- **XRPL Integration**: Direct connection to XRP Ledger mainnet/testnet for decentralized trading
- **Backtesting Engine**: Comprehensive historical data analysis with performance metrics
- **Multiple Trading Strategies**: Modular strategy system with momentum-based strategies
- **Paper Trading Mode**: Test strategies in real-time without risking funds
- **Live Trading**: Automated trading with real funds (use with caution)
- **Risk Management**: Built-in stop loss, take profit, position sizing, and daily loss limits
- **Performance Analytics**: Detailed metrics including Sharpe ratio, drawdown, and profit factor
- **Data Management**: Automatic caching and efficient data fetching from multiple sources
- **Visualization**: Performance plots and equity curves
- **Configurable**: Environment-based configuration for easy deployment
- **Comprehensive Logging**: Detailed logging with Loguru for debugging and monitoring
- **Async Architecture**: High-performance asynchronous design for real-time processing

## Project Structure

```
xrpl_trading_bot/
├── src/
│   ├── bot/              # Main trading bot logic
│   ├── config/           # Configuration and settings
│   ├── exchanges/        # XRPL client and exchange interfaces
│   ├── strategies/       # Trading strategies
│   └── utils/           # Utility functions
├── tests/               # Test suites
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment configuration template
```

## Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd xrpl_trading_bot
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up wallet (for testnet)**
- Go to https://xrpl.org/xrp-testnet-faucet.html
- Generate a test wallet
- Copy the seed and address to your .env file

## Configuration

Key configuration options in `.env`:

- `XRPL_NETWORK`: Network to connect to (testnet/mainnet)
- `BOT_MODE`: Trading mode (paper_trading/live)
- `STRATEGY`: Trading strategy to use
- `TRADING_PAIR`: Currency pair to trade
- `MIN_TRADE_AMOUNT`: Minimum trade size
- `MAX_TRADE_AMOUNT`: Maximum trade size
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage

## Quick Start

### 1. Run a Backtest (No Wallet Required)
```bash
# Quick backtest with last 30 days of data
./run_backtest.sh

# Custom backtest parameters
python backtest.py --days 90 --timeframe 4h --balance 50000 --plot
```

### 2. Paper Trading (Recommended for testing)
```bash
# Ensure BOT_MODE=paper_trading in .env
python main.py
```

### 3. Live Trading (Use with caution)
```bash
# Ensure BOT_MODE=live in .env
# Ensure wallet credentials are set
# Start with small amounts!
python main.py
```

## Usage Examples

### Backtesting
```bash
# Test strategy on 6 months of data
python backtest.py --days 180 --timeframe 1h --plot --save-results

# High-frequency backtest
python backtest.py --days 7 --timeframe 5m --balance 5000

# Backtest with custom commission
python backtest.py --commission 0.0025  # 0.25% commission
```

### Strategy Testing
```bash
# Paper trade with momentum strategy
BOT_MODE=paper_trading python main.py

# Monitor specific trading pair
TRADING_PAIR=XRP/USD python main.py
```

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black .

# Check code style
flake8 .

# Type checking
mypy src/
```

## Trading Strategies

### Simple Momentum Strategy
The included momentum strategy trades based on:
- Price momentum over a lookback period
- Trend strength analysis
- Volume confirmation
- Configurable thresholds and risk parameters

### Creating Custom Strategies
1. Inherit from `BaseStrategy` class
2. Implement the `analyze()` method
3. Return trading signals (BUY/SELL/HOLD)
4. Register strategy in main.py

## Safety Features

- **Paper Trading Mode**: Test without real funds
- **Position Limits**: Maximum open positions cap
- **Daily Loss Limits**: Automatic shutdown on excessive losses
- **Stop Loss/Take Profit**: Automated risk management
- **Balance Checks**: Prevents trades exceeding available balance

## Monitoring

The bot logs:
- Trading signals and executions
- Balance and position updates
- Market data and spreads
- Errors and warnings

Logs are stored in `logs/` directory with rotation.

## Development

### Adding New Features

1. **New Strategy**:
   - Create new file in `src/strategies/`
   - Inherit from `BaseStrategy`
   - Implement required methods

2. **New Exchange**:
   - Create new file in `src/exchanges/`
   - Implement exchange interface
   - Add to bot configuration

3. **New Indicators**:
   - Add to `src/utils/indicators.py`
   - Use in strategy analysis

## Deployment

### Local Deployment
```bash
# Use screen or tmux for persistent sessions
screen -S trading_bot
python main.py
# Detach with Ctrl+A, D
```

### Docker Deployment
```bash
# Build image
docker build -t xrpl-trading-bot .

# Run container
docker run -d --name xrpl-bot --env-file .env xrpl-trading-bot
```

### Systemd Service
Create `/etc/systemd/system/xrpl-trading-bot.service`:
```ini
[Unit]
Description=XRPL Trading Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/xrpl_trading_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Security Considerations

- **Never commit `.env` files** with real credentials
- **Use separate wallets** for testing and production
- **Start with small amounts** when going live
- **Monitor regularly** for unexpected behavior
- **Keep dependencies updated** for security patches

## Troubleshooting

### Connection Issues
- Check network URLs in configuration
- Verify internet connectivity
- Check XRPL network status

### Trading Issues
- Verify wallet has sufficient XRP balance
- Check minimum reserve requirements (20 XRP)
- Review logs for specific errors

### Performance Issues
- Adjust `UPDATE_INTERVAL` for less frequent updates
- Check system resources
- Review strategy complexity

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Ensure code passes quality checks
5. Submit pull request

## Documentation

- [Backtesting Guide](docs/BACKTESTING.md) - Detailed backtesting instructions
- [Project Overview](docs/PROJECT.md) - Technical design and architecture
- [API Reference](docs/API.md) - Code documentation (coming soon)
- [Strategy Development](docs/STRATEGIES.md) - Creating custom strategies (coming soon)

## Performance Requirements

### Minimum Requirements
- Python 3.8+
- 4GB RAM
- 10GB storage
- Stable internet connection

### Recommended (Your System Exceeds These)
- Multi-core CPU (✓ Ryzen 9 7950X)
- 16GB+ RAM (✓ 125GB available)
- SSD storage (✓ NVMe)
- GPU for ML strategies (✓ RX 6700 XT)

## Roadmap

- [x] Core trading bot framework
- [x] XRPL mainnet integration
- [x] Backtesting engine
- [x] Simple momentum strategy
- [ ] Advanced technical indicators
- [ ] Machine learning strategies
- [ ] Multi-exchange support
- [ ] Web dashboard
- [ ] Mobile notifications
- [ ] Strategy marketplace

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**IMPORTANT**: This trading bot is provided for educational and research purposes only. 

- Trading cryptocurrencies carries significant financial risk
- Past performance does not guarantee future results
- Never trade more than you can afford to lose
- Always test thoroughly with paper trading before using real funds
- The authors are not responsible for any financial losses

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/xrpl-trading-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/xrpl-trading-bot/discussions)
- **Documentation**: [Full Docs](docs/)