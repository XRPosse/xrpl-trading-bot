# Scripts Directory

Utility scripts for data collection, analysis, and maintenance.

## Subdirectories

### data_collection/
Scripts for collecting historical and real-time data:
- `collect_amm_history.py` - Collect historical AMM state changes
- `collect_amm_state_changes.py` - Efficient AMM state change collection

### visualization/
Data analysis and visualization tools:
- `visualize_amm_history.py` - Create charts and analysis of AMM pool history

### migration/
Database migration scripts:
- `migrate_collection_logs.py` - Update database schema for real-time collection

## Usage

Most scripts can be run directly:
```bash
python scripts/data_collection/collect_amm_history.py
python scripts/visualization/visualize_amm_history.py
```

For database migrations:
```bash
python scripts/migration/migrate_collection_logs.py
```