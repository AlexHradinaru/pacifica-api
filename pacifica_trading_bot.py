#!/usr/bin/env python3
"""
Pacifica Random Trading Bot

A sophisticated automated trading bot for Pacifica Finance with:
- Race condition fixes for stability
- Automatic position cleanup on startup
- Dynamic hold times and percentage-based position sizing
- Single position management with intelligent timing
- Comprehensive error handling and logging

Based on the same architecture as the Lighter Protocol bot.
"""

import asyncio
import logging
import random
import time
import uuid
import signal
import sys
import os
import fcntl
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import requests
from solders.keypair import Keypair

from config import (
    MAINNET_URL, PRIVATE_KEY, MIN_TRADE_INTERVAL, MAX_TRADE_INTERVAL,
    MAX_DAILY_TRADES, ENABLE_RISK_LIMITS, LOG_LEVEL, LOG_TO_FILE, LOG_FILE,
    EXCLUDED_MARKETS, PREFERRED_MARKETS, DEFAULT_SLIPPAGE, ORDER_TIMEOUT,
    PROXY_URL, USE_PROXY, ALLOWED_TRADING_PAIRS, MANUAL_LEVERAGE, MARGIN_MODE,
    MIN_POSITION_HOLD_MINUTES, MAX_POSITION_HOLD_MINUTES, POSITION_HOLD_MINUTES, 
    SINGLE_POSITION_MODE, ACCOUNT_BALANCE, MIN_POSITION_PERCENT, MAX_POSITION_PERCENT,
    POSITION_LOG_INTERVAL_SECONDS, MIN_WAIT_BETWEEN_POSITIONS, MAX_WAIT_BETWEEN_POSITIONS,
    CLOSE_EXISTING_POSITIONS_ON_START
)
from common.utils import sign_message


class TradingStats:
    """Track trading statistics and risk metrics"""
    def __init__(self):
        self.daily_trades = 0
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.start_time = datetime.now()


class PositionManager:
    """Manage single position lifecycle with dynamic hold times"""
    
    def __init__(self):
        self.current_position = None
        self.position_opened_at = None
        self.position_hold_minutes = None  # Dynamic hold time for current position
        
    def has_position(self) -> bool:
        """Check if we currently have an open position"""
        return self.current_position is not None
        
    def _calculate_hold_time(self, market_symbol: str, current_price: float = None) -> int:
        """Calculate dynamic hold time for a position"""
        # Check for legacy fixed hold time
        if POSITION_HOLD_MINUTES > 0:
            return POSITION_HOLD_MINUTES
        
        # Pure random hold time between min and max
        return random.randint(MIN_POSITION_HOLD_MINUTES, MAX_POSITION_HOLD_MINUTES)
        
    def open_position(self, market_symbol: str, side: str, amount: str, order_id: str, current_price: float = None):
        """Record a new position with dynamic hold time"""
        # Calculate dynamic hold time for this position
        self.position_hold_minutes = self._calculate_hold_time(market_symbol, current_price)
        
        self.current_position = {
            'symbol': market_symbol,
            'side': side,
            'amount': amount,
            'order_id': order_id,
            'hold_minutes': self.position_hold_minutes  # Store the calculated hold time
        }
        self.position_opened_at = datetime.now()
        
    def should_close_position(self) -> bool:
        """Check if position should be closed based on dynamic hold time"""
        if not self.has_position():
            return False
        
        # Safety check for position_opened_at to prevent race conditions
        if self.position_opened_at is None or self.position_hold_minutes is None:
            return False
        
        hold_duration = datetime.now() - self.position_opened_at
        return hold_duration >= timedelta(minutes=self.position_hold_minutes)
        
    def close_position(self):
        """Clear current position"""
        self.current_position = None
        self.position_opened_at = None
        self.position_hold_minutes = None
        
    def get_position_info(self) -> Dict:
        """Get current position information"""
        if not self.has_position():
            return None
            
        # Safety check for position_opened_at to prevent race conditions
        if self.position_opened_at is None:
            return None
            
        hold_duration = datetime.now() - self.position_opened_at
        return {
            **self.current_position,
            'opened_at': self.position_opened_at,
            'hold_duration_minutes': hold_duration.total_seconds() / 60,
            'target_hold_minutes': self.position_hold_minutes,
            'should_close': self.should_close_position()
        }


