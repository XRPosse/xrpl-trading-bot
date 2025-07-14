# Installation Guide

## System Requirements

### Minimum Requirements
- Python 3.8 or higher
- 4GB RAM
- 10GB free disk space
- Internet connection

### Recommended Requirements
- Python 3.10+
- 16GB+ RAM
- SSD with 50GB+ free space
- Stable high-speed internet

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/xrpl-trading-bot.git
cd xrpl-trading-bot
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration with your preferred editor
nano .env  # or vim, code, etc.
```

### 5. Set Up XRPL Wallet (Optional for Backtesting)

For **Testnet** (recommended for testing):
1. Visit https://xrpl.org/xrp-testnet-faucet.html
2. Generate a test wallet
3. Copy the seed and address to your `.env` file

For **Mainnet** (real trading):
1. Use an existing XRPL wallet or create one securely
2. Ensure it has at least 20 XRP (account reserve)
3. **NEVER share your seed phrase**

### 6. Verify Installation

```bash
# Run tests
pytest

# Check if backtest works
python backtest.py --days 7 --timeframe 1h
```

## Platform-Specific Instructions

### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt update
sudo apt install python3-dev python3-pip python3-venv git

# Install TA-Lib (optional, for advanced indicators)
sudo apt install libta-lib0-dev
pip install TA-Lib
```

### macOS

```bash
# Using Homebrew
brew install python@3.10 git

# Install TA-Lib (optional)
brew install ta-lib
pip install TA-Lib
```

### Windows

1. Install Python from https://python.org
2. Install Git from https://git-scm.com
3. Use PowerShell or Git Bash for commands
4. Consider using WSL2 for better compatibility

## Docker Installation (Alternative)

```bash
# Build Docker image
docker build -t xrpl-trading-bot .

# Run with Docker
docker run -it --env-file .env xrpl-trading-bot
```

## GPU Support (Optional)

### For AMD GPUs (like RX 6700 XT):
```bash
# Install ROCm (Linux only)
# Follow: https://docs.amd.com/en/latest/deploy/linux/quick_start.html

# Install PyTorch with ROCm support
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.7
```

### For NVIDIA GPUs:
```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**
   ```bash
   # Ensure virtual environment is activated
   which python  # Should show venv path
   ```

2. **Permission Denied**
   ```bash
   # Use sudo for system packages (Linux/Mac)
   sudo apt install package-name
   ```

3. **SSL Certificate Errors**
   ```bash
   # Update certificates
   pip install --upgrade certifi
   ```

4. **Memory Errors During Backtest**
   - Use larger timeframes (4h, 1d)
   - Reduce backtest period
   - Close other applications

## Next Steps

1. Read the [Quick Start Guide](QUICK_START.md)
2. Configure your settings in `.env`
3. Run a backtest to verify everything works
4. Start with paper trading before using real funds

## Updating

To update to the latest version:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

Always check the [CHANGELOG.md](../CHANGELOG.md) for breaking changes.