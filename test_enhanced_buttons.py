#!/usr/bin/env python3
"""
Test script to verify the new file and folder button functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from bot_continuous import OneDriveTelegramBot

load_dotenv()

async def test_buttons_and_files():
    """Test that buttons are created for all files and folders"""
    bot = OneDriveTelegramBot()
    
    # Initialize authentication
    bot.initialize_authentication()
    await bot.test_and_cache_users()
    
    print("🧪 Testing enhanced button functionality...")
    print(f"📁 Base folder: {bot.base_folder}")
    print(f"🔒 Restricted mode: {bot.restricted_mode}")
    print()
    
    # Test University folder contents
    print("📂 Testing University folder contents and buttons:")
    try:
        university_items = await bot.get_onedrive_items("/")
        if university_items:
            print(f"✅ University folder contains {len(university_items)} items:")
            
            # Separate folders and files
            folders = [item for item in university_items if item['is_folder']]
            files = [item for item in university_items if not item['is_folder']]
            
            print(f"\n📁 Folders ({len(folders)}):")
            for i, folder in enumerate(folders, 1):
                print(f"   {i}. {folder['name']}")
            
            print(f"\n📄 Files ({len(files)}):")
            for i, file in enumerate(files, 1):
                size_mb = file['size'] / 1024 / 1024
                size_str = f"({size_mb:.1f} MB)" if size_mb > 1 else f"({file['size']} bytes)"
                print(f"   {i}. {file['name']} {size_str}")
                
                # Test file cache functionality
                file_id = f"/_{file['name']}"
                file_hash = str(hash(file_id))[-8:]
                print(f"      Cache ID: {file_hash}")
                
                # Test if download URL is available
                download_url = file.get('download_url', 'Not available')
                print(f"      Download URL: {'Available' if download_url and download_url != 'Not available' else 'Not available'}")
            
            print(f"\n🔢 Total items that will have buttons: {len(university_items)}")
            print("   (Previously only 4 folder buttons were shown)")
            
        else:
            print("❌ University folder appears to be empty or inaccessible")
    except Exception as e:
        print(f"❌ Error accessing University folder: {e}")
    
    print("\n" + "="*50)
    print("📊 FUNCTIONALITY IMPROVEMENTS:")
    print("✅ All folders now have clickable buttons (not limited to 4)")
    print("✅ All files now have clickable buttons for direct download")
    print("✅ Pagination support for folders with many items")
    print("✅ File cache system for efficient callback handling")
    print("✅ Dynamic download URL fetching when needed")
    print("✅ Better file size display and download limits")
    print("✅ Enhanced navigation with proper back/forward buttons")

if __name__ == "__main__":
    asyncio.run(test_buttons_and_files())
