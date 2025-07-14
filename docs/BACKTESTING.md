# Backtesting Guide

## Overview

The backtesting system allows you to test trading strategies on historical data without risking real funds. It simulates trades based on historical price data and provides detailed performance metrics.

## System Requirements

Your system is well-equipped for backtesting:
- **CPU**: AMD Ryzen 9 7950X (16 cores) - Excellent for parallel strategy optimization
- **RAM**: 125GB - Can handle large datasets and multiple backtests simultaneously
- **Storage**: NVMe SSD - Fast data loading and caching
- **GPU**: AMD RX 6700 XT - Can be utilized for ML-based strategies with ROCm

## Quick Start

### Run a simple backtest:
```bash
./run_backtest.sh
```

### Custom backtest parameters:
```bash
python backtest.py --days 90 --timeframe 4h --balance 50000 --plot
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--strategy` | simple_momentum | Trading strategy to use |
| `--days` | 30 | Number of days to backtest |
| `--timeframe` | 1h | Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d) |
| `--balance` | 10000 | Initial balance in USD |
| `--commission` | 0.001 | Trading commission (0.001 = 0.1%) |
| `--use-cache` | False | Use cached historical data |
| `--save-cache` | True | Save fetched data to cache |
| `--save-results` | False | Save detailed results to CSV |
| `--plot` | False | Generate performance plots |
| `--no-display` | False | Save plots without displaying |

## Example Commands

### Basic backtest with plots:
```bash
python backtest.py --plot --save-results
```

### Long-term backtest (6 months):
```bash
python backtest.py --days 180 --timeframe 4h --plot
```

### High-frequency backtest:
```bash
python backtest.py --days 7 --timeframe 5m --balance 5000
```

### Backtest with different commission:
```bash
python backtest.py --commission 0.0025  # 0.25% commission
```

## Output Files

All output files are saved in the `data/` directory:

- **Historical Data Cache**: `xrp_usdt_{timeframe}_{days}d.csv`
- **Trade History**: `backtest_trades_{timestamp}.csv`
- **Equity Curve**: `backtest_equity_{timestamp}.csv`
- **Performance Plot**: `backtest_plot_{timestamp}.png`

## Performance Metrics

The backtest provides these key metrics:

- **Total P&L**: Absolute and percentage profit/loss
- **Win Rate**: Percentage of profitable trades
- **Average Win/Loss**: Average profit on winning/losing trades
- **Profit Factor**: Ratio of gross profit to gross loss
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns

## Data Sources

Currently using Binance for historical XRP/USDT data. The system fetches:
- OHLCV (Open, High, Low, Close, Volume) data
- Configurable timeframes from 1 minute to 1 day
- Automatic caching for faster subsequent runs

## Strategy Configuration

Modify strategy parameters in the code or create new strategies:

```python
# Example: Adjust momentum strategy parameters
strategy = SimpleMomentumStrategy({
    "lookback_period": 30,      # Increase lookback period
    "momentum_threshold": 0.03,  # Higher threshold (3%)
    "stop_loss_pct": 3.0,       # Wider stop loss
    "take_profit_pct": 8.0      # Higher profit target
})
```

## Tips for Effective Backtesting

1. **Start with longer timeframes** (1h, 4h) for more reliable signals
2. **Test multiple market conditions** - bull, bear, and sideways markets
3. **Consider transaction costs** - always include realistic commissions
4. **Validate with out-of-sample data** - test on recent data not used in development
5. **Watch for overfitting** - strategies that are too complex may not work live

## Limitations

- **No slippage modeling** - Real trades may have worse fills
- **Simplified order book** - Assumes infinite liquidity
- **No network delays** - Instant order execution assumed
- **Historical bias** - Past performance doesn't guarantee future results

## Next Steps

1. **Parameter Optimization**: Use the system's multi-core CPU to run parallel backtests with different parameters
2. **Walk-Forward Analysis**: Test strategy robustness over time
3. **Monte Carlo Simulation**: Add randomness to test strategy stability
4. **Multi-Asset Testing**: Expand beyond XRP/USDT

## Troubleshooting

### "No historical data available"
- Check internet connection
- Verify Binance API is accessible
- Try a different timeframe or shorter period

### Memory issues with large datasets
- Use larger timeframes (4h, 1d)
- Reduce the backtest period
- Enable data caching with `--use-cache`

### Slow backtests
- Enable caching: `--use-cache --save-cache`
- Use fewer days or larger timeframes
- Close other applications to free CPU