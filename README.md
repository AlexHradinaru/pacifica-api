# Pacifica Random Trading Bot

A sophisticated automated trading bot for Pacifica Finance with advanced features including race condition fixes, dynamic position management, and comprehensive risk controls.

## ⚠️ **MANDATORY PROXY REQUIREMENT**

**This bot REQUIRES a proxy server to function properly. You MUST configure a valid proxy in your `.env` file before running the bot.**

## 🚀 Features

- **Random Trading**: Automatically places random long/short positions across multiple trading pairs
- **Dynamic Position Management**: Configurable hold times with intelligent position lifecycle management
- **Percentage-Based Position Sizing**: Risk management based on account balance percentages
- **Single Position Mode**: Maintains only one position at a time with automatic closing
- **Race Condition Protection**: Robust error handling and state management
- **Automatic Position Cleanup**: Closes existing positions on startup (configurable)
- **Process Management**: Built-in process isolation and management scripts
- **Comprehensive Logging**: Detailed logging with configurable levels and file output
- **Graceful Shutdown**: Signal handling for clean bot termination
- **Proxy Support**: Full proxy integration for secure trading

## 📋 Prerequisites

- Python 3.7+
- Solana wallet with private key
- Pacifica Finance account
- **Proxy server (MANDATORY)**

## 🛠️ Installation

1. **Clone and setup**:
   ```bash
   cd python-sdk
   pip3 install -r requirements.txt
   ```

2. **Install additional dependencies**:
   ```bash
   pip3 install python-dotenv psutil
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

## ⚙️ Configuration

### Required Configuration

Edit `.env` file with your settings:

```env
# REQUIRED: Your Solana wallet private key (base58 encoded)
PACIFICA_PRIVATE_KEY=your_base58_private_key_here

# REQUIRED: Proxy server (MANDATORY)
USE_PROXY=true
PROXY_URL=http://username:password@proxy.example.com:8080

# Account balance for percentage calculations
ACCOUNT_BALANCE=500.0

# Position sizing (percentage of account balance)
MIN_POSITION_PERCENT=50.0
MAX_POSITION_PERCENT=80.0
```

### Trading Pairs and Leverage

The bot trades these pairs with configured leverage:
- **BTC**: 5x leverage
- **ETH**: 5x leverage  
- **HYPE**: 5x leverage
- **SOL**: 5x leverage
- **BNB**: 5x leverage

### Dynamic Hold Times

Positions are held for a random duration between:
- **Minimum**: 3 minutes (configurable)
- **Maximum**: 10 minutes (configurable)

## 🚀 Usage

### Quick Start

```bash
# Start the bot
python3 start_bot.py start

# Check status
python3 start_bot.py status

# View logs
python3 start_bot.py logs

# Stop the bot
python3 start_bot.py stop
```

### Direct Execution

```bash
# Run directly (not recommended for production)
python3 pacifica_trading_bot.py
```

### Process Management Commands

```bash
python3 start_bot.py start     # Start bot in background
python3 start_bot.py stop      # Gracefully stop bot
python3 start_bot.py status    # Check if running + stats
python3 start_bot.py logs      # Follow logs in real-time
python3 start_bot.py restart   # Stop and start bot
```

## 📊 Bot Behavior

### Single Position Mode (Default)

1. **Startup**: Checks for and closes any existing positions (if enabled)
2. **Trading Cycle**:
   - Opens one random position (long/short, random pair, percentage-based size)
   - Holds position for random duration (3-10 minutes)
   - Closes position automatically
   - Waits random time (10-50 seconds) before next position
3. **Logging**: Position status logged every 2 minutes
4. **Shutdown**: Graceful cleanup on termination signals

### Position Sizing Logic

- **Risk Calculation**: Random percentage (50-80%) of account balance
- **Leverage Application**: Multiplied by pair-specific leverage
- **Size Calculation**: `(Risk Amount × Leverage) ÷ Asset Price`
- **Safety Cap**: Maximum 80% of account balance per position

### Example Position Calculation

```
Account Balance: $500
Random Risk: 60% = $300
BTC Leverage: 5x
Notional Value: $300 × 5 = $1,500
BTC Price: $65,000
Position Size: $1,500 ÷ $65,000 = 0.023 BTC
```

## 📁 Project Structure

```
python-sdk/
├── pacifica_trading_bot.py    # Main bot logic
├── start_bot.py               # Process management script
├── config.py                  # Configuration management
├── env.example                # Environment template
├── common/                    # Pacifica SDK utilities
│   ├── constants.py           # API endpoints
│   └── utils.py               # Signing utilities
├── rest/                      # REST API examples
└── ws/                        # WebSocket examples
```

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_POSITION_HOLD_MINUTES` | 3 | Minimum hold time |
| `MAX_POSITION_HOLD_MINUTES` | 10 | Maximum hold time |
| `POSITION_LOG_INTERVAL_SECONDS` | 120 | Position logging frequency |
| `MIN_WAIT_BETWEEN_POSITIONS` | 10 | Minimum wait between positions |
| `MAX_WAIT_BETWEEN_POSITIONS` | 50 | Maximum wait between positions |
| `CLOSE_EXISTING_POSITIONS_ON_START` | true | Close positions on startup |
| `DEFAULT_SLIPPAGE` | 0.5 | Slippage tolerance (%) |
| `LOG_LEVEL` | INFO | Logging level |

### Risk Management

- **Daily Trade Limit**: 50 trades per day (configurable)
- **Position Limits**: One position at a time in single position mode
- **Slippage Protection**: Configurable slippage tolerance
- **Process Isolation**: File locks prevent multiple instances

## 🛡️ Security Features

- **Environment Variables**: Sensitive data stored in `.env` file
- **Process Locks**: Prevents multiple bot instances
- **Graceful Shutdown**: Clean resource cleanup
- **Error Handling**: Comprehensive exception management
- **Proxy Support**: Secure connection routing

## 📝 Logging

Logs include:
- Trade execution details
- Position lifecycle events
- Error messages and debugging info
- Performance statistics
- Configuration summaries

Log files: `pacifica_trading_bot.log`

## ⚠️ Risk Disclaimer

**This bot is for educational and testing purposes. Cryptocurrency trading involves substantial risk of loss. Use at your own risk.**

- Test with small amounts first
- Monitor bot behavior closely
- Understand the risks of automated trading
- Ensure proper risk management settings

## 🔧 Troubleshooting

### Common Issues

1. **"Proxy URL is required"**
   - Configure valid proxy in `.env` file
   - Ensure proxy format: `http://username:password@host:port`

2. **"Bot is already running"**
   - Check status: `python3 start_bot.py status`
   - Stop existing instance: `python3 start_bot.py stop`

3. **"Private key invalid"**
   - Ensure base58 encoded Solana private key
   - Check key length and format

4. **Connection errors**
   - Verify proxy configuration
   - Check internet connectivity
   - Validate Pacifica API access

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

## 📞 Support

For issues and questions:
1. Check the logs: `python3 start_bot.py logs`
2. Verify configuration in `.env`
3. Test with minimal position sizes
4. Review Pacifica API documentation

## 📄 License

This project is based on the Pacifica Python SDK examples and follows the same licensing terms.