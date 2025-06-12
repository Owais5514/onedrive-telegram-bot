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
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Import Git integration for index persistence
try:
    from git_integration import git_manager
    GIT_AVAILABLE = True
except ImportError:
    git_manager = None
    GIT_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneDriveIndexer:
    def __init__(self, target_folders=None, folder_config=None):
        """Initialize the OneDrive indexer with Azure credentials and folder configuration"""
        # Set default configuration if not provided
        if target_folders is None:
            target_folders = ["Sharing"]  # Default fallback
        if folder_config is None:
            folder_config = {
                "case_sensitive": False,
                "search_subfolders": False,
                "require_all_folders": False
            }
        
        self.target_folders = target_folders
        self.folder_config = folder_config
        
        logger.info(f"Configured to search for folders: {target_folders}")
        logger.info(f"Folder search config: {folder_config}")
        
        # Load environment variables
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.target_user_id = os.getenv('TARGET_USER_ID')
        
        # Validate required environment variables
        missing_vars = []
        if not self.client_id:
            missing_vars.append('AZURE_CLIENT_ID')
        if not self.client_secret:
            missing_vars.append('AZURE_CLIENT_SECRET')
        if not self.tenant_id:
            missing_vars.append('AZURE_TENANT_ID')
        if not self.target_user_id:
            missing_vars.append('TARGET_USER_ID')
            
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Please ensure these are set in your .env file or environment")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info(f"Initializing OneDrive indexer for user: {self.target_user_id}")
        logger.info(f"Using tenant: {self.tenant_id}")
        
        # Initialize MSAL app
        try:
            self.app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize MSAL application: {e}")
            raise
        
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
        
        # Git integration for index persistence
        self.git_enabled = GIT_AVAILABLE and git_manager is not None
        if self.git_enabled:
            logger.info("Git integration enabled for index persistence")
        else:
            logger.info("Git integration not available")

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

    def find_target_folders(self) -> List[Dict]:
        """Find the target folders in the user's OneDrive root based on configuration"""
        token = self.get_access_token()
        if not token:
            return []
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.target_user_id}/drive/root/children"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error fetching root items: {response.text}")
                return []
                
            root_items = response.json().get('value', [])
            logger.info(f"Found {len(root_items)} items in OneDrive root")
            
            found_folders = []
            available_folders = []
            
            for item in root_items:
                if 'folder' in item:
                    folder_name = item.get('name', '')
                    available_folders.append(folder_name)
                    
                    # Check if this folder matches any of our target folders
                    for target_folder in self.target_folders:
                        if self.folder_config.get("case_sensitive", False):
                            name_match = folder_name == target_folder
                        else:
                            name_match = folder_name.lower() == target_folder.lower()
                        
                        if name_match:
                            logger.info(f"Found target folder: {folder_name}")
                            found_folders.append(item)
                            break
            
            logger.info(f"Available folders: {available_folders}")
            logger.info(f"Found {len(found_folders)} target folders: {[f['name'] for f in found_folders]}")
            
            # Check if we meet the requirements
            if self.folder_config.get("require_all_folders", False):
                if len(found_folders) < len(self.target_folders):
                    missing = set(self.target_folders) - set(f['name'] for f in found_folders)
                    logger.error(f"Not all required folders found. Missing: {missing}")
                    return []
            elif not found_folders:
                logger.error(f"None of the target folders found: {self.target_folders}")
                return []
            
            return found_folders
            
        except Exception as e:
            logger.error(f"Error finding target folders: {e}")
            return []

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
        """Build complete file index from OneDrive Sharing folder"""
        # Check if we should use cached index
        if not force_rebuild and os.path.exists(self.index_file) and os.path.exists(self.timestamp_file):
            try:
                with open(self.timestamp_file, 'r') as f:
                    last_update = float(f.read().strip())
                time_since_update = datetime.now().timestamp() - last_update
                
                # If index is less than 1 week old, use cached version
                if time_since_update < 604800:  # 1 week (7 days * 24 hours * 3600 seconds)
                    days_ago = time_since_update / 86400  # Convert to days
                    if days_ago < 1:
                        logger.info(f"Using cached index (updated {time_since_update/3600:.1f} hours ago)")
                    else:
                        logger.info(f"Using cached index (updated {days_ago:.1f} days ago)")
                    self.load_cached_index()
                    return True
            except Exception as e:
                logger.warning(f"Error reading cached index: {e}")
        
        logger.info("Building new file index...")
        
        # Reset stats
        self.total_folders = 0
        self.total_files = 0
        self.total_size = 0
        
        # Find target folders
        target_folders = self.find_target_folders()
        if not target_folders:
            return False
        
        # Initialize index with target folders
        # For now, we'll use the first found folder as root for backward compatibility
        # In the future, this could be expanded to support multiple root folders
        primary_folder = target_folders[0]
        self.file_index = {'root': primary_folder['id']}
        
        logger.info(f"Using primary folder '{primary_folder['name']}' as root")
        
        # Start recursive indexing
        success = self.index_folder(primary_folder['id'], 'root')
        
        if success:
            self.save_index()
            logger.info(f"✅ Index built successfully!")
            logger.info(f"📊 Total: {self.total_folders} folders, {self.total_files} files")
            logger.info(f"💾 Total size: {self.total_size / (1024*1024*1024):.2f} GB")
            return True
        else:
            logger.error("❌ Failed to build index")
            return False

    def initialize_index(self) -> bool:
        """Initialize index by loading cached version or building if necessary"""
        # Try to load from Git index branch first (GitHub Actions environment)
        if self.git_enabled and git_manager.is_github_actions:
            logger.info("GitHub Actions environment detected, trying to load index from Git...")
            if git_manager.load_index_from_branch([self.index_file, self.timestamp_file]):
                logger.info("Index files loaded from Git index branch")
        
        # First try to load existing cached index
        if os.path.exists(self.index_file) and os.path.exists(self.timestamp_file):
            try:
                with open(self.timestamp_file, 'r') as f:
                    last_update = float(f.read().strip())
                time_since_update = datetime.now().timestamp() - last_update
                
                # If index is less than 1 week old, just load it
                if time_since_update < 604800:  # 1 week (7 days * 24 hours * 3600 seconds)
                    days_ago = time_since_update / 86400  # Convert to days
                    if days_ago < 1:
                        logger.info(f"Loading cached index (updated {time_since_update/3600:.1f} hours ago)")
                    else:
                        logger.info(f"Loading cached index (updated {days_ago:.1f} days ago)")
                    self.load_cached_index()
                    return True
                else:
                    logger.info(f"Cached index is {time_since_update/86400:.1f} days old, rebuilding...")
            except Exception as e:
                logger.warning(f"Error reading cached index timestamp: {e}")
        
        # If no valid cache, build new index
        return self.build_index()

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
            
            # Commit to Git if available and in GitHub Actions
            if self.git_enabled and git_manager.is_github_actions:
                logger.info("Committing index files to Git repository...")
                if git_manager.commit_to_index_branch([self.index_file, self.timestamp_file]):
                    logger.info("✅ Index files committed to Git repository")
                else:
                    logger.warning("⚠️ Failed to commit index files to Git repository")
            
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
