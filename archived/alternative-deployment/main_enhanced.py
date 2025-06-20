#!/usr/bin/env python3
"""
OneDrive Telegram Bot Launcher - Enhanced
Supports both polling and webhook methods
"""

import sys
import os
import signal
import logging
import argparse
from bot import OneDriveBot
from bot_webhook import OneDriveBotWebhook

# =============================================================================
# CONFIGURATION SECTION - EASY TO MODIFY
# =============================================================================

# OneDrive folder locations to index
ONEDRIVE_FOLDERS = [
    "Sharing",  # Primary folder name to look for
    # "AUST Resources",  # Example: uncomment to add more folders
    # "Public",     # Example: uncomment to add more folders
    # "Archive",    # Example: uncomment to add more folders
]

# Configuration for folder search behavior
FOLDER_CONFIG = {
    "case_sensitive": False,
    "search_subfolders": False,
    "require_all_folders": False,
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

def print_usage():
    """Print usage information"""
    print("""
OneDrive Telegram Bot - Multiple Deployment Methods

Usage:
    python main_enhanced.py [method] [options]

Methods:
    polling   - Use polling method (default, good for development)
    webhook   - Use webhook method (better for production)

Examples:
    python main_enhanced.py polling           # Run with polling
    python main_enhanced.py webhook           # Run with webhook
    python main_enhanced.py --help            # Show this help

Environment Variables for Webhook:
    WEBHOOK_URL      - Your public webhook URL (e.g., https://yourdomain.com)
    WEBHOOK_PATH     - Webhook path (default: /webhook)
    WEBHOOK_PORT     - Port to listen on (default: 8443)
    WEBHOOK_HOST     - Host to bind to (default: 0.0.0.0)
    SSL_CERT_FILE    - Path to SSL certificate file (optional)
    SSL_KEY_FILE     - Path to SSL private key file (optional)

Setup Guide:
    1. Polling (Easy setup):
       - Just run: python main_enhanced.py polling
       - No additional configuration needed
       - Good for development and testing

    2. Webhook (Production setup):
       - Set WEBHOOK_URL in .env file
       - Ensure your server is publicly accessible
       - HTTPS is required by Telegram
       - Run: python main_enhanced.py webhook

Comparison:
    Polling:
        ✅ Easy to set up
        ✅ Works behind NAT/firewall
        ✅ No SSL certificate needed
        ❌ Less efficient (constant API calls)
        ❌ Higher latency

    Webhook:
        ✅ More efficient (push notifications)
        ✅ Lower latency
        ✅ Better for high-traffic bots
        ❌ Requires public HTTPS endpoint
        ❌ More complex setup
    """)

def validate_webhook_config():
    """Validate webhook configuration"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ Error: WEBHOOK_URL not set in .env file")
        print("📋 Please add WEBHOOK_URL=https://yourdomain.com to your .env file")
        return False
    
    if not webhook_url.startswith('https://'):
        print("❌ Error: WEBHOOK_URL must use HTTPS (required by Telegram)")
        return False
    
    return True

def main():
    """Main function to run the bot"""
    parser = argparse.ArgumentParser(description='OneDrive Telegram Bot')
    parser.add_argument('method', nargs='?', default='polling', 
                       choices=['polling', 'webhook'],
                       help='Bot method to use (default: polling)')
    parser.add_argument('--help-methods', action='store_true',
                       help='Show detailed help about methods')
    
    args = parser.parse_args()
    
    if args.help_methods:
        print_usage()
        return 0
    
    method = args.method.lower()
    bot = None
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
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
        
        # Method-specific validation and setup
        if method == 'webhook':
            if not validate_webhook_config():
                return 1
            
            print("🔗 Starting bot with webhook method...")
            print("ℹ️  This requires a public HTTPS endpoint")
            
            bot = OneDriveBotWebhook(
                onedrive_folders=ONEDRIVE_FOLDERS,
                folder_config=FOLDER_CONFIG
            )
        else:
            print("🔄 Starting bot with polling method...")
            print("ℹ️  Bot will continuously poll for updates")
            
            bot = OneDriveBot(
                onedrive_folders=ONEDRIVE_FOLDERS,
                folder_config=FOLDER_CONFIG
            )
        
        # Run the bot with the selected method
        bot.run(method if hasattr(bot, 'run') and len(bot.run.__code__.co_varnames) > 1 else None)
        
    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        logger.exception("Detailed error information:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
