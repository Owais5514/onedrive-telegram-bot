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
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dotenv import load_dotenv

# Import database manager for persistent storage
try:
    from database import db_manager
    DB_AVAILABLE = True
except ImportError:
    db_manager = None
    DB_AVAILABLE = False

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
        
        # File paths (fallback storage)
        self.index_file = 'file_index.json'
        self.timestamp_file = 'index_timestamp.txt'
        
        # Database keys for cache storage
        self.db_index_key = 'file_index'
        self.db_timestamp_key = 'index_timestamp'
        
        # Cache
        self.file_index = {}
        self.access_token = None
        self.token_expires = None
        
        # Stats
        self.total_folders = 0
        self.total_files = 0
        self.total_size = 0
        
        # Progress tracking for async operations
        self.is_indexing = False
        self.indexing_progress = 0
        self.indexing_total = 0
        self.indexing_current_path = ""
        self.progress_callback = None
        
        # Database integration for index persistence
        self.db_enabled = DB_AVAILABLE and db_manager and db_manager.enabled
        if self.db_enabled:
            logger.info("Database integration enabled for file index persistence")
        else:
            logger.info("Database not available for file index - using file storage")
        
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

    async def get_access_token_async(self) -> Optional[str]:
        """Get valid access token for Microsoft Graph API (async version)"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
            
        try:
            # Run token acquisition in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.token_expires = datetime.now() + timedelta(seconds=result.get("expires_in", 3600) - 300)
                logger.info("Access token acquired successfully (async)")
                return self.access_token
            else:
                logger.error(f"No access token in result: {result}")
        except Exception as e:
            logger.error(f"Error getting access token (async): {e}")
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

    async def find_target_folders_async(self) -> List[Dict]:
        """Find the target folders in the user's OneDrive root based on configuration (async version)"""
        token = await self.get_access_token_async()
        if not token:
            return []
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.target_user_id}/drive/root/children"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error fetching root items: {error_text}")
                        return []
                        
                    data = await response.json()
                    root_items = data.get('value', [])
                    
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
            logger.error(f"Error finding target folders (async): {e}")
            return []

    def index_folder(self, folder_id: str, path: str, depth: int = 0, max_depth: int = 0) -> bool:
        """Recursively index folder contents with depth tracking and optional depth limit"""
        # Check depth limit
        if max_depth > 0 and depth >= max_depth:
            logger.info(f"{'  ' * depth}Reached max depth ({max_depth}) for: {path}")
            return True
            
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
            
            # Recursively index subfolders if within depth limit
            if max_depth == 0 or depth < max_depth - 1:
                for folder_item in folders_in_current:
                    subfolder_path = f"{path}/{folder_item['name']}" if path != 'root' else folder_item['name']
                    success = self.index_folder(folder_item['id'], subfolder_path, depth + 1, max_depth)
                    if not success:
                        logger.warning(f"Failed to index subfolder: {subfolder_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing folder {path}: {e}")
            return False

    async def index_folder_async(self, folder_id: str, path: str, depth: int = 0, max_depth: int = 0, session: aiohttp.ClientSession = None) -> bool:
        """Recursively index folder contents with depth tracking and optional depth limit (async version)"""
        # Check depth limit
        if max_depth > 0 and depth >= max_depth:
            logger.info(f"{'  ' * depth}Reached max depth ({max_depth}) for: {path}")
            return True
            
        token = await self.get_access_token_async()
        if not token:
            return False
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.target_user_id}/drive/items/{folder_id}/children"
            
            # Update progress
            self.indexing_current_path = path
            if self.progress_callback:
                try:
                    await self.progress_callback(self.indexing_progress, self.indexing_total, path)
                except Exception as e:
                    logger.warning(f"Error in progress callback: {e}")
            
            logger.info(f"{'  ' * depth}Indexing: {path}")
            
            # Use existing session or create new one
            close_session = False
            if session is None:
                session = aiohttp.ClientSession()
                close_session = True
            
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error fetching folder contents for {path}: {error_text}")
                        return False
                        
                    data = await response.json()
                    items = data.get('value', [])
            finally:
                if close_session:
                    await session.close()
            
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
            
            # Update progress after processing current folder
            self.indexing_progress += 1
            
            # Recursively index subfolders if within depth limit
            if max_depth == 0 or depth < max_depth - 1:
                if folders_in_current:
                    # Use optimized batch processing for better performance
                    success = await self.batch_index_folders_async(folders_in_current, path, depth, max_depth, session)
                    if not success:
                        logger.warning(f"Some subfolders in {path} failed to index")
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing folder {path} (async): {e}")
            return False

    async def batch_index_folders_async(self, folder_items: List[Dict], parent_path: str, depth: int = 0, max_depth: int = 0, session: aiohttp.ClientSession = None) -> bool:
        """Process multiple folders concurrently with better rate limiting and error handling"""
        if not folder_items:
            return True
            
        # Limit concurrent requests to avoid Microsoft Graph API rate limits
        semaphore = asyncio.Semaphore(5)  # Increased from 3 to 5 for better performance
        
        async def process_single_folder(folder_item):
            async with semaphore:
                subfolder_path = f"{parent_path}/{folder_item['name']}" if parent_path != 'root' else folder_item['name']
                try:
                    # Add exponential backoff for rate limiting
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # Small delay to prevent overwhelming the API
                            await asyncio.sleep(0.05 * (2 ** attempt))  # Exponential backoff
                            success = await self.index_folder_async(folder_item['id'], subfolder_path, depth + 1, max_depth, session)
                            return success
                        except Exception as e:
                            if attempt == max_retries - 1:
                                logger.warning(f"Failed to index subfolder {subfolder_path} after {max_retries} attempts: {e}")
                                return False
                            else:
                                logger.debug(f"Retry {attempt + 1} for folder {subfolder_path}: {e}")
                                await asyncio.sleep(1 * (2 ** attempt))  # Wait before retry
                except Exception as e:
                    logger.warning(f"Failed to index subfolder {subfolder_path}: {e}")
                    return False
        
        # Update total count for progress tracking
        self.indexing_total += len(folder_items)
        
        # Process folders in batches to avoid memory issues with very large directories
        batch_size = 10  # Process 10 folders at a time
        
        for i in range(0, len(folder_items), batch_size):
            batch = folder_items[i:i + batch_size]
            tasks = [process_single_folder(folder_item) for folder_item in batch]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any failures
                for j, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(f"Exception processing folder {batch[j]['name']}: {result}")
                    elif not result:
                        logger.warning(f"Failed to process folder: {batch[j]['name']}")
                        
                # Small delay between batches to be kind to the API
                if i + batch_size < len(folder_items):
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error processing folder batch: {e}")
                return False
        
        return True

    async def optimize_token_management(self):
        """Proactively refresh tokens to avoid delays during indexing"""
        try:
            # Check if token will expire soon (within 5 minutes)
            if self.token_expires and (self.token_expires - datetime.now()).total_seconds() < 300:
                logger.info("Proactively refreshing access token...")
                await self.get_access_token_async()
        except Exception as e:
            logger.warning(f"Error in proactive token refresh: {e}")

    def set_progress_callback(self, callback: Callable):
        """Set progress callback for external monitoring"""
        self.progress_callback = callback

    def get_indexing_status(self) -> Dict[str, Any]:
        """Get current indexing status and progress"""
        return {
            'is_indexing': self.is_indexing,
            'progress': self.indexing_progress,
            'total': self.indexing_total,
            'current_path': self.indexing_current_path,
            'completion_percentage': int((self.indexing_progress / self.indexing_total) * 100) if self.indexing_total > 0 else 0
        }

    def build_index(self, force_rebuild: bool = False) -> bool:
        """Build complete file index from OneDrive target folders (legacy method)"""
        # Check if we should use cached index (try database first, then files)
        if not force_rebuild:
            last_update = None
            
            # Try to get timestamp from database first
            if self.db_enabled:
                try:
                    timestamp_data = db_manager.get_cache(self.db_timestamp_key)
                    if timestamp_data and 'timestamp' in timestamp_data:
                        last_update = timestamp_data['timestamp']
                        logger.debug("Retrieved timestamp from database")
                except Exception as e:
                    logger.debug(f"Could not get timestamp from database: {e}")
            
            # Fallback to file timestamp
            if last_update is None and os.path.exists(self.timestamp_file):
                try:
                    with open(self.timestamp_file, 'r') as f:
                        last_update = float(f.read().strip())
                        logger.debug("Retrieved timestamp from file")
                except Exception as e:
                    logger.debug(f"Could not get timestamp from file: {e}")
            
            # Check if we have a valid cached index
            if last_update:
                try:
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
                    logger.warning(f"Error checking cached index: {e}")
        
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
        success = self.index_folder(primary_folder['id'], 'root', 0, 0)  # 0 for unlimited depth
        
        if success:
            self.save_index()
            logger.info(f"✅ Index built successfully!")
            logger.info(f"📊 Total: {self.total_folders} folders, {self.total_files} files")
            logger.info(f"💾 Total size: {self.total_size / (1024*1024*1024):.2f} GB")
            return True
        else:
            logger.error("❌ Failed to build index")
            return False

    async def build_index_async(self, force_rebuild: bool = False, progress_callback: Callable = None) -> bool:
        """Build complete file index from OneDrive target folders (async version with progress tracking)"""
        if self.is_indexing:
            logger.warning("Indexing already in progress")
            return False
            
        self.is_indexing = True
        self.progress_callback = progress_callback
        
        try:
            # Check if we should use cached index (try database first, then files)
            if not force_rebuild:
                last_update = None
                
                # Try to get timestamp from database first
                if self.db_enabled:
                    try:
                        timestamp_data = db_manager.get_cache(self.db_timestamp_key)
                        if timestamp_data and 'timestamp' in timestamp_data:
                            last_update = timestamp_data['timestamp']
                            logger.debug("Retrieved timestamp from database")
                    except Exception as e:
                        logger.debug(f"Could not get timestamp from database: {e}")
                
                # Fallback to file timestamp
                if last_update is None and os.path.exists(self.timestamp_file):
                    try:
                        with open(self.timestamp_file, 'r') as f:
                            last_update = float(f.read().strip())
                            logger.debug("Retrieved timestamp from file")
                    except Exception as e:
                        logger.debug(f"Could not get timestamp from file: {e}")
                
                # Check if we have a valid cached index
                if last_update:
                    try:
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
                        logger.warning(f"Error checking cached index: {e}")
            
            logger.info("Building new file index (async)...")
            
            # Optimize token management before starting
            await self.optimize_token_management()
            
            # Reset stats
            self.total_folders = 0
            self.total_files = 0
            self.total_size = 0
            self.indexing_progress = 0
            self.indexing_total = 1  # Start with 1 for the initial folder discovery
            
            # Find target folders
            target_folders = await self.find_target_folders_async()
            if not target_folders:
                return False
            
            # Initialize index with target folders
            primary_folder = target_folders[0]
            self.file_index = {'root': primary_folder['id']}
            
            logger.info(f"Using primary folder '{primary_folder['name']}' as root")
            
            # Create a session for reuse
            async with aiohttp.ClientSession() as session:
                # Start recursive indexing
                success = await self.index_folder_async(primary_folder['id'], 'root', 0, 0, session)
            
            if success:
                self.save_index()
                logger.info(f"✅ Index built successfully (async)!")
                logger.info(f"📊 Total: {self.total_folders} folders, {self.total_files} files")
                logger.info(f"💾 Total size: {self.total_size / (1024*1024*1024):.2f} GB")
                return True
            else:
                logger.error("❌ Failed to build index (async)")
                return False
                
        except Exception as e:
            logger.error(f"Error in async build_index: {e}")
            return False
        finally:
            self.is_indexing = False
            self.progress_callback = None

    def initialize_index(self) -> bool:
        """Initialize index by loading cached version or building if necessary"""
        # Try database first, then file fallback, then rebuild
        
        last_update = None
        
        # Try to get timestamp from database first
        if self.db_enabled:
            try:
                timestamp_data = db_manager.get_cache(self.db_timestamp_key)
                if timestamp_data and 'timestamp' in timestamp_data:
                    last_update = timestamp_data['timestamp']
                    logger.debug("Found timestamp in database")
            except Exception as e:
                logger.debug(f"Could not get timestamp from database: {e}")
        
        # Fallback to file timestamp if database not available
        if last_update is None and os.path.exists(self.timestamp_file):
            try:
                with open(self.timestamp_file, 'r') as f:
                    last_update = float(f.read().strip())
                    logger.debug("Found timestamp in file")
            except Exception as e:
                logger.debug(f"Could not get timestamp from file: {e}")
        
        # Check if we have a valid cached index
        if last_update:
            try:
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
                logger.warning(f"Error checking cached index timestamp: {e}")
        
        # If no valid cache, build new index
        return self.build_index()

    def load_cached_index(self):
        """Load cached index from database with file fallback"""
        try:
            # Try database first
            if self.db_enabled:
                try:
                    cached_index = db_manager.get_cache(self.db_index_key)
                    if cached_index:
                        self.file_index = cached_index
                        logger.info(f"✅ Loaded cached index from database ({len(self.file_index)} paths)")
                        return
                    else:
                        logger.info("No cached index found in database, trying file fallback")
                except Exception as e:
                    logger.warning(f"Failed to load index from database: {e}, trying file fallback")
            
            # Fallback to file
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r') as f:
                    self.file_index = json.load(f)
                logger.info(f"✅ Loaded cached index from file ({len(self.file_index)} paths)")
            else:
                logger.info("No cached index file found")
                
        except Exception as e:
            logger.error(f"Error loading cached index: {e}")
            self.file_index = {}

    def save_index(self, append_mode=False):
        """Save index and timestamp to database with file fallback"""
        timestamp = datetime.now().timestamp()
        
        try:
            # Handle append mode
            if append_mode:
                if self.db_enabled:
                    # Load existing index from database and merge
                    existing_index = db_manager.get_cache(self.db_index_key)
                    if existing_index:
                        logger.info("Loading existing index from database for append mode...")
                        merged_index = existing_index.copy()
                        merged_index.update(self.file_index)
                        self.file_index = merged_index
                        logger.info(f"Merged with existing index (now {len(self.file_index)} total paths)")
                elif os.path.exists(self.index_file):
                    # Fallback to file-based append
                    logger.info("Loading existing index from file for append mode...")
                    try:
                        with open(self.index_file, 'r') as f:
                            existing_index = json.load(f)
                        
                        merged_index = existing_index.copy()
                        merged_index.update(self.file_index)
                        self.file_index = merged_index
                        logger.info(f"Merged with existing index (now {len(self.file_index)} total paths)")
                    except Exception as e:
                        logger.warning(f"Failed to load existing index for append: {e}")
                        logger.info("Creating new index instead")
            
            # Try to save to database first
            if self.db_enabled:
                try:
                    # Save index to database
                    if db_manager.save_cache(self.db_index_key, self.file_index):
                        # Save timestamp to database
                        db_manager.save_cache(self.db_timestamp_key, {'timestamp': timestamp})
                        logger.info(f"✅ Index saved to database ({len(self.file_index)} paths)")
                        
                        # Also save to file as backup
                        self._save_index_to_file(timestamp)
                        return
                    else:
                        logger.warning("Failed to save index to database, falling back to file")
                except Exception as e:
                    logger.warning(f"Database save failed: {e}, falling back to file")
            
            # Fallback to file storage
            self._save_index_to_file(timestamp)
            logger.info("✅ Index saved to file (database not available)")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _save_index_to_file(self, timestamp):
        """Helper method to save index to files"""
        # Save index
        with open(self.index_file, 'w') as f:
            json.dump(self.file_index, f, indent=2)
        
        # Save timestamp
        with open(self.timestamp_file, 'w') as f:
            f.write(str(timestamp))
            
        logger.debug(f"Index and timestamp saved to files")

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
            # Try to get timestamp from database first
            if self.db_enabled:
                try:
                    timestamp_data = db_manager.get_cache(self.db_timestamp_key)
                    if timestamp_data and 'timestamp' in timestamp_data:
                        stats['last_updated'] = datetime.fromtimestamp(timestamp_data['timestamp'])
                        logger.debug("Got timestamp from database for stats")
                except Exception as e:
                    logger.debug(f"Could not get timestamp from database for stats: {e}")
            
            # Fallback to file timestamp
            if stats['last_updated'] is None and os.path.exists(self.timestamp_file):
                with open(self.timestamp_file, 'r') as f:
                    timestamp = float(f.read().strip())
                    stats['last_updated'] = datetime.fromtimestamp(timestamp)
                    logger.debug("Got timestamp from file for stats")
            
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
    parser.add_argument('--folder', type=str, help='Specific folder name to index')
    parser.add_argument('--append', action='store_true', help='Append to existing index instead of replacing')
    parser.add_argument('--replace', action='store_true', help='Replace existing index (default behavior)')
    parser.add_argument('--max-depth', type=int, default=0, help='Maximum folder depth to index (0 for unlimited)')
    
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
    if args.folder:
        # Use new folder-specific indexing
        append_mode = args.append and not args.replace
        success = indexer.build_index_for_folder(
            folder_name=args.folder,
            force_rebuild=args.force,
            append_mode=append_mode,
            max_depth=args.max_depth
        )
        
        if success:
            print(f"✅ Index built successfully for folder '{args.folder}'!")
            if append_mode:
                print("📝 Index was appended to existing data")
            else:
                print("🔄 Index was created/replaced")
        else:
            print(f"❌ Failed to build index for folder '{args.folder}'")
            return 1
    else:
        # Use legacy target folders method
        success = indexer.build_index(force_rebuild=args.force)
        if success:
            print("✅ Index built successfully!")
        else:
            print("❌ Failed to build index")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
