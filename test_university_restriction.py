#!/usr/bin/env python3
"""
Test script to verify University folder restriction is working correctly
"""

import asyncio
import os
from dotenv import load_dotenv
from bot_continuous import OneDriveTelegramBot

load_dotenv()

async def test_university_restriction():
    """Test that the bot is properly restricted to University folder"""
    bot = OneDriveTelegramBot()
    
    # Initialize authentication
    bot.initialize_authentication()
    await bot.test_and_cache_users()
    
    print("🧪 Testing University folder restriction...")
    print(f"📁 Base folder: {bot.base_folder}")
    print(f"🔒 Restricted mode: {bot.restricted_mode}")
    print()
    
    # Test cases to verify restriction
    test_cases = [
        ("/", "Default root path"),
        ("", "Empty path"),
        ("Documents", "Trying to access Documents folder"),
        ("../", "Directory traversal attempt"),
        ("../Documents", "Directory traversal to Documents"),
        ("University/subfolder", "Valid University subfolder"),
        ("../../Desktop", "Multiple directory traversal attempt"),
    ]
    
    for path, description in test_cases:
        print(f"🔍 Testing: {description}")
        print(f"   Input path: '{path}'")
        
        try:
            items = await bot.get_onedrive_items(path)
            if items:
                print(f"   ✅ Returned {len(items)} items")
                # Show first few items as example
                for i, item in enumerate(items[:3]):
                    print(f"      - {item.get('name', 'Unknown')}")
                if len(items) > 3:
                    print(f"      ... and {len(items) - 3} more items")
            else:
                print("   ❌ No items returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
    
    # Test accessing University folder contents specifically
    print("📂 Testing University folder contents:")
    try:
        university_items = await bot.get_onedrive_items("University")
        if university_items:
            print(f"✅ University folder contains {len(university_items)} items:")
            for item in university_items:
                item_type = "📁" if item.get('folder') else "📄"
                print(f"   {item_type} {item.get('name', 'Unknown')}")
        else:
            print("❌ University folder appears to be empty or inaccessible")
    except Exception as e:
        print(f"❌ Error accessing University folder: {e}")

if __name__ == "__main__":
    asyncio.run(test_university_restriction())
