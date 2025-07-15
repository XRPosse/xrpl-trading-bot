# Deployment Guide

## Prerequisites

- Python 3.8+ with virtual environment
- PostgreSQL database
- XRPL mainnet access (public nodes or private node)
- Systemd-based Linux system (Ubuntu/Debian recommended)
- Sufficient disk space for historical data (10GB+ recommended)

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/xrpl_trading

# XRPL Connection
XRPL_WSS_URL=wss://s1.ripple.com:443
```

### Production Settings
Create `.env.production`:
```bash
# Database
DATABASE_URL=postgresql://prod_user:secure_pass@localhost:5432/xrpl_prod

# XRPL Nodes (use multiple for redundancy)
XRPL_WSS_URL=wss://s1.ripple.com:443
XRPL_WSS_URL_BACKUP=wss://s2.ripple.com:443

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/xrpl-trading/collector.log
```

## Deployment Steps

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib

# Create application user (optional)
sudo useradd -m -s /bin/bash xrpl-bot
```

### 2. Database Setup

```bash
# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE xrpl_trading;
CREATE USER xrpl_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE xrpl_trading TO xrpl_user;
EOF

# Initialize database schema
python -c "from src.database.models import init_database; from src.config.settings import get_settings; init_database(get_settings().database_url)"
```

### 3. Application Deployment

```bash
# Clone repository
git clone https://github.com/your-org/xrpl-trading-bot.git
cd xrpl-trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python migrate_collection_logs.py
```

### 4. Real-time Data Collection Service

#### Install as systemd service:
```bash
# Install the service
sudo ./setup_systemd_service.sh

# The service will:
# - Start automatically on boot
# - Restart on failures
# - Log to systemd journal
```

#### Service Management:
```bash
# Check status
sudo systemctl status xrpl-realtime-collector

# View logs
sudo journalctl -u xrpl-realtime-collector -f

# Start/Stop/Restart
sudo systemctl start xrpl-realtime-collector
sudo systemctl stop xrpl-realtime-collector
sudo systemctl restart xrpl-realtime-collector

# Enable/Disable autostart
sudo systemctl enable xrpl-realtime-collector
sudo systemctl disable xrpl-realtime-collector
```

### 5. Monitoring Setup

#### Run monitoring dashboard:
```bash
# In a screen/tmux session
python monitor_collection.py
```

#### Or create a monitoring service:
```bash
# Create monitoring service file
sudo tee /etc/systemd/system/xrpl-monitor.service <<EOF
[Unit]
Description=XRPL Collection Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$PATH"
ExecStart=$(which python) $(pwd)/monitor_collection.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable xrpl-monitor
sudo systemctl start xrpl-monitor
```

## Production Considerations

### 1. Security
- Use strong database passwords
- Restrict database access to localhost
- Keep system and dependencies updated
- Use firewall rules to limit access

### 2. Performance
- Adjust PostgreSQL settings for your hardware
- Use connection pooling for database
- Monitor disk usage (data grows over time)
- Consider archiving old data

### 3. Reliability
- Set up automated backups
- Monitor service health
- Configure alerts for failures
- Use multiple XRPL nodes for redundancy

### 4. Backup Strategy
```bash
# Daily database backup
sudo tee /etc/cron.daily/xrpl-backup <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/xrpl"
DB_NAME="xrpl_trading"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR
pg_dump $DB_NAME | gzip > $BACKUP_DIR/xrpl_${DATE}.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

sudo chmod +x /etc/cron.daily/xrpl-backup
```

## Monitoring and Maintenance

### Health Checks
```bash
# Check collection gaps
python -c "
from src.database.models import DataCollectionLog, get_session, init_database
from src.config.settings import get_settings

engine = init_database(get_settings().database_url)
session = get_session(engine)

logs = session.query(DataCollectionLog).all()
for log in logs:
    print(f'{log.target}: Last ledger {log.last_processed_ledger}')
"

# Check disk usage
df -h /var/lib/postgresql
```

### Troubleshooting

#### Service won't start
```bash
# Check logs
sudo journalctl -u xrpl-realtime-collector -n 100

# Common issues:
# - Database connection failed
# - Python path incorrect
# - Missing dependencies
```

#### High memory usage
```bash
# Check process memory
ps aux | grep python

# Restart service
sudo systemctl restart xrpl-realtime-collector
```

#### Data gaps
```bash
# Manual backfill
python collect_full_history.py --days 1

# Check collection status
python monitor_collection.py
```

## Scaling Considerations

### Horizontal Scaling
- Run multiple collectors for different token sets
- Use database replication for read scaling
- Implement queue-based processing

### Vertical Scaling
- Increase database connection pool
- Optimize PostgreSQL configuration
- Use faster storage (SSD/NVMe)

## Updates and Maintenance

### Updating the Application
```bash
# Stop service
sudo systemctl stop xrpl-realtime-collector

# Pull updates
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations if needed
python migrate_collection_logs.py

# Restart service
sudo systemctl start xrpl-realtime-collector
```

### Regular Maintenance Tasks
1. **Weekly**: Check logs for errors
2. **Monthly**: Review disk usage and database size
3. **Quarterly**: Update dependencies and system packages
4. **Yearly**: Archive old data, review scaling needs

---
Last updated: 2025-07-14