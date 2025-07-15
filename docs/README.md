# XRPL Trading Bot Documentation

Comprehensive documentation for the XRPL Trading Bot with real-time data collection, backtesting, and AI-powered trading strategies.

## Quick Start

```bash
# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start real-time data collection
python start_realtime_collection.py

# Or install as system service
sudo ./setup_systemd_service.sh
```

## Documentation Overview

### Getting Started
- [**INSTALLATION.md**](INSTALLATION.md) - Setting up the development environment
- [**QUICK_START.md**](QUICK_START.md) - Get up and running quickly
- [**CONFIGURATION.md**](CONFIGURATION.md) - Configuration options and settings

### Core Features
- [**DATA_COLLECTION.md**](DATA_COLLECTION.md) - Real-time and historical data collection
- [**BACKTESTING.md**](BACKTESTING.md) - Testing trading strategies with historical data
- [**ARCHITECTURE.md**](ARCHITECTURE.md) - System design and components

### Database
- [**DATABASE.md**](DATABASE.md) - Database schema and models
- [**data_collection_improvements.md**](data_collection_improvements.md) - Recent improvements

### Deployment & Operations
- [**DEPLOYMENT.md**](DEPLOYMENT.md) - Production deployment with systemd
- [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) - Common issues and solutions
- [**SECURITY.md**](SECURITY.md) - Security best practices

### Development
- [**API.md**](API.md) - API reference
- [**TESTING.md**](TESTING.md) - Testing guidelines
- [**CONTRIBUTING.md**](CONTRIBUTING.md) - How to contribute
- [**CHANGELOG.md**](CHANGELOG.md) - Version history

## Key Features

### Real-time Data Collection
- WebSocket monitoring of XRPL transactions
- Automatic gap detection and backfill
- Support for 10+ tokens including RLUSD
- Systemd service for 24/7 operation

### Data Storage
- PostgreSQL database with optimized schema
- Transaction-level granularity
- AMM pool snapshots and LP tracking
- 30-day historical data retention

### Monitoring
- Rich terminal dashboard
- Collection health metrics
- Gap detection and alerts
- Transaction rate monitoring

## Project Structure

```
xrpl_trading_bot/
├── src/
│   ├── config/          # Configuration and tokens
│   ├── data/            # Data collection modules
│   ├── database/        # Models and storage
│   ├── realtime/        # Real-time collection
│   ├── strategies/      # Trading strategies
│   └── utils/           # Helper utilities
├── docs/                # Documentation
├── scripts/             # Utility scripts
├── tests/               # Test suite
└── monitor_collection.py # Monitoring dashboard
```

## Collected Tokens

- **RLUSD** - Ripple USD stablecoin
- **UGA** - Utility token
- **BEAR** - Meme token
- **CULT** - Community token
- **OBEY** - Meme token
- **POSSE** - Community token
- **XJOY** - Entertainment token
- **GNOSIS** - Prediction token
- **FARM** - DeFi token
- **FML** - Community token

## System Requirements

- Python 3.8+
- PostgreSQL 12+
- 10GB+ disk space
- Systemd (for service deployment)
- Network access to XRPL nodes

---
Last updated: 2025-07-14