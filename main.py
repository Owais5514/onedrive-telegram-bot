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

# =============================================================================
# CONFIGURATION SECTION - EASY TO MODIFY
# =============================================================================

# OneDrive folder locations to index
# QUICK SETUP: Change "Sharing" to your OneDrive folder name
# Example: ONEDRIVE_FOLDERS = ["Documents"] or ONEDRIVE_FOLDERS = ["My_Files"]
# See CONFIG_EXAMPLES.md for more examples
ONEDRIVE_FOLDERS = [
    "Sharing",  # Primary folder name to look for
    "AUST Resources",  # Example: uncomment to add more folders
    # "Public",     # Example: uncomment to add more folders
    # "Archive",    # Example: uncomment to add more folders
]

# Configuration for folder search behavior
# Most users can leave these settings as default
FOLDER_CONFIG = {
    "case_sensitive": False,  # Set to True if folder names should be case-sensitive
    "search_subfolders": False,  # Set to True to search in subfolders (not recommended for performance)
    "require_all_folders": False,  # Set to True if ALL folders must exist, False if ANY folder is sufficient
}

# =============================================================================
# END CONFIGURATION SECTION
# =============================================================================

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
        
        # Initialize and run bot with folder configuration
        bot = OneDriveBot(
            onedrive_folders=ONEDRIVE_FOLDERS,
            folder_config=FOLDER_CONFIG
        )
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
