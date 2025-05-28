#!/usr/bin/env python3
"""
Test script to verify the callback fix for AI search functionality
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

async def test_callback_fix():
    """Test the AI search callback fix"""
    print("🧪 Testing AI Search Callback Fix")
    print("=" * 50)
    
    try:
        # Import the bot class
        from bot_continuous import OneDriveTelegramBot
        
        # Create a mock bot instance for testing
        bot = OneDriveTelegramBot()
        
        # Mock the file index to simulate loaded files
        bot.file_index = {
            'file1': {
                'name': 'calculus_notes.pdf',
                'folder': '/University/Math',
                'description': 'calculus mathematics notes pdf',
                'size': 1024
            },
            'file2': {
                'name': 'python_tutorial.py',
                'folder': '/University/Programming',
                'description': 'python programming tutorial code',
                'size': 2048
            }
        }
        
        print(f"✅ Bot class imported successfully")
        print(f"✅ File index mocked with {len(bot.file_index)} files")
        
        # Test the search functionality
        search_results = bot.search_files("calculus", limit=5)
        print(f"✅ Search function works - found {len(search_results)} results for 'calculus'")
        
        # Create mock CallbackQuery object to test the fix
        class MockCallbackQuery:
            def __init__(self):
                self.from_user = MagicMock()
                self.from_user.id = 12345
                self.message = MagicMock()
                self.message.message_id = 123
                self.message.chat = MagicMock()
                
            async def answer(self):
                pass
                
            async def edit_message_text(self, text, parse_mode=None, reply_markup=None):
                print(f"📝 Mock message edit: {text[:50]}...")
                
        class MockContext:
            def __init__(self):
                self.user_data = {}
                
        # Test the callback handling
        mock_query = MockCallbackQuery()
        mock_context = MockContext()
        
        # Test the handle_ai_search method with CallbackQuery object
        print("\n🔍 Testing handle_ai_search with CallbackQuery object...")
        
        # Mock the rate limiting methods
        bot.check_user_query_limit = lambda user_id: True
        
        # This should work without the AttributeError now
        await bot.handle_ai_search(mock_query, mock_context)
        
        print("✅ handle_ai_search completed without errors")
        print("✅ AI search mode set:", mock_context.user_data.get('ai_search_mode'))
        
        print("\n🎉 All tests passed! The callback fix is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_callback_fix())
    sys.exit(0 if success else 1)
