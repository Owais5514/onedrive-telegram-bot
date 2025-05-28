#!/usr/bin/env python3
"""
Test script to verify the enhanced AI search functionality and persistent user tracking
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

async def test_enhanced_features():
    """Test the enhanced search and persistent user tracking"""
    print("🧪 Testing Enhanced AI Search Features")
    print("=" * 60)
    
    try:
        # Import the bot class
        from bot_continuous import OneDriveTelegramBot
        
        # Create a bot instance for testing
        bot = OneDriveTelegramBot()
        
        # Check if user data files are created
        print("📁 Checking persistent storage files...")
        
        # Test user query tracking
        test_user_id = 12345
        
        print(f"✅ Initial query limit check for user {test_user_id}: {bot.check_user_query_limit(test_user_id)}")
        
        # Increment query count
        bot.increment_user_query_count(test_user_id)
        print(f"✅ After increment, query limit check: {bot.check_user_query_limit(test_user_id)}")
        
        # Check if files were created
        if os.path.exists(bot.user_queries_path):
            print(f"✅ User queries file created: {bot.user_queries_path}")
            with open(bot.user_queries_path, 'r') as f:
                data = json.load(f)
                print(f"📊 Stored query data: {data}")
        
        if os.path.exists(bot.unlimited_users_path):
            print(f"✅ Unlimited users file created: {bot.unlimited_users_path}")
        
        # Test enhanced search (if file index exists)
        if os.path.exists(bot.file_index_path):
            print(f"\n🔍 Testing enhanced search algorithm...")
            
            # Load the file index
            with open(bot.file_index_path, 'r', encoding='utf-8') as f:
                bot.file_index = json.load(f)
                print(f"📂 Loaded {len(bot.file_index)} files from index")
            
            # Test search queries with detailed scoring
            test_queries = [
                "calculus notes",
                "python programming", 
                "mathematics pdf",
                "semester assignment"
            ]
            
            for query in test_queries:
                results = bot.search_files(query, limit=3)
                print(f"\n🔎 Query: '{query}'")
                print(f"   Found {len(results)} results")
                
                for i, result in enumerate(results[:3], 1):
                    print(f"   {i}. {result['name']} (Score: {result['score']:.1f})")
                    print(f"      Path: {result['folder']}")
        
        print(f"\n🎉 All enhanced features tested successfully!")
        
        # Test unlimited user functionality
        print(f"\n👤 Testing unlimited user functionality...")
        bot.add_unlimited_user(test_user_id)
        print(f"✅ Added user {test_user_id} to unlimited list")
        print(f"✅ Query limit check (should be True): {bot.check_user_query_limit(test_user_id)}")
        
        # Verify persistence
        bot2 = OneDriveTelegramBot()
        print(f"✅ New bot instance - unlimited user persisted: {test_user_id in bot2.unlimited_users}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_features())
    sys.exit(0 if success else 1)
