# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Real-time AMM state tracking with transaction-level granularity
- AMMStateTracker module for monitoring pool reserves
- Periodic AMM snapshots (every 30 minutes)
- AMM data visualization tools
- Enhanced monitoring dashboard with AMM metrics
- Systemd service configuration for 24/7 operation
- Automatic gap detection and backfill up to 30 days
- Full transaction history collection for all tokens
- Support for 10 tokens including RLUSD, UGA, BEAR, etc.

### Changed
- Updated real-time collector to capture AMM state changes
- Enhanced collection manager with AMM snapshot scheduling
- Improved database schema with LP token support
- Updated documentation with AMM tracking details

### Fixed
- Websocket payload limit issues with batch processing
- Hardcoded ledger number calculations
- BEAR token code formatting issue
- Database migration for collection progress tracking

## [0.2.0] - 2025-07-14

### Added
- Real-time XRPL data collection system
- PostgreSQL database integration
- Transaction metadata processing
- AMM pool state tracking (711+ snapshots collected)
- Data export functionality (CSV, Parquet)
- Rich terminal monitoring dashboard

### Data Collection Stats
- 67,000+ transactions collected
- 10 AMM pools monitored
- 30-day historical data retention
- RLUSD identified as most active token (31,000+ transactions)

## [0.1.0] - 2025-07-01

### Added
- Initial project setup
- Basic XRPL connectivity
- Token configuration system
- Database models design

---

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)