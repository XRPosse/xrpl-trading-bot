#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run backtest with default parameters
echo "Running XRP/USDT backtest for the last 30 days..."
echo "================================================="

python backtest.py \
    --strategy simple_momentum \
    --days 30 \
    --timeframe 1h \
    --balance 10000 \
    --use-cache \
    --save-results \
    --plot \
    "$@"