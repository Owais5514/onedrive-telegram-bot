#!/usr/bin/env python3
"""
Simple test to verify key enhancements work
"""

import json
import os
from datetime import datetime

# Test 1: Check if the bot can be imported
try:
    print("Testing bot import...")
    import sys
    sys.path.insert(0, os.getcwd())
    from bot_continuous import OneDriveTelegramBot
    print("✅ Bot imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 2: Test persistent user tracking
try:
    print("\nTesting persistent user tracking...")
    bot = OneDriveTelegramBot()
    
    # Test user query limit
    test_user = 99999
    initial_limit = bot.check_user_query_limit(test_user)
    print(f"✅ Initial query limit for user {test_user}: {initial_limit}")
    
    # Increment and check
    bot.increment_user_query_count(test_user) 
    after_limit = bot.check_user_query_limit(test_user)
    print(f"✅ After increment, limit check: {after_limit}")
    
    # Check if file was created
    if os.path.exists(bot.user_queries_path):
        print(f"✅ User queries file created: {bot.user_queries_path}")
    
except Exception as e:
    print(f"❌ User tracking test failed: {e}")

# Test 3: Test enhanced search if index exists
try:
    print(f"\nTesting enhanced search...")
    if os.path.exists("file_index.json"):
        print("✅ File index found, testing search...")
        
        # Mock some data for testing
        bot.file_index = {
            "file1": {
                "name": "calculus_notes.pdf",
                "folder": "/math/semester1",
                "description": "calculus mathematics notes differential integral",
                "size": 1024
            },
            "file2": {
                "name": "python_guide.py", 
                "folder": "/programming/tutorials",
                "description": "python programming tutorial beginner guide",
                "size": 2048
            }
        }
        
        # Test search
        results = bot.search_files("calculus notes", limit=5)
        print(f"✅ Search test completed. Found {len(results)} results")
        if results:
            print(f"   Top result: {results[0]['name']} (Score: {results[0]['score']})")
    else:
        print("⚠️ No file index found, skipping search test")
        
except Exception as e:
    print(f"❌ Search test failed: {e}")

print(f"\n🎉 Basic enhancement tests completed!")
