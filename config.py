# =============================================================================
# PACIFICA TRADING BOT CONFIGURATION
# =============================================================================

import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file (or custom path)
dotenv_path = os.getenv('DOTENV_PATH', '.env')
load_dotenv(dotenv_path)

def get_env_str(key: str, default: str = "") -> str:
    """Get string environment variable"""
    return os.getenv(key, default)

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

# =============================================================================
# PACIFICA API CONFIGURATION
# =============================================================================
MAINNET_URL = "https://api.pacifica.fi/api/v1"
WS_URL = "wss://ws.pacifica.fi/ws"

# Private key for Solana wallet (base58 encoded)
PRIVATE_KEY = get_env_str("PACIFICA_PRIVATE_KEY")

# =============================================================================
# TRADING CONFIGURATION
# =============================================================================
# Trading intervals (seconds)
MIN_TRADE_INTERVAL = get_env_int("MIN_TRADE_INTERVAL", 30)
MAX_TRADE_INTERVAL = get_env_int("MAX_TRADE_INTERVAL", 300)

# Risk management
MAX_DAILY_TRADES = get_env_int("MAX_DAILY_TRADES", 50)
ENABLE_RISK_LIMITS = get_env_bool("ENABLE_RISK_LIMITS", True)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL = get_env_str("LOG_LEVEL", "INFO")
LOG_TO_FILE = get_env_bool("LOG_TO_FILE", True)
LOG_FILE = get_env_str("LOG_FILE", "pacifica_trading_bot.log")

# =============================================================================
# MARKET CONFIGURATION
# =============================================================================
# Markets to exclude from trading
EXCLUDED_MARKETS: List[str] = []

# Preferred markets (empty = all available)
PREFERRED_MARKETS: List[str] = []

# Default slippage percentage
DEFAULT_SLIPPAGE = get_env_float("DEFAULT_SLIPPAGE", 0.5)

# Order timeout (seconds)
ORDER_TIMEOUT = get_env_int("ORDER_TIMEOUT", 30)

# =============================================================================
# PROXY CONFIGURATION (MANDATORY)
# =============================================================================
# Proxy is REQUIRED for this bot - always set to true
USE_PROXY = get_env_bool("USE_PROXY", True)

# REQUIRED: Proxy URL with authentication
# Format: http://username:password@host:port
PROXY_URL = get_env_str("PROXY_URL")

# =============================================================================
# TRADING PAIRS AND LEVERAGE
# =============================================================================
# Allowed trading pairs (Pacifica symbols)
ALLOWED_TRADING_PAIRS = ["BTC", "ETH", "HYPE", "SOL", "BNB"]

# Manual leverage settings per pair (leverage multiplier)
MANUAL_LEVERAGE: Dict[str, float] = {
    "BTC": 5.0,      # Standard leverage for BTC
    "ETH": 5.0,      # Standard leverage for ETH
    "HYPE": 5.0,     # Standard leverage for HYPE
    "SOL": 5.0,      # Standard leverage for SOL
    "BNB": 5.0,      # Standard leverage for BNB
}

# Margin mode (0 = cross, 1 = isolated)
MARGIN_MODE = get_env_int("MARGIN_MODE", 0)

# =============================================================================
# POSITION SIZING - PERCENTAGE BASED
# =============================================================================
# Account balance for percentage calculations
ACCOUNT_BALANCE = get_env_float("ACCOUNT_BALANCE", 500.0)

# Position size as percentage of account balance
MIN_POSITION_PERCENT = get_env_float("MIN_POSITION_PERCENT", 50.0)
MAX_POSITION_PERCENT = get_env_float("MAX_POSITION_PERCENT", 80.0)

# =============================================================================
# POSITION MANAGEMENT - DYNAMIC HOLD TIMES
# =============================================================================
# Dynamic random hold time range (minutes) - bot picks random time between min/max
MIN_POSITION_HOLD_MINUTES = get_env_int("MIN_POSITION_HOLD_MINUTES", 3)
MAX_POSITION_HOLD_MINUTES = get_env_int("MAX_POSITION_HOLD_MINUTES", 10)

# Logging and timing configuration
POSITION_LOG_INTERVAL_SECONDS = get_env_int("POSITION_LOG_INTERVAL_SECONDS", 120)  # Log every 2 minutes
MIN_WAIT_BETWEEN_POSITIONS = get_env_int("MIN_WAIT_BETWEEN_POSITIONS", 10)  # Minimum wait (seconds)
MAX_WAIT_BETWEEN_POSITIONS = get_env_int("MAX_WAIT_BETWEEN_POSITIONS", 50)  # Maximum wait (seconds)

# Startup configuration
CLOSE_EXISTING_POSITIONS_ON_START = get_env_bool("CLOSE_EXISTING_POSITIONS_ON_START", True)  # Close existing positions before starting

# Legacy support (deprecated - use MIN/MAX instead)
POSITION_HOLD_MINUTES = get_env_int("POSITION_HOLD_MINUTES", 0)  # 0 = use dynamic
SINGLE_POSITION_MODE = get_env_bool("SINGLE_POSITION_MODE", True)

