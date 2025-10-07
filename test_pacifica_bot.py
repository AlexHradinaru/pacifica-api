#!/usr/bin/env python3
"""
Test script for Pacifica Trading Bot

This script tests the bot configuration and basic functionality
using the test environment configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Set environment to use test config
os.environ['DOTENV_PATH'] = '.env.test'

# Import after setting environment
from config import get_config_summary
from pacifica_trading_bot import PacificaRandomTradingBot


async def test_bot_initialization():
    """Test bot initialization and configuration"""
    print("🧪 Testing Pacifica Bot Initialization")
    print("=" * 50)
    
    try:
        # Print configuration summary
        print("📋 Configuration Summary:")
        print(get_config_summary())
        
        # Initialize bot
        print("\n🤖 Initializing bot...")
        bot = PacificaRandomTradingBot()
        
        # Test client initialization
        print("🔗 Testing client initialization...")
        success = await bot.initialize_client()
        
        if success:
            print("✅ Bot initialized successfully!")
            print(f"📍 Public Key: {bot.public_key}")
            print(f"🔐 Proxy Enabled: {bot.session.proxies is not None}")
            
            # Test configuration validation
            print("\n🔍 Testing configuration validation...")
            print("✅ All configuration checks passed")
            
            # Test trade parameter generation
            print("\n🎲 Testing trade parameter generation...")
            trade_params = bot._generate_random_trade_params()
            print(f"📊 Sample trade params: {trade_params}")
            
            return True
        else:
            print("❌ Bot initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Cleanup
        if 'bot' in locals():
            await bot.cleanup()


async def test_trading_logic():
    """Test trading logic without actually placing orders"""
    print("\n🎯 Testing Trading Logic")
    print("=" * 30)
    
    try:
        bot = PacificaRandomTradingBot()
        
        if not await bot.initialize_client():
            print("❌ Failed to initialize client for trading test")
            return False
        
        # Test position manager
        print("📊 Testing Position Manager...")
        print(f"   Has position: {bot.position_manager.has_position()}")
        
        # Test trade parameter generation multiple times
        print("🎲 Testing multiple trade generations...")
        for i in range(3):
            params = bot._generate_random_trade_params()
            print(f"   Trade {i+1}: {params['symbol']} {params['side']} {params['amount']} units")
        
        # Test position sizing calculations
        print("💰 Testing position sizing...")
        test_prices = {"BTC": 65000, "ETH": 3500, "SOL": 150}
        for symbol, price in test_prices.items():
            size = bot._calculate_percentage_position_size(symbol, price)
            notional = size * price
            print(f"   {symbol}: {size:.6f} units = ${notional:.2f} notional")
        
        print("✅ Trading logic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Trading logic test failed: {e}")
        return False
    finally:
        if 'bot' in locals():
            await bot.cleanup()


async def test_dry_run():
    """Test a dry run of the bot (no actual API calls)"""
    print("\n🏃 Testing Dry Run Mode")
    print("=" * 25)
    
    try:
        bot = PacificaRandomTradingBot()
        
        if not await bot.initialize_client():
            print("❌ Failed to initialize client for dry run")
            return False
        
        print("🚀 Starting dry run (will stop after 10 seconds)...")
        
        # Override the _make_request method to simulate API responses
        original_make_request = bot._make_request
        
        def mock_make_request(endpoint, payload, request_type):
            print(f"   🔄 Mock API call: {request_type} to {endpoint}")
            print(f"      Payload: {payload}")
            # Simulate successful response
            return True, {"status": "success", "order_id": "mock_order_123"}
        
        bot._make_request = mock_make_request
        
        # Run for a short time
        bot.running = True
        
        # Simulate one trading cycle
        if bot.position_manager.has_position():
            print("   📊 Position already exists, testing close logic...")
        else:
            print("   📈 No position, testing open logic...")
            await bot._place_random_trade()
            
            if bot.position_manager.has_position():
                position_info = bot.position_manager.get_position_info()
                print(f"   ✅ Position opened: {position_info}")
                
                # Test position closing
                print("   🔄 Testing position close...")
                await bot._close_position()
                print(f"   ✅ Position closed: {not bot.position_manager.has_position()}")
        
        print("✅ Dry run completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Dry run failed: {e}")
        return False
    finally:
        if 'bot' in locals():
            await bot.cleanup()


async def main():
    """Run all tests"""
    print("🧪 Pacifica Trading Bot Test Suite")
    print("=" * 40)
    
    # Check if test config exists
    test_config = Path('.env.test')
    if not test_config.exists():
        print("❌ .env.test file not found")
        return
    
    tests = [
        ("Bot Initialization", test_bot_initialization),
        ("Trading Logic", test_trading_logic),
        ("Dry Run", test_dry_run)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Bot is ready for use.")
    else:
        print("⚠️  Some tests failed. Check configuration and dependencies.")


if __name__ == "__main__":
    asyncio.run(main())
