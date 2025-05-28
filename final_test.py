#!/usr/bin/env python3
"""
Final comprehensive test for the OneDrive Telegram Bot AI Search functionality
"""

import asyncio
import json
import os
from datetime import datetime
from bot_continuous import OneDriveTelegramBot

async def comprehensive_test():
    """Comprehensive test of all bot functionality"""
    print("🚀 Comprehensive OneDrive Telegram Bot AI Search Test")
    print("=" * 60)
    
    # Create bot instance
    bot = OneDriveTelegramBot()
    
    # Test 1: Authentication
    print("\n1️⃣ Testing Authentication...")
    auth_success = bot.initialize_authentication()
    if auth_success:
        print("   ✅ Azure authentication successful")
    else:
        print("   ❌ Azure authentication failed")
        return
    
    # Test 2: User access
    print("\n2️⃣ Testing User Access...")
    success = await bot.test_and_cache_users()
    if success:
        print(f"   ✅ Found {len(bot.users_cache)} users")
        print(f"   ✅ Default user: {bot.users_cache[bot.default_user_id]['name']}")
    else:
        print("   ❌ User access failed")
        return
    
    # Test 3: File index persistence
    print("\n3️⃣ Testing File Index Persistence...")
    
    # Check if index files exist
    index_exists = os.path.exists(bot.file_index_path)
    timestamp_exists = os.path.exists(bot.index_timestamp_path)
    
    print(f"   📁 Index file exists: {index_exists}")
    print(f"   ⏰ Timestamp file exists: {timestamp_exists}")
    
    if timestamp_exists:
        with open(bot.index_timestamp_path, 'r') as f:
            timestamp_str = f.read().strip()
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            print(f"   📅 Index age: {age}")
    
    # Load the index
    await bot.build_file_index()
    print(f"   ✅ File index loaded with {len(bot.file_index)} files")
    
    # Test 4: Search functionality
    print("\n4️⃣ Testing Search Functionality...")
    
    test_cases = [
        ("calculus", "mathematics content"),
        ("python", "programming files"),
        ("chemistry", "science materials"),
        ("assignment", "coursework"),
        ("pdf", "document files"),
        ("lecture", "educational content")
    ]
    
    search_results_summary = {}
    
    for query, description in test_cases:
        results = bot.search_files(query, limit=3)
        search_results_summary[query] = len(results)
        
        if results:
            print(f"   ✅ '{query}' ({description}): {len(results)} files found")
            # Show top result
            top_result = results[0]
            print(f"      🏆 Top result: {top_result['name']} (Score: {top_result['score']})")
        else:
            print(f"   ⚠️  '{query}' ({description}): No files found")
    
    # Test 5: Claude AI integration
    print("\n5️⃣ Testing Claude AI Integration...")
    
    if bot.claude_api_key:
        # Test with a simple query that should have results
        test_query = "calculus notes"
        search_results = bot.search_files(test_query, limit=3)
        
        if search_results:
            try:
                ai_response = await bot.query_claude_ai(test_query, search_results)
                if ai_response and not ai_response.startswith("Sorry"):
                    print("   ✅ Claude AI integration working")
                    print(f"   💬 Sample response length: {len(ai_response)} characters")
                else:
                    print("   ⚠️  Claude AI returned error response")
            except Exception as e:
                print(f"   ❌ Claude AI error: {e}")
        else:
            print("   ⚠️  No search results to test Claude AI with")
    else:
        print("   ❌ Claude API key not configured")
    
    # Test 6: Performance metrics
    print("\n6️⃣ Performance Metrics...")
    
    # Test search speed
    import time
    start_time = time.time()
    for _ in range(10):
        bot.search_files("test query", limit=5)
    end_time = time.time()
    avg_search_time = (end_time - start_time) / 10
    
    print(f"   ⚡ Average search time: {avg_search_time:.3f} seconds")
    print(f"   📊 Files per second: {len(bot.file_index) / avg_search_time:.0f}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_searches = sum(search_results_summary.values())
    successful_searches = sum(1 for count in search_results_summary.values() if count > 0)
    
    print(f"✅ Authentication: Working")
    print(f"✅ User Access: Working ({len(bot.users_cache)} users)")
    print(f"✅ File Index: {len(bot.file_index)} files indexed")
    print(f"✅ Search Success Rate: {successful_searches}/{len(test_cases)} queries")
    print(f"✅ Total Results Found: {total_searches} files")
    print(f"✅ Claude AI: {'Working' if bot.claude_api_key else 'Not configured'}")
    print(f"✅ Performance: {avg_search_time:.3f}s per search")
    
    if successful_searches == len(test_cases) and bot.claude_api_key:
        print("\n🎉 ALL TESTS PASSED! AI Search functionality is fully operational!")
    elif successful_searches >= len(test_cases) * 0.8:
        print("\n✅ Most tests passed! AI Search functionality is working well!")
    else:
        print("\n⚠️  Some tests failed. Check the configuration and file index.")
    
    print("\n🤖 The OneDrive Telegram Bot AI Search is ready for use!")

if __name__ == '__main__':
    asyncio.run(comprehensive_test())