# =============================================================================
# VALIDATION
# =============================================================================
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Validate API credentials
    if not PRIVATE_KEY:
        errors.append("PACIFICA_PRIVATE_KEY is required")
    
    if PRIVATE_KEY and len(PRIVATE_KEY) < 32:
        errors.append("PACIFICA_PRIVATE_KEY appears to be invalid (too short)")
    
    # Validate trading intervals
    if MIN_TRADE_INTERVAL >= MAX_TRADE_INTERVAL:
        errors.append("MIN_TRADE_INTERVAL must be less than MAX_TRADE_INTERVAL")
    
    # Validate position sizing
    if MIN_POSITION_PERCENT >= MAX_POSITION_PERCENT:
        errors.append("MIN_POSITION_PERCENT must be less than MAX_POSITION_PERCENT")
    
    if MIN_POSITION_PERCENT <= 0 or MAX_POSITION_PERCENT <= 0:
        errors.append("Position percentages must be greater than 0")
    
    if MAX_POSITION_PERCENT > 100:
        errors.append("MAX_POSITION_PERCENT cannot exceed 100%")
    
    if ACCOUNT_BALANCE <= 0:
        errors.append("ACCOUNT_BALANCE must be greater than 0")
    
    # Validate hold times
    if MIN_POSITION_HOLD_MINUTES >= MAX_POSITION_HOLD_MINUTES:
        errors.append("MIN_POSITION_HOLD_MINUTES must be less than MAX_POSITION_HOLD_MINUTES")
    
    if MIN_POSITION_HOLD_MINUTES <= 0:
        errors.append("MIN_POSITION_HOLD_MINUTES must be greater than 0")
    
    # Validate timing settings
    if POSITION_LOG_INTERVAL_SECONDS <= 0:
        errors.append("POSITION_LOG_INTERVAL_SECONDS must be greater than 0")
    
    if MIN_WAIT_BETWEEN_POSITIONS >= MAX_WAIT_BETWEEN_POSITIONS:
        errors.append("MIN_WAIT_BETWEEN_POSITIONS must be less than MAX_WAIT_BETWEEN_POSITIONS")
    
    if MIN_WAIT_BETWEEN_POSITIONS <= 0:
        errors.append("MIN_WAIT_BETWEEN_POSITIONS must be greater than 0")
    
    # Validate proxy configuration (MANDATORY)
    if USE_PROXY and not PROXY_URL:
        errors.append("PROXY_URL is required when USE_PROXY is true. Proxy usage is mandatory for this bot.")
    
    if USE_PROXY and PROXY_URL:
        if not PROXY_URL.startswith(('http://', 'https://')):
            errors.append("PROXY_URL must start with http:// or https://")
        if '@' not in PROXY_URL:
            errors.append("PROXY_URL must include authentication credentials (username:password@host:port)")
        if "proxy.example.com" in PROXY_URL or "username:password" in PROXY_URL:
            errors.append("PROXY_URL is still using example values. Please update with your actual proxy credentials.")
    
    # Validate trading pairs and leverage
    if not ALLOWED_TRADING_PAIRS:
        errors.append("ALLOWED_TRADING_PAIRS cannot be empty")
    
    for pair in ALLOWED_TRADING_PAIRS:
        if pair not in MANUAL_LEVERAGE:
            errors.append(f"Missing leverage setting for {pair} in MANUAL_LEVERAGE")
    
    for pair, leverage in MANUAL_LEVERAGE.items():
        if leverage <= 0 or leverage > 100:
            errors.append(f"Invalid leverage {leverage} for {pair}. Must be between 0 and 100")
    
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ValueError(error_msg)

# Validate configuration on import
validate_config()

# =============================================================================
# CONFIGURATION SUMMARY (for logging)
# =============================================================================
def get_config_summary() -> str:
    """Get a safe configuration summary for logging (no sensitive data)"""
    # Determine hold time display
    if POSITION_HOLD_MINUTES > 0:
        hold_time_str = f"{POSITION_HOLD_MINUTES} minutes (fixed - legacy)"
    else:
        hold_time_str = f"{MIN_POSITION_HOLD_MINUTES}-{MAX_POSITION_HOLD_MINUTES} minutes (pure random)"
    
    return f"""
Configuration Summary:
- Account Balance: ${ACCOUNT_BALANCE}
- Position Risk: {MIN_POSITION_PERCENT}%-{MAX_POSITION_PERCENT}%
- Trading Pairs: {', '.join(ALLOWED_TRADING_PAIRS)}
- Leverage Settings: {', '.join(f'{k}:{v}x' for k, v in MANUAL_LEVERAGE.items())}
- Position Hold Time: {hold_time_str}
- Position Logging: Every {POSITION_LOG_INTERVAL_SECONDS} seconds
- Wait Between Positions: {MIN_WAIT_BETWEEN_POSITIONS}-{MAX_WAIT_BETWEEN_POSITIONS} seconds
- Close Existing Positions: {CLOSE_EXISTING_POSITIONS_ON_START}
- Single Position Mode: {SINGLE_POSITION_MODE}
- Proxy Enabled: {USE_PROXY}
- Log Level: {LOG_LEVEL}
"""
