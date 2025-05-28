#!/usr/bin/env python3
"""
Test script to verify AI search functionality
"""

import asyncio
import json
from bot_continuous import OneDriveTelegramBot

async def test_ai_search():
    """Test the AI search functionality"""
    print("🔍 Testing AI Search Functionality...")
    
    # Create bot instance
    bot = OneDriveTelegramBot()
    
    # Initialize authentication
    print("🔐 Initializing authentication...")
    auth_success = bot.initialize_authentication()
    if not auth_success:
        print("❌ Authentication failed")
        return
    
    # Test and cache users
    print("👥 Testing user access...")
    success = await bot.test_and_cache_users()
    if not success:
        print("❌ User caching failed")
        return
    
    print(f"✅ Default user: {bot.users_cache[bot.default_user_id]['name']}")
    
    # Load file index
    print("📂 Loading file index...")
    await bot.build_file_index()
    print(f"✅ File index loaded with {len(bot.file_index)} files")
    
    # Test search functionality
    test_queries = [
        "calculus notes",
        "python programming files",
        "semester 1 assignments",
        "mathematics",
        "engineering"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        results = bot.search_files(query, limit=5)
        
        if results:
            print(f"   ✅ Found {len(results)} relevant files:")
            for i, file_info in enumerate(results, 1):
                print(f"      {i}. {file_info['name']} (Score: {file_info['score']})")
                print(f"         Path: {file_info['path']}")
        else:
            print("   ❌ No files found")
    
    # Test Claude AI integration
    print(f"\n🤖 Testing Claude AI integration...")
    if bot.claude_api_key:
        test_query = "calculus notes"
        search_results = bot.search_files(test_query, limit=3)
        
        if search_results:
            ai_response = await bot.query_claude_ai(test_query, search_results)
            print(f"✅ Claude AI Response:")
            print(f"   Query: '{test_query}'")
            print(f"   Response: {ai_response[:200]}...")
        else:
            print("❌ No search results to test with Claude AI")
    else:
        print("⚠️ Claude API key not configured")
    
    print("\n✅ AI Search test completed!")

if __name__ == '__main__':
    asyncio.run(test_ai_search())
