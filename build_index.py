#!/usr/bin/env python3
"""
Build file index for OneDrive Telegram Bot
"""

import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the bot class
from bot_continuous import OneDriveTelegramBot

async def build_index():
    """Build and save the file index"""
    print("🔧 Initializing bot for indexing...")
    
    try:
        # Create bot instance
        bot = OneDriveTelegramBot()
        
        # Initialize authentication
        print("🔐 Getting authentication token...")
        auth_success = bot.initialize_authentication()
        
        if not auth_success:
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful")
        
        # Test authentication and cache users
        success = await bot.test_and_cache_users()
        if success and bot.users_cache:
            print(f"👤 Default user: {bot.users_cache[bot.default_user_id]['name']}")
        else:
            print("⚠️ No users found, but continuing with indexing...")
        # Build file index
        print("📂 Building file index...")
        await bot.build_file_index(force_rebuild=True)
        print("✅ File index completed!")
        
        # Check if files were saved
        if os.path.exists(bot.file_index_path):
            print(f"📁 Index saved to: {bot.file_index_path}")
            print(f"📊 Total files indexed: {len(bot.file_index)}")
        else:
            print("⚠️ Index file not found after building")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(build_index())
