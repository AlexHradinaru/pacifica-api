#!/usr/bin/env python3
"""
Pacifica Trading Bot Setup Script

This script helps you set up the Pacifica trading bot by:
1. Checking dependencies
2. Creating .env file from template
3. Validating configuration
4. Providing setup guidance

Usage:
    python3 setup.py
"""

import os
import sys
import subprocess
from pathlib import Path


class PacificaBotSetup:
    """Setup helper for Pacifica trading bot"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.env_file = self.script_dir / ".env"
        self.env_example = self.script_dir / "env.example"
        
    def check_python_version(self):
        """Check Python version compatibility"""
        print("🐍 Checking Python version...")
        
        if sys.version_info < (3, 7):
            print("❌ Python 3.7+ is required")
            return False
        
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        return True
    
    def check_dependencies(self):
        """Check if required packages are installed"""
        print("📦 Checking dependencies...")
        
        required_packages = [
            "requests",
            "solders", 
            "websockets",
            "base58",
            "python-dotenv"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                # Handle special package name mappings
                import_name = package.replace("-", "_")
                if package == "python-dotenv":
                    import_name = "dotenv"
                
                __import__(import_name)
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} (missing)")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n📋 Install missing packages:")
            print(f"pip3 install {' '.join(missing_packages)}")
            return False
        
        return True
    
    def create_env_file(self):
        """Create .env file from template"""
        print("⚙️  Setting up environment configuration...")
        
        if self.env_file.exists():
            response = input("📋 .env file already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("📋 Keeping existing .env file")
                return True
        
        if not self.env_example.exists():
            print("❌ env.example template not found")
            return False
        
        # Copy template
        with open(self.env_example, 'r') as src:
            content = src.read()
        
        with open(self.env_file, 'w') as dst:
            dst.write(content)
        
        print(f"✅ Created .env file from template")
        return True
    
    def validate_env_config(self):
        """Validate .env configuration"""
        print("🔍 Validating configuration...")
        
        if not self.env_file.exists():
            print("❌ .env file not found")
            return False
        
        # Load .env file
        env_vars = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        issues = []
        
        # Check critical settings
        if not env_vars.get('PACIFICA_PRIVATE_KEY'):
            issues.append("PACIFICA_PRIVATE_KEY is not set")
        elif env_vars['PACIFICA_PRIVATE_KEY'] == 'your_base58_private_key_here':
            issues.append("PACIFICA_PRIVATE_KEY is still using example value")
        
        # Check proxy (MANDATORY)
        if env_vars.get('USE_PROXY', 'true').lower() == 'true':
            proxy_url = env_vars.get('PROXY_URL', '')
            if not proxy_url:
                issues.append("PROXY_URL is required (proxy usage is mandatory)")
            elif proxy_url == 'http://username:password@proxy.example.com:8080':
                issues.append("PROXY_URL is still using example values")
            elif not proxy_url.startswith(('http://', 'https://')):
                issues.append("PROXY_URL must start with http:// or https://")
            elif '@' not in proxy_url:
                issues.append("PROXY_URL must include authentication (username:password@host:port)")
        
        # Check account balance
        try:
            balance = float(env_vars.get('ACCOUNT_BALANCE', '0'))
            if balance <= 0:
                issues.append("ACCOUNT_BALANCE must be greater than 0")
        except ValueError:
            issues.append("ACCOUNT_BALANCE must be a valid number")
        
        # Check position percentages
        try:
            min_percent = float(env_vars.get('MIN_POSITION_PERCENT', '0'))
            max_percent = float(env_vars.get('MAX_POSITION_PERCENT', '0'))
            
            if min_percent <= 0 or max_percent <= 0:
                issues.append("Position percentages must be greater than 0")
            elif min_percent >= max_percent:
                issues.append("MIN_POSITION_PERCENT must be less than MAX_POSITION_PERCENT")
            elif max_percent > 100:
                issues.append("MAX_POSITION_PERCENT cannot exceed 100%")
                
        except ValueError:
            issues.append("Position percentages must be valid numbers")
        
        if issues:
            print("❌ Configuration issues found:")
            for issue in issues:
                print(f"   • {issue}")
            return False
        
        print("✅ Configuration looks good")
        return True
    
    def show_next_steps(self):
        """Show next steps after setup"""
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit .env file with your actual credentials:")
        print("   - Set your Solana private key (PACIFICA_PRIVATE_KEY)")
        print("   - Configure your proxy server (PROXY_URL) - MANDATORY")
        print("   - Adjust your account balance and risk settings")
        print()
        print("2. Test the configuration:")
        print("   python3 -c \"import config; print('Config OK')\"")
        print()
        print("3. Start the bot:")
        print("   python3 start_bot.py start")
        print()
        print("4. Monitor the bot:")
        print("   python3 start_bot.py status")
        print("   python3 start_bot.py logs")
        print()
        print("⚠️  IMPORTANT: Proxy configuration is MANDATORY for this bot!")
        print("⚠️  Start with small position sizes for testing!")
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🚀 Pacifica Trading Bot Setup")
        print("=" * 40)
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        print()
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        print()
        
        # Create .env file
        if not self.create_env_file():
            return False
        
        print()
        
        # Validate configuration
        config_valid = self.validate_env_config()
        
        print()
        
        if config_valid:
            self.show_next_steps()
        else:
            print("❌ Please fix the configuration issues in .env file")
            print("📋 Then run: python3 setup.py")
        
        return config_valid


def main():
    """Main entry point"""
    setup = PacificaBotSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
