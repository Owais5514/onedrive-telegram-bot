#!/usr/bin/env python3
"""
Quick Start Script for OneDrive Telegram Bot (Render Mode)
Test the bot locally before deploying to Render
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import aiohttp
        import telegram
        import msal
        import requests
        import dotenv
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("📦 Installing requirements...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("📋 Please copy .env.example to .env and fill in your credentials")
        print("   Or see .env.render for Render-specific template")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'ADMIN_USER_ID', 
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET',
        'AZURE_TENANT_ID',
        'TARGET_USER_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ Environment variables configured")
    return True

def main():
    """Main function"""
    print("🚀 OneDrive Telegram Bot - Local Test Runner")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check environment
    if not check_env_file():
        return 1
    
    # Set PORT for local testing (Render will override this)
    if not os.getenv('PORT'):
        os.environ['PORT'] = '8080'
        print("🔧 Set PORT=8080 for local testing")
    
    print("🎯 Starting bot in Render mode...")
    print("📍 Bot will be available at: http://localhost:8080")
    print("🏥 Health check: http://localhost:8080/health")
    print("🔗 Webhook endpoint: http://localhost:8080/webhook")
    print()
    print("⚠️  Note: For local testing, the webhook won't work with Telegram")
    print("   Use ngrok or deploy to Render for webhook functionality")
    print()
    
    try:
        # Import and run the bot
        from app import main as run_bot
        return run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
