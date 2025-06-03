#!/usr/bin/env python3
"""
OneDrive File Indexer
Handles indexing of OneDrive files and folders for the Telegram bot
Can be run independently or imported by other scripts
"""

import os
import json
import logging
import msal
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneDriveIndexer:
    def __init__(self):
        """Initialize the OneDrive indexer with Azure credentials"""
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET') 
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.target_user_id = os.getenv('TARGET_USER_ID', 'owais5514@0s7s6.onmicrosoft.com')
        
        # Initialize MSAL app
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        
        # File paths
        self.index_file = 'file_index.json'
        self.timestamp_file = 'index_timestamp.txt'
        
        # Cache
        self.file_index = {}
        self.access_token = None
        self.token_expires = None
        
        # Stats
        self.total_folders = 0
        self.total_files = 0
        self.total_size = 0

    def get_access_token(self) -> Optional[str]:
        """Get valid access token for Microsoft Graph API"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
            
        try:
            result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.token_expires = datetime.now() + timedelta(seconds=result.get("expires_in", 3600) - 300)
                logger.info("Access token acquired successfully")
                return self.access_token
            else:
                logger.error(f"No access token in result: {result}")
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
        return None

    def find_university_folder(self) -> Optional[Dict]:
        """Find the University folder in the target user's OneDrive root"""
        token = self.get_access_token()
        if not token:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.target_user_id}/drive/root/children"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error fetching root items: {response.text}")
                return None
                
            root_items = response.json().get('value', [])
            logger.info(f"Found {len(root_items)} items in OneDrive root")
            
            for item in root_items:
                if item.get('name', '').lower() == 'university' and 'folder' in item:
                    logger.info(f"Found University folder: {item['name']}")
                    return item
            
            logger.error("University folder not found")
            available_folders = [item.get('name') for item in root_items if 'folder' in item]
            logger.info(f"Available folders: {available_folders}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding University folder: {e}")
            return None

    def index_folder(self, folder_id: str, path: str, depth: int = 0) -> bool:
        """Recursively index folder contents with depth tracking"""
        token = self.get_access_token()
        if not token:
            return False
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.target_user_id}/drive/items/{folder_id}/children"
            
            logger.info(f"{'  ' * depth}Indexing: {path}")
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error fetching folder contents for {path}: {response.text}")
                return False
                
            items = response.json().get('value', [])
            self.file_index[path] = []
            
            folders_in_current = []
            files_in_current = []
            
            for item in items:
                item_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': 'folder' if 'folder' in item else 'file',
                    'size': item.get('size', 0),
                    'modified': item.get('lastModifiedDateTime', ''),
                    'path': f"{path}/{item['name']}" if path != 'root' else item['name']
                }
                
                if 'file' in item:
                    item_info['download_url'] = item.get('@microsoft.graph.downloadUrl', '')
                    files_in_current.append(item)
                    self.total_files += 1
                    self.total_size += item.get('size', 0)
                else:
                    folders_in_current.append(item)
                    self.total_folders += 1
                
                self.file_index[path].append(item_info)
            
            logger.info(f"{'  ' * depth}Found {len(folders_in_current)} folders and {len(files_in_current)} files in {path}")
            
            # Recursively index subfolders
            for folder_item in folders_in_current:
                subfolder_path = f"{path}/{folder_item['name']}" if path != 'root' else folder_item['name']
                success = self.index_folder(folder_item['id'], subfolder_path, depth + 1)
                if not success:
                    logger.warning(f"Failed to index subfolder: {subfolder_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing folder {path}: {e}")
            return False

    def build_index(self, force_rebuild: bool = False) -> bool:
        """Build complete file index from OneDrive University folder"""
        # Check if we should use cached index
        if not force_rebuild and os.path.exists(self.index_file) and os.path.exists(self.timestamp_file):
            try:
                with open(self.timestamp_file, 'r') as f:
                    last_update = float(f.read().strip())
                time_since_update = datetime.now().timestamp() - last_update
                
                # If index is less than 1 hour old, use cached version
                if time_since_update < 3600:  # 1 hour
                    logger.info(f"Using cached index (updated {time_since_update/60:.1f} minutes ago)")
                    self.load_cached_index()
                    return True
            except Exception as e:
                logger.warning(f"Error reading cached index: {e}")
        
        logger.info("Building new file index...")
        
        # Reset stats
        self.total_folders = 0
        self.total_files = 0
        self.total_size = 0
        
        # Find University folder
        university_folder = self.find_university_folder()
        if not university_folder:
            return False
        
        # Initialize index with University folder as root
        self.file_index = {'root': university_folder['id']}
        
        # Start recursive indexing
        success = self.index_folder(university_folder['id'], 'root')
        
        if success:
            self.save_index()
            logger.info(f"✅ Index built successfully!")
            logger.info(f"📊 Total: {self.total_folders} folders, {self.total_files} files")
            logger.info(f"💾 Total size: {self.total_size / (1024*1024*1024):.2f} GB")
            return True
        else:
            logger.error("❌ Failed to build index")
            return False

    def load_cached_index(self):
        """Load cached index from file"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r') as f:
                    self.file_index = json.load(f)
                logger.info(f"Loaded cached index with {len(self.file_index)} paths")
        except Exception as e:
            logger.error(f"Error loading cached index: {e}")

    def save_index(self):
        """Save index and timestamp to files"""
        try:
            # Save index
            with open(self.index_file, 'w') as f:
                json.dump(self.file_index, f, indent=2)
            
            # Save timestamp
            with open(self.timestamp_file, 'w') as f:
                f.write(str(datetime.now().timestamp()))
                
            logger.info(f"Index saved to {self.index_file}")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def get_folder_contents(self, path: str = 'root') -> List[Dict]:
        """Get folder contents from cached index"""
        return self.file_index.get(path, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        stats = {
            'total_paths': len(self.file_index),
            'total_folders': 0,
            'total_files': 0,
            'total_size': 0,
            'last_updated': None
        }
        
        try:
            if os.path.exists(self.timestamp_file):
                with open(self.timestamp_file, 'r') as f:
                    timestamp = float(f.read().strip())
                    stats['last_updated'] = datetime.fromtimestamp(timestamp)
            
            # Count files and folders from index
            for path, items in self.file_index.items():
                if isinstance(items, list):
                    for item in items:
                        if item.get('type') == 'file':
                            stats['total_files'] += 1
                            stats['total_size'] += item.get('size', 0)
                        elif item.get('type') == 'folder':
                            stats['total_folders'] += 1
                            
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            
        return stats

    def search_files(self, query: str) -> List[Dict]:
        """Search for files by name"""
        results = []
        query_lower = query.lower()
        
        for path, items in self.file_index.items():
            if isinstance(items, list):
                for item in items:
                    if query_lower in item.get('name', '').lower():
                        item_copy = item.copy()
                        item_copy['folder_path'] = path
                        results.append(item_copy)
        
        return results

def main():
    """Main function for running indexer independently"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OneDrive File Indexer')
    parser.add_argument('--force', '-f', action='store_true', help='Force rebuild index')
    parser.add_argument('--stats', '-s', action='store_true', help='Show index statistics')
    parser.add_argument('--search', type=str, help='Search for files')
    
    args = parser.parse_args()
    
    indexer = OneDriveIndexer()
    
    if args.stats:
        indexer.load_cached_index()
        stats = indexer.get_stats()
        print(f"\n📊 Index Statistics:")
        print(f"   Total paths: {stats['total_paths']}")
        print(f"   Total folders: {stats['total_folders']}")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total size: {stats['total_size'] / (1024*1024*1024):.2f} GB")
        print(f"   Last updated: {stats['last_updated']}")
        return
    
    if args.search:
        indexer.load_cached_index()
        results = indexer.search_files(args.search)
        print(f"\n🔍 Search results for '{args.search}':")
        for result in results[:20]:  # Limit to 20 results
            print(f"   📄 {result['name']} (in {result['folder_path']})")
        if len(results) > 20:
            print(f"   ... and {len(results) - 20} more results")
        return
    
    # Build index
    success = indexer.build_index(force_rebuild=args.force)
    if success:
        print("✅ Index built successfully!")
    else:
        print("❌ Failed to build index")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
