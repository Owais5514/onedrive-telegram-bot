#!/usr/bin/env python3
"""
OneDrive Folder Discovery Tool
Helps you find available folders in OneDrive root for bot configuration
"""

import os
import sys
import logging
from dotenv import load_dotenv
from indexer import OneDriveIndexer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Discover available folders in OneDrive root"""
    print("🔍 OneDrive Folder Discovery Tool")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found!")
        print("📋 Please copy .env.example to .env and fill in your credentials.")
        return 1
    
    try:
        # Create a temporary indexer to check folders
        indexer = OneDriveIndexer(target_folders=["dummy"], folder_config={})
        
        # Get access token to test connection
        token = indexer.get_access_token()
        if not token:
            print("❌ Failed to get access token. Check your Azure credentials in .env file.")
            return 1
        
        print("✅ Successfully connected to OneDrive!")
        print()
        
        # Get root items
        import requests
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://graph.microsoft.com/v1.0/users/{indexer.target_user_id}/drive/root/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error fetching OneDrive contents: {response.text}")
            return 1
        
        root_items = response.json().get('value', [])
        
        # Find folders
        folders = [item for item in root_items if 'folder' in item]
        files = [item for item in root_items if 'file' in item]
        
        print(f"📁 Found {len(folders)} folders and {len(files)} files in OneDrive root")
        print()
        
        if folders:
            print("📂 Available folders for bot configuration:")
            print("-" * 40)
            for i, folder in enumerate(folders, 1):
                folder_name = folder.get('name', 'Unknown')
                item_count = folder.get('folder', {}).get('childCount', 'Unknown')
                print(f"{i:2d}. {folder_name} ({item_count} items)")
            
            print()
            print("💡 To use any of these folders, edit main.py and change:")
            print("   ONEDRIVE_FOLDERS = [\"YourFolderName\"]")
            print()
            print("📖 See CONFIG_EXAMPLES.md for more configuration examples")
        else:
            print("📭 No folders found in OneDrive root directory")
            print("💡 You may need to create a folder first in OneDrive")
        
        if files:
            print()
            print(f"📄 Note: {len(files)} files found in root (files are ignored, only folders are used)")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Error during folder discovery: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