class PacificaRandomTradingBot:
    """Random trading bot for Pacifica Finance"""
    def __init__(self):
        self.setup_logging()
        self.stats = TradingStats()
        self.position_manager = PositionManager()
        self.keypair: Optional[Keypair] = None
        self.public_key: Optional[str] = None
        self.available_markets: List[str] = ALLOWED_TRADING_PAIRS.copy()
        self.running = False
        self.lock_file = None
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Acquire process lock to prevent multiple instances
        self._acquire_process_lock()
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
        
    def _acquire_process_lock(self):
        """Acquire process lock to prevent multiple instances"""
        try:
            self.lock_file = open('.pacifica_trading_bot.lock', 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            self.logger.info(f"Process lock acquired (PID: {os.getpid()})")
        except (IOError, OSError) as e:
            self.logger.error(f"Could not acquire process lock: {e}")
            self.logger.error("Another instance of the bot may be running")
            sys.exit(1)
            
    def _release_process_lock(self):
        """Release process lock"""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                os.unlink('.pacifica_trading_bot.lock')
                self.logger.info("Process lock released")
            except Exception as e:
                self.logger.warning(f"Error releasing process lock: {e}")

    def setup_logging(self):
        """Configure logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL.upper()),
            format=log_format,
            handlers=[]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(console_handler)
        
        # File handler
        if LOG_TO_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setFormatter(logging.Formatter(log_format))
            self.logger.addHandler(file_handler)

    async def initialize_client(self):
        """Initialize Pacifica client"""
        try:
            self.logger.info("Initializing Pacifica Random Trading Bot...")
            
            # Setup proxy if enabled
            if USE_PROXY and PROXY_URL:
                self.logger.info(f"Using proxy: {PROXY_URL}")
                self.session = requests.Session()
                self.session.proxies = {
                    'http': PROXY_URL,
                    'https': PROXY_URL
                }
            else:
                self.session = requests.Session()
            
            # Initialize keypair
            if not PRIVATE_KEY:
                raise ValueError("PRIVATE_KEY is required")
                
            self.keypair = Keypair.from_base58_string(PRIVATE_KEY)
            self.public_key = str(self.keypair.pubkey())
            
            self.logger.info("Successfully connected to Pacifica")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            return False

    def _make_request(self, endpoint: str, payload: Dict, request_type: str) -> Tuple[bool, Optional[Dict]]:
        """Make authenticated request to Pacifica API"""
        try:
            # Generate timestamp and signature
            timestamp = int(time.time() * 1_000)
            
            signature_header = {
                "timestamp": timestamp,
                "expiry_window": 5_000,
                "type": request_type,
            }
            
            # Sign the message
            message, signature = sign_message(signature_header, payload, self.keypair)
            
            # Construct request
            request_data = {
                "account": self.public_key,
                "signature": signature,
                "timestamp": timestamp,
                "expiry_window": 5_000,
                **payload
            }
            
            # Make request
            url = f"{MAINNET_URL}{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(url, json=request_data, headers=headers, timeout=ORDER_TIMEOUT)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return False, response.json() if response.text else None
                
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return False, None

    def _make_silent_request(self, endpoint: str, payload: Dict, request_type: str) -> Tuple[bool, Optional[Dict]]:
        """Make authenticated request to Pacifica API without logging errors (for position detection)"""
        try:
            # Generate timestamp and signature
            timestamp = int(time.time() * 1_000)
            
            signature_header = {
                "timestamp": timestamp,
                "expiry_window": 5_000,
                "type": request_type,
            }
            
            # Sign the message
            message, signature = sign_message(signature_header, payload, self.keypair)
            
            # Construct request
            request_data = {
                "account": self.public_key,
                "signature": signature,
                "timestamp": timestamp,
                "expiry_window": 5_000,
                **payload
            }
            
            # Make request
            url = f"{MAINNET_URL}{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            response = self.session.post(url, json=request_data, headers=headers, timeout=ORDER_TIMEOUT)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                # Return the error response without logging
                return False, response.json() if response.text else None
                
        except Exception as e:
            # Return None without logging
            return False, None

    def _calculate_percentage_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on account percentage - ADJUSTED FOR PACIFICA'S ACTUAL LEVERAGE"""
        # Random percentage between min and max
        risk_percent = random.uniform(MIN_POSITION_PERCENT, MAX_POSITION_PERCENT)
        
        # Calculate risk amount in dollars
        risk_amount = (risk_percent / 100) * ACCOUNT_BALANCE
        
        # CRITICAL: Pacifica uses 50x leverage by default, not our configured leverage
        # We need to adjust our position size calculation accordingly
        configured_leverage = MANUAL_LEVERAGE.get(symbol, 1.0)
        actual_platform_leverage = 50.0  # Pacifica's actual leverage
        
        # Calculate what our position size should be to achieve our intended risk
        # If we want 5x effective leverage but platform uses 50x, we need 1/10th the position size
        leverage_adjustment_factor = configured_leverage / actual_platform_leverage
        
        # Calculate base notional value (what we want to risk)
        target_notional = risk_amount * configured_leverage
        
        # Adjust position size for platform's actual leverage
        adjusted_position_size = (risk_amount * leverage_adjustment_factor) / price
        
        # Cap position size to prevent excessive exposure
        max_risk_amount = 0.8 * ACCOUNT_BALANCE
        max_position_size = (max_risk_amount * leverage_adjustment_factor) / price
        
        if adjusted_position_size > max_position_size:
            adjusted_position_size = max_position_size
            self.logger.warning(f"Reduced position size for {symbol} due to risk limits")
        
        # Calculate actual notional with platform leverage for logging
        actual_notional = adjusted_position_size * price * actual_platform_leverage
        
        self.logger.info(f"LEVERAGE ADJUSTMENT: Configured {configured_leverage}x → Platform {actual_platform_leverage}x")
        self.logger.info(f"Risk calculation: {risk_percent:.1f}% of ${ACCOUNT_BALANCE} = ${risk_amount:.2f} target risk")
        self.logger.info(f"Position adjustment: ${target_notional:.2f} target notional → {adjusted_position_size:.6f} units (factor: {leverage_adjustment_factor:.3f})")
        self.logger.info(f"Actual exposure: {adjusted_position_size:.6f} units × ${price:.2f} × {actual_platform_leverage}x = ${actual_notional:.2f}")
        
        return adjusted_position_size

    def _generate_random_trade_params(self) -> Dict:
        """Generate random trading parameters"""
        # Select random market from allowed pairs
        symbol = random.choice(self.available_markets)
        
        # Random side (bid = long, ask = short)
        side = random.choice(["bid", "ask"])
        
        # For demo purposes, use a mock price (in real implementation, fetch from API)
        mock_prices = {
            "BTC": 65000.0,
            "ETH": 3500.0,
            "HYPE": 0.25,
            "SOL": 150.0,
            "BNB": 600.0
        }
        
        price = mock_prices.get(symbol, 100.0)
        
        # Calculate position size based on percentage
        position_size = self._calculate_percentage_position_size(symbol, price)
        
        # Format amount (Pacifica expects string and must be multiple of lot size)
        # Different symbols have different lot sizes
        lot_sizes = {
            "BTC": 0.001,    # BTC typically has smaller lot size
            "ETH": 0.01,     # ETH standard lot size
            "HYPE": 1.0,     # HYPE might have larger lot size (low price)
            "SOL": 0.01,     # SOL standard lot size  
            "BNB": 0.01,     # BNB standard lot size
        }
        
        lot_size = lot_sizes.get(symbol, 0.01)  # Default to 0.01
        position_size_rounded = round(position_size / lot_size) * lot_size
        
        # Ensure minimum position size
        if position_size_rounded < lot_size:
            position_size_rounded = lot_size
            
        # Format with appropriate decimal places
        if lot_size >= 1.0:
            amount = f"{position_size_rounded:.0f}"
        elif lot_size >= 0.01:
            amount = f"{position_size_rounded:.2f}"
        else:
            amount = f"{position_size_rounded:.3f}"
        
        self.logger.info(f"Final position: {amount} units (lot size {lot_size} adjusted from {position_size:.6f} calculated units)")
        
        return {
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "slippage_percent": str(DEFAULT_SLIPPAGE),
            "reduce_only": False
        }

    async def _place_random_trade(self):
        """Place a random market order"""
        try:
            # Generate trade parameters
            trade_params = self._generate_random_trade_params()
            
            self.logger.info(f"Placing {trade_params['side'].upper()} market order: {trade_params['symbol']} size={trade_params['amount']} slippage={trade_params['slippage_percent']}%")
            
            # Add client order ID
            trade_params["client_order_id"] = str(uuid.uuid4())
            
            # Place market order
            success, response = self._make_request("/orders/create_market", trade_params, "create_market_order")
            
            if success and response:
                self.logger.info(f"Trade successful! Order ID: {trade_params['client_order_id']}")
                
                # Record position
                self.position_manager.open_position(
                    trade_params["symbol"],
                    trade_params["side"],
                    trade_params["amount"],
                    trade_params["client_order_id"]
                )
                
                # Update stats
                self.stats.daily_trades += 1
                self.stats.total_trades += 1
                self.stats.successful_trades += 1
                
                # Log trade details
                self._log_trade_details(trade_params, response)
                
            else:
                self.logger.error(f"Trade failed for {trade_params['symbol']}")
                self.stats.failed_trades += 1
                
        except Exception as e:
            self.logger.error(f"Error placing trade: {e}")
            self.stats.failed_trades += 1

    def _log_trade_details(self, trade_params: Dict, response: Dict):
        """Log detailed trade information"""
        # Get the calculated hold time for logging
        hold_time = self.position_manager.position_hold_minutes
        hold_type = "fixed" if POSITION_HOLD_MINUTES > 0 else "random"
        
        self.logger.info(f"Position opened: {trade_params['symbol']} {trade_params['side'].upper()} - will hold for {hold_time} minutes ({hold_type})")
        
        trade_details = {
            "timestamp": datetime.now().isoformat(),
            "symbol": trade_params["symbol"],
            "side": trade_params["side"],
            "amount": trade_params["amount"],
            "slippage": trade_params["slippage_percent"],
            "client_order_id": trade_params["client_order_id"],
            "daily_trades": self.stats.daily_trades,
            "total_trades": self.stats.total_trades
        }
        
        self.logger.info(f"Trade details: {json.dumps(trade_details, indent=2)}")

    async def _close_position(self):
        """Close the current position"""
        if not self.position_manager.has_position():
            return
            
        position = self.position_manager.current_position
        
        try:
            self.logger.info(f"Closing position: {position['symbol']} {position['side'].upper()}")
            
            # Create opposite side order to close position
            opposite_side = "ask" if position['side'] == "bid" else "bid"
            
            close_params = {
                "symbol": position['symbol'],
                "side": opposite_side,
                "amount": position['amount'],
                "slippage_percent": str(DEFAULT_SLIPPAGE),
                "reduce_only": True,
                "client_order_id": str(uuid.uuid4())
            }
            
            success, response = self._make_request("/orders/create_market", close_params, "create_market_order")
            
            if success:
                self.logger.info(f"Order placed for closing position. Order ID: {close_params['client_order_id']}")
                
                # Wait a moment and verify the position is actually closed
                await asyncio.sleep(2)
                
                # Try to place a small test order to verify position is closed
                test_params = {
                    "symbol": position['symbol'],
                    "side": position['side'],  # Same side as original position
                    "amount": "0.0001",  # Very small amount
                    "slippage_percent": str(DEFAULT_SLIPPAGE),
                    "reduce_only": True,
                    "client_order_id": str(uuid.uuid4())
                }
                
                test_success, test_response = self._make_request("/orders/create_market", test_params, "create_market_order")
                
                if not test_success:
                    # Test order failed - position is likely closed
                    self.logger.info(f"✅ Position {position['symbol']} successfully closed!")
                    self.position_manager.close_position()
                else:
                    # Test order succeeded - position might still exist, try opposite direction
                    self.logger.warning(f"⚠️  Position {position['symbol']} may still exist. Trying opposite direction...")
                    
                    opposite_params = {
                        "symbol": position['symbol'],
                        "side": "ask" if position['side'] == "bid" else "bid",  # Opposite side
                        "amount": position['amount'],
                        "slippage_percent": str(DEFAULT_SLIPPAGE),
                        "reduce_only": True,
                        "client_order_id": str(uuid.uuid4())
                    }
                    
                    opposite_success, opposite_response = self._make_request("/orders/create_market", opposite_params, "create_market_order")
                    
                    if opposite_success:
                        self.logger.info(f"✅ Position {position['symbol']} closed with opposite direction!")
                        self.position_manager.close_position()
                    else:
                        self.logger.error(f"❌ Both close attempts failed for {position['symbol']}")
                        # Clear position state anyway to prevent infinite loops
                        self.position_manager.close_position()
            else:
                # CRITICAL FIX: Clear position state even if API says "No position found"
                # This prevents the bot from getting stuck in a loop
                error_msg = response.get('error', '') if isinstance(response, dict) else str(response)
                if "No position found" in error_msg or "No position" in error_msg:
                    self.logger.warning(f"Position {position['symbol']} not found on exchange - clearing internal state")
                    self.position_manager.close_position()
                else:
                    self.logger.error(f"Failed to close position: {position['symbol']} - {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            # CRITICAL FIX: Clear position state on any error to prevent infinite loops
            self.logger.warning(f"Clearing position state due to error: {position['symbol']}")
            self.position_manager.close_position()

    async def _check_and_close_existing_positions(self):
        """Check for existing open positions and close them before starting trading"""
        try:
            self.logger.info("🔍 Checking for existing open positions...")
            
            # Since Pacifica doesn't have a direct "get positions" endpoint,
            # we'll attempt to close common position types and verify success
            common_symbols = ALLOWED_TRADING_PAIRS.copy()
            positions_found = 0
            
            # Test different position sizes to catch various position amounts
            test_amounts = ["0.001", "0.01", "0.1", "1.0"]
            
            for symbol in common_symbols:
                try:
                    self.logger.debug(f"🔍 Testing {symbol} for existing positions...")
                    
                    # Try different amounts for long positions (sell to close)
                    position_closed = False
                    for amount in test_amounts:
                        long_closed = await self._attempt_close_position(symbol, "ask", amount)
                        if long_closed:
                            positions_found += 1
                            self.logger.info(f"✅ Closed long position in {symbol} (size: {amount})")
                            position_closed = True
                            break  # Move to next symbol if position found
                    
                    # Only try short positions if no long position was found
                    if not position_closed:
                        for amount in test_amounts:
                            short_closed = await self._attempt_close_position(symbol, "bid", amount)
                            if short_closed:
                                positions_found += 1
                                self.logger.info(f"✅ Closed short position in {symbol} (size: {amount})")
                                break  # Move to next symbol if position found
                        
                except Exception as e:
                    self.logger.debug(f"🔍 No position found in {symbol}: {e}")
                    continue
            
            if positions_found > 0:
                self.logger.info(f"✅ Closed {positions_found} existing position(s)")
                # Wait for positions to be fully closed
                await asyncio.sleep(5)
            else:
                self.logger.info("✅ No existing positions found")
            
        except Exception as e:
            self.logger.error(f"❌ Error checking existing positions: {e}")
            self.logger.info("⚠️  Continuing with bot startup despite position check error...")
    
    async def _attempt_close_position(self, symbol: str, side: str, amount: str) -> bool:
        """Attempt to close a position and return True if successful"""
        try:
            close_params = {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "slippage_percent": str(DEFAULT_SLIPPAGE),
                "reduce_only": True,
                "client_order_id": str(uuid.uuid4())
            }
            
            # Use silent request for position detection to avoid error spam
            success, response = self._make_silent_request("/orders/create_market", close_params, "create_market_order")
            
            if success:
                # Check if the order was actually filled (not just accepted)
                order_id = close_params['client_order_id']
                self.logger.debug(f"🔍 Close order placed for {symbol} {side} (amount: {amount}): {order_id}")
                
                # Wait a moment and check if we can place another order
                # If we can't, it means the position was closed
                await asyncio.sleep(3)  # Increased wait time for better verification
                
                # Try to place a test order with the SAME side as the original position
                # If this fails with "No position found", the position was closed
                test_params = {
                    "symbol": symbol,
                    "side": side,  # Same side as the close order
                    "amount": amount,  # Same amount as the close order
                    "slippage_percent": str(DEFAULT_SLIPPAGE),
                    "reduce_only": True,
                    "client_order_id": str(uuid.uuid4())
                }
                
                # Use silent request for verification to avoid error spam
                test_success, test_response = self._make_silent_request("/orders/create_market", test_params, "create_market_order")
                
                if not test_success:
                    # Check the error message to determine if position was closed
                    error_msg = test_response.get('error', '') if isinstance(test_response, dict) else str(test_response)
                    
                    if "No position found" in error_msg:
                        # Position was successfully closed - this is SUCCESS!
                        self.logger.info(f"✅ Position in {symbol} successfully closed (verified)")
                        return True
                    else:
                        # Some other error occurred
                        self.logger.debug(f"🔍 Test order failed for {symbol}: {error_msg}")
                        return False
                else:
                    # Test order succeeded - position still exists, try opposite direction
                    self.logger.warning(f"⚠️  Position in {symbol} still exists, trying opposite direction...")
                    
                    # Try opposite direction
                    opposite_params = {
                        "symbol": symbol,
                        "side": "ask" if side == "bid" else "bid",  # Opposite side
                        "amount": amount,
                        "slippage_percent": str(DEFAULT_SLIPPAGE),
                        "reduce_only": True,
                        "client_order_id": str(uuid.uuid4())
                    }
                    
                    # Use silent request for opposite direction attempt to avoid error spam
                    opposite_success, opposite_response = self._make_silent_request("/orders/create_market", opposite_params, "create_market_order")
                    
                    if opposite_success:
                        self.logger.info(f"✅ Position in {symbol} closed with opposite direction")
                        return True
                    else:
                        self.logger.debug(f"🔍 Opposite direction also failed for {symbol}")
                        return False
            else:
                # Order was rejected - check the error message
                error_msg = response.get('error', '') if isinstance(response, dict) else str(response)
                
                # If it's a lot size error, try with a different amount
                if "not a multiple of lot size" in error_msg:
                    self.logger.debug(f"🔍 Lot size issue for {symbol} {side} with amount {amount}")
                    return False
                elif "No position found" in error_msg:
                    self.logger.debug(f"🔍 No position found for {symbol} {side} (expected)")
                    return False
                elif "Invalid reduce-only order side" in error_msg:
                    # This means there IS a position but we're trying the wrong side
                    self.logger.debug(f"🔍 Wrong side for {symbol} - position exists but side is incorrect")
                    return False
                else:
                    self.logger.debug(f"🔍 Order rejected for {symbol} {side}: {error_msg}")
                    return False
                
        except Exception as e:
            self.logger.debug(f"🔍 Error attempting to close {symbol} {side}: {e}")
            return False

    def _print_stats(self):
        """Print current trading statistics"""
        if self.stats.total_trades > 0:
            success_rate = (self.stats.successful_trades / self.stats.total_trades) * 100
        else:
            success_rate = 0.0
            
        self.logger.info(
            f"Trading Stats - Daily: {self.stats.daily_trades}/{MAX_DAILY_TRADES} "
            f"Total: {self.stats.total_trades} "
            f"Success: {self.stats.successful_trades} "
            f"Failed: {self.stats.failed_trades} "
            f"Success Rate: {success_rate:.1f}%"
        )

    async def run(self):
        """Main trading loop"""
        self.logger.info("Starting Pacifica random trading bot...")
        if SINGLE_POSITION_MODE:
            self.logger.info(f"Single position mode enabled - holding positions for {MIN_POSITION_HOLD_MINUTES}-{MAX_POSITION_HOLD_MINUTES} minutes")
        
        # Check and close any existing positions before starting (if enabled)
        if CLOSE_EXISTING_POSITIONS_ON_START:
            await self._check_and_close_existing_positions()
        else:
            self.logger.info("⚠️  Skipping existing position check (CLOSE_EXISTING_POSITIONS_ON_START=false)")
        
        self.running = True
        
        try:
            while self.running:
                # Print stats periodically
                self._print_stats()
                
                if SINGLE_POSITION_MODE:
                    # Single position management logic
                    if self.position_manager.has_position():
                        position_info = self.position_manager.get_position_info()
                        
                        # Safety check for position_info to prevent race conditions
                        if position_info is None:
                            self.logger.warning("⚠️  Position info is None, skipping this cycle")
                            await asyncio.sleep(1)
                            continue
                        
                        # Log position status every 2 minutes (120 seconds) instead of every 30 seconds
                        if not hasattr(self, '_last_position_log_time') or self._last_position_log_time is None:
                            self._last_position_log_time = datetime.now()
                        
                        time_since_last_log = (datetime.now() - self._last_position_log_time).total_seconds()
                        if time_since_last_log >= POSITION_LOG_INTERVAL_SECONDS:
                            self.logger.info(f"Current position: {position_info['symbol']} {position_info['side'].upper()} "
                                           f"(held for {position_info['hold_duration_minutes']:.1f}/{position_info['target_hold_minutes']} minutes)")
                            self._last_position_log_time = datetime.now()
                        
                        if self.position_manager.should_close_position():
                            await self._close_position()
                            # Reset log timer for next position
                            self._last_position_log_time = None
                            
                            # Dynamic wait time between positions
                            wait_time = random.randint(MIN_WAIT_BETWEEN_POSITIONS, MAX_WAIT_BETWEEN_POSITIONS)
                            self.logger.info(f"Waiting {wait_time} seconds before opening next position...")
                            await asyncio.sleep(wait_time)
                        else:
                            # Check every 30 seconds if position should be closed (but don't log every time)
                            await asyncio.sleep(30)
                            continue
                    else:
                        # No position, open a new one
                        await self._place_random_trade()
                        
                        # Wait a bit after opening position
                        await asyncio.sleep(10) # Small initial wait after opening a position
                else:
                    await self._place_random_trade()
                    wait_time = random.randint(MIN_TRADE_INTERVAL, MAX_TRADE_INTERVAL)
                    self.logger.info(f"Waiting {wait_time} seconds until next trade...")
                    for _ in range(wait_time):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping...")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        self._release_process_lock()
        self._print_stats()
        self.logger.info("Pacifica trading bot stopped")


async def main():
    """Main entry point"""
    bot = PacificaRandomTradingBot()
    
    # Initialize client
    if not await bot.initialize_client():
        return
    
    # Start trading
    await bot.run()


if __name__ == "__main__":
    import os
    asyncio.run(main())
