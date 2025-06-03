#!/usr/bin/env python3
"""
OneDrive Telegram Bot Launcher
Simple launcher script for the bot with error handling
"""

import sys
import os
import signal
import logging
from bot import OneDriveBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot"""
    bot = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if bot:
            bot.shutdown_requested = True
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
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
