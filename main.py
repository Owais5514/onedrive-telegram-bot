#!/usr/bin/env python3
"""
OneDrive Telegram Bot Launcher
Simple launcher script for the bot with error handling
"""

import sys
import os
from bot import OneDriveBot

def main():
    """Main function to run the bot"""
    try:
        # Check if .env file exists
        if not os.path.exists('.env'):
            print("❌ Error: .env file not found!")
            print("📋 Please copy .env.example to .env and fill in your credentials.")
            return 1
        
        # Initialize and run bot
        bot = OneDriveBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
