# Quick Start Guide

Get your XRPL trading bot running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Git installed
- Basic command line knowledge

## 5-Minute Setup

### Step 1: Clone and Enter Directory
```bash
git clone https://github.com/yourusername/xrpl-trading-bot.git
cd xrpl-trading-bot
```

### Step 2: Quick Install
```bash
# One-line setup (Linux/Mac)
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Windows
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
```

### Step 3: Configure
```bash
cp .env.example .env
# No need to edit for backtesting!
```

### Step 4: Run Your First Backtest
```bash
./run_backtest.sh
# or
python backtest.py --days 30 --plot
```

That's it! You should see backtest results in your terminal.

## What Just Happened?

1. You cloned the trading bot code
2. Created a Python virtual environment
3. Installed all dependencies
4. Ran a backtest on 30 days of XRP/USDT data
5. Generated performance metrics

## Next Steps

### 1. Explore Backtesting
Try different parameters:
```bash
# Test on 90 days with 4-hour candles
python backtest.py --days 90 --timeframe 4h --plot

# Test with $50,000 starting balance
python backtest.py --balance 50000 --save-results
```

### 2. Configure for Paper Trading
Edit `.env`:
```bash
BOT_MODE=paper_trading
TRADING_PAIR=XRP/USDT
UPDATE_INTERVAL=60
```

Run paper trading:
```bash
python main.py
```

### 3. Understand the Output

**Backtest Metrics:**
- **Total P&L**: Your profit/loss
- **Win Rate**: Percentage of profitable trades
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns (higher is better)

**Files Created:**
- `data/` - Historical data cache and results
- `logs/` - Bot activity logs

## Common Commands

```bash
# Backtest with visualization
python backtest.py --plot

# Paper trading
python main.py

# Run tests
pytest

# Format code
black .

# Check code style
flake8 .
```

## Quick Tips

1. **Start with backtesting** - No wallet or funds needed
2. **Use paper trading** - Test strategies in real-time safely
3. **Read the logs** - They contain valuable debugging info
4. **Small position sizes** - When you eventually go live
5. **Monitor regularly** - Even automated bots need supervision

## Troubleshooting Quick Fixes

**"No module named 'xrpl'"**
```bash
pip install -r requirements.txt
```

**"Permission denied"**
```bash
chmod +x run_backtest.sh
```

**"No historical data"**
```bash
# Check internet connection
# Try shorter time period
python backtest.py --days 7
```

## Getting Help

- Check [Documentation](README.md)
- See [Troubleshooting Guide](TROUBLESHOOTING.md)
- Create an [Issue](https://github.com/yourusername/xrpl-trading-bot/issues)

## Ready for More?

- [Backtesting Guide](BACKTESTING.md) - Deep dive into backtesting
- [Configuration Guide](CONFIGURATION.md) - All settings explained
- [Strategy Development](STRATEGIES.md) - Create custom strategies