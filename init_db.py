#!/usr/bin/env python3
"""
Database initialization script for OneDrive Telegram Bot
Run this script to set up the database on Render
"""

import sys
import logging
from database import db_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Initialize database"""
    print("🔧 Initializing OneDrive Telegram Bot Database...")
    
    if not db_manager.enabled:
        print("❌ Database connection not available!")
        print("Please check your DATABASE_URL environment variable.")
        return 1
    
    print("📊 Creating database tables...")
    if db_manager.create_tables():
        print("✅ Database tables created successfully!")
        
        # Check if we can migrate any existing data
        user_count = db_manager.get_user_count()
        print(f"📈 Current user count: {user_count}")
        
        if user_count == 0:
            print("💡 Database is empty - data will be migrated when bot starts")
        
        return 0
    else:
        print("❌ Failed to create database tables!")
        return 1

if __name__ == "__main__":
    exit(main())
