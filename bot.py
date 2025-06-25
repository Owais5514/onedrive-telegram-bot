import os
import json
import logging
import asyncio
import requests
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from indexer import OneDriveIndexer
from database import db_manager

# Import Git integration for feedback persistence
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

# AI features removed - keeping bot lightweight and focused

class OneDriveBot:
    async def send_keepalive_ping(self):
        """Send a keep-alive ping to maintain service activity during long operations (for Render)"""
        try:
            # If running under Render, update last_activity if present
            if hasattr(self, 'last_activity'):
                from datetime import datetime, timezone
                self.last_activity = datetime.now(timezone.utc)
            # Optionally, log or perform other keep-alive actions here
        except Exception as e:
            import logging
            logging.warning(f"Error sending keep-alive ping: {e}")
    def __init__(self, onedrive_folders=None, folder_config=None):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_USER_ID', '0'))
        
        # Set default folder configuration if not provided
        if onedrive_folders is None:
            onedrive_folders = ["Sharing"]  # Default fallback
        if folder_config is None:
            folder_config = {
                "case_sensitive": False,
                "search_subfolders": False,
                "require_all_folders": False
            }
        
        # Initialize OneDrive indexer with folder configuration
        self.indexer = OneDriveIndexer(
            target_folders=onedrive_folders,
            folder_config=folder_config
        )
        
        # Callback data mapping to handle long file names (max 64 bytes for Telegram)
        self.callback_map = {}
        self.callback_counter = 0
        
        # User and data management
        self.unlimited_users = set()
        
        # Feedback collection state
        self.awaiting_feedback = set()  # Track users who are providing feedback
        self.awaiting_mass_message = set()  # Track admins providing mass message
        self.awaiting_add_user = set()  # Track admin adding users manually
        
        # Database integration for data persistence
        if db_manager.enabled:
            logger.info("Database integration enabled for data persistence")
        else:
            logger.info("Database not available - using fallback file storage")
        
        # Track bot startup time for pending message handling
        self.startup_time = None
        
        # Initialize database and load data
        self.init_database()
        self.load_data()

    def init_database(self):
        """Initialize database and migrate data if needed"""
        if db_manager.enabled:
            logger.info("Initializing database...")
            if db_manager.create_tables():
                logger.info("Database tables ready")
                
                # Migrate existing file data if it exists and database is empty
                if db_manager.get_user_count() == 0:
                    logger.info("Database is empty, attempting to migrate from files...")
                    if db_manager.migrate_from_files('unlimited_users.json', 'feedback_log.txt'):
                        logger.info("Successfully migrated data from files")
                    else:
                        logger.info("No file data to migrate or migration failed")
            else:
                logger.error("Failed to initialize database tables")
        else:
            logger.warning("Database not available - will use file fallback (data may be lost on restart)")

    def load_data(self):
        """Load data from database or fallback to files"""
        try:
            if db_manager.enabled:
                # Load users from database
                self.unlimited_users = db_manager.get_all_users()
                logger.info(f"Loaded {len(self.unlimited_users)} users from database")
            else:
                # Fallback to file loading
                if os.path.exists('unlimited_users.json'):
                    with open('unlimited_users.json', 'r') as f:
                        self.unlimited_users = set(json.load(f))
                    logger.info(f"Loaded {len(self.unlimited_users)} users from file (fallback)")
        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def save_data(self):
        """Save data to database or fallback to files"""
        try:
            if db_manager.enabled:
                # Database automatically saves data, no need to explicitly save user list
                logger.debug("Using database - no manual save needed")
            else:
                # Fallback to file saving
                with open('unlimited_users.json', 'w') as f:
                    json.dump(list(self.unlimited_users), f)
                logger.info("Saved user data to file (fallback)")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def save_unlimited_users(self):
        """Save unlimited users to database or file - convenience method"""
        self.save_data()

    def get_folder_contents(self, path: str = 'root') -> List[Dict]:
        """Get folder contents from indexer"""
        return self.indexer.get_folder_contents(path)

    async def download_file_async(self, file_id: str) -> Optional[bytes]:
        """Download file from OneDrive asynchronously using aiohttp"""
        token = self.indexer.get_access_token()
        if not token:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.indexer.target_user_id}/drive/items/{file_id}/content"
            
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"HTTP {response.status} error downloading file {file_id}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading file {file_id}")
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
        return None

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from OneDrive using indexer's token (legacy sync method)"""
        token = self.indexer.get_access_token()
        if not token:
            return None
            
        try:
            import requests
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.indexer.target_user_id}/drive/items/{file_id}/content"
            response = requests.get(url, headers=headers, timeout=300)
            
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
        return None

    async def notify_subscribers(self, message: str):
        """Notify unlimited users"""
        for user_id in self.unlimited_users:
            try:
                msg = await self.application.bot.send_message(chat_id=user_id, text=message)
                # Delete message after 1 minute
                asyncio.create_task(self._delete_message_later(user_id, msg.message_id, 60))
            except Exception as e:
                logger.error(f"Error notifying user {user_id}: {e}")

    async def _delete_message_later(self, chat_id: int, message_id: int, delay: int):
        """Delete message after delay"""
        await asyncio.sleep(delay)
        try:
            await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    def create_callback_data(self, prefix: str, data: str) -> str:
        """Create short callback data for Telegram buttons (max 64 bytes)"""
        full_data = f"{prefix}_{data}"
        
        # If data is short enough, use it directly
        if len(full_data.encode('utf-8')) <= 64:
            return full_data
            
        # Otherwise, create a mapping
        self.callback_counter += 1
        short_id = f"{prefix}_{self.callback_counter}"
        self.callback_map[short_id] = data
        
        return short_id
    
    def resolve_callback_data(self, callback_data: str) -> str:
        """Resolve short callback data to original data"""
        if callback_data in self.callback_map:
            return self.callback_map[callback_data]
        
        # If not in map, assume it's direct data (remove prefix)
        if '_' in callback_data:
            return callback_data.split('_', 1)[1]
        
        return callback_data

    def _was_message_queued(self, update: Update) -> bool:
        """Check if this message was queued while bot was offline"""
        if self.startup_time and hasattr(update, 'message') and update.message:
            return update.message.date < self.startup_time
        return False

    def _add_queued_message_notice(self, text: str, was_queued: bool) -> str:
        """Add notice to message if it was queued"""
        if was_queued:
            return f"✅ Bot is now online and ready!\n(Your command was received while bot was starting)\n\n{text}"
        return text

    # Command handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # Add user to tracking system
        user_id = update.effective_user.id
        user = update.effective_user
        
        if user_id not in self.unlimited_users:
            self.unlimited_users.add(user_id)
            
            # Add to database if available
            if db_manager.enabled:
                db_manager.add_user(
                    user_id=user_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            else:
                self.save_data()  # Fallback to file
                
            logger.info(f"New user added: {user_id} (@{user.username})")
        
        keyboard = [
            [InlineKeyboardButton("📁 Browse Files", callback_data="browse_root")]
        ]
        
        # Add refresh index button only for admin
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("🔄 Refresh Index", callback_data="refresh_index")])
            
        # Add information and admin buttons
        keyboard.extend([
            [InlineKeyboardButton("❓ Help", callback_data="show_help"),
             InlineKeyboardButton("ℹ️ About", callback_data="show_about")],
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy"),
             InlineKeyboardButton("📝 Feedback", callback_data="show_feedback")]
        ])
        
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🎓 Welcome to OneDrive Sharing Bot!\n\n"
        )
        
        # Check if this is a queued command from when bot was offline
        if self._was_message_queued(update):
            welcome_text = self._add_queued_message_notice(welcome_text, True)
        
        welcome_text += "📂 Browse and download sharing files\n"
        
        if update.effective_user.id == self.admin_id:
            welcome_text += "� Admin controls available\n"
            
        welcome_text += "\nSelect an option below:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 OneDrive Sharing Bot Help\n\n"
            "📋 Available Commands:\n"
            "• /start - Start the bot and show main menu\n"
            "• /menu - Show bot menu with options\n"
            "• /help - Show this help message\n"
            "• /about - About this bot\n"
            "• /privacy - Privacy policy\n"
            "• /feedback - Submit feedback or report issues\n"
            "• /admin - Admin panel (admin only)\n\n"
            "🗂️ Navigation & Usage:\n"
            "• 📁 Browse Files - Explore sharing folders\n"
            "• ⬅️ Back - Navigate to parent folder\n"
            "• 🏠 Main Menu - Return to start screen\n"
            "• 🔄 Refresh - Update file index (admin only)\n\n"
            "⚡ Performance: Files are cached for speed"
        )
        
        # Add queued message notice if applicable
        help_text = self._add_queued_message_notice(help_text, self._was_message_queued(update))
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup)

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        about_text = (
            "📖 About OneDrive Sharing Bot\n\n"
            "🎯 Purpose: Provide easy access to Sharing files stored in OneDrive\n"
            "🔧 Technology: Python + Telegram Bot API + Microsoft Graph API\n"
            "📊 Features:\n"
            "• Fast file browsing with local indexing\n"
            "• Direct file downloads\n"
            "• Real-time notifications for subscribers\n"
            "• Admin management tools\n\n"
            "🔗 Powered by Microsoft Graph API"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(about_text, reply_markup=reply_markup)

    async def privacy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /privacy command"""
        privacy_text = (
            "🔒 Privacy Policy\n\n"
            "📊 Data Collection:\n"
            "• User ID for bot functionality\n"
            "• File access logs for admin purposes\n"
            "• No personal messages are stored\n\n"
            "🛡️ Data Protection:\n"
            "• Files are accessed read-only from OneDrive\n"
            "• No files are stored on bot servers\n"
            "• User data is encrypted and secure\n\n"
            "🔄 Data Usage:\n"
            "• Only for providing bot services\n"
            "• No data sharing with third parties\n"
            "• Users can request data deletion anytime\n\n"
            "📧 Contact admin for privacy concerns"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(privacy_text, reply_markup=reply_markup)

    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback command"""
        feedback_text = (
            "📝 Feedback & Support\n\n"
            "Your feedback helps improve this bot!\n\n"
            "🐛 Found a bug?\n"
            "💡 Have a suggestion?\n"
            "❓ Need help with something?\n\n"
            "Click the button below to submit your feedback."
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Submit Feedback", callback_data="submit_feedback")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(feedback_text, reply_markup=reply_markup)

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command (admin only)"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Access denied. Admin only.")
            return

        keyboard = [
            [InlineKeyboardButton("🔄 Rebuild Index", callback_data="admin_rebuild")],
            [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🛑 Shutdown Bot", callback_data="admin_shutdown")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 Admin Panel\n\nSelect an option:",
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "browse_root":
            await self.show_folder_contents(query, "root")
        elif data == "refresh_index":
            await self.refresh_index(query)
        elif data == "main_menu":
            await self.show_main_menu(query)
        elif data == "show_help":
            await self.show_help_inline(query)
        elif data == "show_about":
            await self.show_about_inline(query)
        elif data == "show_privacy":
            await self.show_privacy_inline(query)
        elif data == "show_feedback":
            await self.show_feedback_inline(query)
        elif data == "submit_feedback":
            await self.start_feedback_collection(query)
        elif data == "show_admin":
            await self.show_admin_inline(query)
        elif data == "noop":
            pass  # Do nothing for page indicator
        elif data.startswith("page_"):
            page_info = self.resolve_callback_data(data)
            path, page_str = page_info.split(":", 1)
            page = int(page_str)
            await self.show_folder_contents(query, path, page)
        elif data.startswith("folder_"):
            path = self.resolve_callback_data(data)
            await self.show_folder_contents(query, path)
        elif data.startswith("file_"):
            file_info = self.resolve_callback_data(data)
            await self.handle_file_download(query, file_info)
        elif data.startswith("download_"):
            download_info = self.resolve_callback_data(data)
            await self.download_and_send_file(query, download_info)
        elif data.startswith("back_"):
            path = self.resolve_callback_data(data)
            await self.show_folder_contents(query, path)
        elif data.startswith("admin_"):
            await self.handle_admin_action(query, data[6:])

    async def show_folder_contents(self, query, path: str, page: int = 0):
        """Show folder contents with navigation buttons and pagination"""
        contents = self.get_folder_contents(path)
        
        keyboard = []
        folders = []
        files = []
        
        if contents:
            folders = [item for item in contents if item['type'] == 'folder']
            files = [item for item in contents if item['type'] == 'file']
        
        # Pagination settings
        items_per_page = 8
        total_folders = len(folders)
        total_files = len(files)
        total_items = total_folders + total_files
        
        # Calculate pagination for combined items
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        # Combine folders and files for pagination
        all_items = folders + files
        page_items = all_items[start_idx:end_idx]
        
        # Add items for current page
        for item in page_items:
            if item['type'] == 'folder':
                folder_path = f"{path}/{item['name']}" if path != "root" else item['name']
                callback_data = self.create_callback_data("folder", folder_path)
                keyboard.append([InlineKeyboardButton(
                    f"📁 {item['name']}", 
                    callback_data=callback_data
                )])
            else:  # file
                size_mb = item.get('size', 0) / (1024 * 1024) if item.get('size', 0) > 0 else 0
                file_id = item.get('id', item.get('path', item.get('name', f'file_{len(keyboard)}')))
                file_info = f"{file_id}_{item.get('name', 'unknown')}"
                callback_data = self.create_callback_data("file", file_info)
                keyboard.append([InlineKeyboardButton(
                    f"📄 {item['name']} ({size_mb:.1f}MB)", 
                    callback_data=callback_data
                )])
        
        # Add pagination buttons if needed
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 0
        if total_pages > 1:
            pagination_row = []
            
            # Previous page button
            if page > 0:
                prev_callback = self.create_callback_data("page", f"{path}:{page-1}")
                pagination_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=prev_callback))
            
            # Page indicator
            pagination_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
            
            # Next page button
            if page < total_pages - 1:
                next_callback = self.create_callback_data("page", f"{path}:{page+1}")
                pagination_row.append(InlineKeyboardButton("Next ➡️", callback_data=next_callback))
            
            keyboard.append(pagination_row)
        
        
        # Add navigation buttons at the bottom in three columns
        bottom_row = []
        
        # Back button (left column) - always show back button
        if path != "root":
            parent_path = "/".join(path.split("/")[:-1]) if "/" in path else "root"
            back_callback = self.create_callback_data("back", parent_path)
            bottom_row.append(InlineKeyboardButton("⬅️ Back", callback_data=back_callback))
        else:
            bottom_row.append(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
        
        # Main Menu button (center column)
        bottom_row.append(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        # Refresh button (right column) - only for admin
        if hasattr(query, 'from_user') and query.from_user.id == self.admin_id:
            bottom_row.append(InlineKeyboardButton("🔄 Refresh", callback_data="refresh_index"))
        
        # Add the bottom row to keyboard
        keyboard.append(bottom_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        folder_name = path.split("/")[-1] if path != "root" else "Sharing"
        
        # Build status text
        if total_items == 0:
            status_text = "📁 Empty folder"
        else:
            if page > 0:
                showing_start = start_idx + 1
                showing_end = min(end_idx, total_items)
                status_text = f"📊 Showing {showing_start}-{showing_end} of {total_items} items"
                if total_folders > 0 and total_files > 0:
                    status_text += f" ({total_folders} folders, {total_files} files)"
            else:
                status_text = f"📊 {total_folders} folders, {total_files} files"
        
        text = f"📁 Current folder: {folder_name}\n\n{status_text}"
        
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_file_download(self, query, file_info: str):
        """Handle file download confirmation"""
        parts = file_info.split("_", 1)
        if len(parts) != 2:
            await query.edit_message_text("❌ Error: Invalid file information.")
            return
            
        file_id, file_name = parts
        
        # Find file info to check size and get folder path
        file_details = None
        current_folder_path = "root"
        
        for path, items in self.indexer.file_index.items():
            if isinstance(items, list):
                for item in items:
                    if item.get('id') == file_id:
                        file_details = item
                        current_folder_path = path
                        break
                if file_details:
                    break
        
        if not file_details:
            await query.edit_message_text("❌ Error: File not found in index.")
            return
        
        # Check file size (Telegram limit is 50MB)
        file_size_mb = file_details.get('size', 0) / (1024 * 1024)
        if file_size_mb > 50:
            await self.handle_large_file_download(query, file_details, file_name, current_folder_path, file_size_mb)
            return
        
        # Store folder path for return navigation
        download_callback = self.create_callback_data("download", f"{file_id}|{current_folder_path}")
        back_callback = self.create_callback_data("folder", current_folder_path)
        
        keyboard = [
            [InlineKeyboardButton("⬇️ Download", callback_data=download_callback)],
            [InlineKeyboardButton("⬅️ Back to Folder", callback_data=back_callback)],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📄 File: {file_name}\n"
            f"📊 Size: {file_size_mb:.1f}MB\n\n"
            f"⬇️ Do you want to download this file?",
            reply_markup=reply_markup
        )

    async def download_and_send_file(self, query, download_info: str):
        """Download and send file to user, or provide OneDrive link for large files"""
        try:
            # Parse download info: file_id|folder_path
            parts = download_info.split('|', 1)
            if len(parts) != 2:
                await query.edit_message_text("❌ Error: Invalid download information.")
                return
            
            file_id, current_folder_path = parts
            
            # Find file details from the index
            file_details = None
            file_name = "Unknown File"
            
            for path, items in self.indexer.file_index.items():
                if isinstance(items, list):
                    for item in items:
                        if item.get('id') == file_id:
                            file_details = item
                            file_name = item.get('name', 'Unknown File')
                            break
                    if file_details:
                        break
            
            if not file_details:
                await query.edit_message_text("❌ Error: File not found in index.")
                return
            
            # Check file size (Telegram limit is 50MB)
            file_size = file_details.get('size', 0)
            file_size_mb = file_size / (1024 * 1024)
            

            
            # Handle large files (>50MB) with OneDrive link
            if file_size_mb > 50:
                await self.handle_large_file_download(query, file_details, file_name, current_folder_path, file_size_mb)
                return
            
            # Send downloading message for small files
            await query.edit_message_text(f"⬇️ Downloading {file_name}...\n📊 Size: {file_size_mb:.1f}MB")
            
            # Download the file asynchronously
            file_content = await self.download_file_async(file_id)
            
            if file_content:
                # Send the file
                from io import BytesIO
                file_obj = BytesIO(file_content)
                file_obj.name = file_name
                
                await query.message.reply_document(
                    document=file_obj,
                    filename=file_name,
                    caption=f"📄 {file_name}\n📊 Size: {file_size_mb:.1f}MB"
                )
                
                # Create navigation buttons
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ File sent successfully!\n\n📄 {file_name}\n📊 Size: {file_size_mb:.1f}MB",
                    reply_markup=reply_markup
                )
                

                    
            else:
                # Download failed - provide OneDrive link as fallback
                download_url = self.get_onedrive_download_url(file_id)
                
                if download_url:
                    keyboard = [
                        [InlineKeyboardButton("🔗 Download from OneDrive", url=download_url)],
                        [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"❌ Download failed through Telegram\n\n"
                        f"📄 {file_name}\n"
                        f"📊 Size: {file_size_mb:.1f}MB\n\n"
                        f"🔗 Use the OneDrive link below to download:",
                        reply_markup=reply_markup
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"❌ Download failed\n\n"
                        f"📄 {file_name}\n"
                        f"📊 Size: {file_size_mb:.1f}MB\n\n"
                        f"Unable to download file or generate OneDrive link.",
                        reply_markup=reply_markup
                    )
                

                    
        except Exception as e:
            logger.error(f"Error in download_and_send_file: {e}")
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path if 'current_folder_path' in locals() else "root"))],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ An error occurred during download",
                reply_markup=reply_markup
            )

    async def handle_large_file_download(self, query, file_details, file_name, current_folder_path, file_size_mb):
        """Handle large file download by providing OneDrive direct link"""
        try:
            # Get OneDrive download URL
            download_url = self.get_onedrive_download_url(file_details['id'])
            
            if download_url:
                keyboard = [
                    [InlineKeyboardButton("🔗 Download from OneDrive", url=download_url)],
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"📄 **{file_name}**\n"
                    f"📊 Size: {file_size_mb:.1f}MB\n\n"
                    f"⚠️ This file exceeds Telegram's 50MB limit.\n"
                    f"🔗 Use the link below to download directly from OneDrive:\n\n"
                    f"💡 The download will start automatically when you click the link.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                

                    
            else:
                # Fallback if download URL cannot be generated
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"❌ File too large for Telegram\n\n"
                    f"📄 {file_name}\n"
                    f"📊 Size: {file_size_mb:.1f}MB\n\n"
                    f"⚠️ Telegram has a 50MB limit and download link is unavailable.",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error handling large file download: {e}")
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ Error handling large file\n\n📄 {file_name}",
                reply_markup=reply_markup
            )

    def get_onedrive_download_url(self, file_id: str) -> Optional[str]:
        """Get OneDrive direct download URL for a file"""
        try:
            token = self.indexer.get_access_token()
            if not token:
                return None
                
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.indexer.target_user_id}/drive/items/{file_id}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                # Get the @microsoft.graph.downloadUrl which provides direct download
                download_url = file_data.get('@microsoft.graph.downloadUrl')
                if download_url:
                    return download_url
                    
                # Alternative: get sharing link
                share_url = f"https://graph.microsoft.com/v1.0/users/{self.indexer.target_user_id}/drive/items/{file_id}/createLink"
                share_payload = {
                    "type": "view",
                    "scope": "anonymous"
                }
                share_response = requests.post(share_url, headers=headers, json=share_payload)
                if share_response.status_code == 201:
                    share_data = share_response.json()
                    return share_data.get('link', {}).get('webUrl')
                    
        except Exception as e:
            logger.error(f"Error getting OneDrive download URL: {e}")
            
        return None

    async def refresh_index(self, query):
        """Refresh file index (admin only) with async progress updates"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied. Admin only.", show_alert=True)
            return
            
        # Check if indexing is already in progress
        if hasattr(self.indexer, 'is_indexing') and self.indexer.is_indexing:
            await query.answer("⏳ Indexing already in progress. Please wait...", show_alert=True)
            return
            
        initial_message = await query.edit_message_text("🔄 Starting file index refresh...\n\n📊 Progress: 0%\n📁 Initializing...")
        
        # Keep track of message for updates
        chat_id = query.message.chat_id
        message_id = initial_message.message_id
        
        # Progress callback to update the message
        last_update_time = datetime.now()
        
        async def progress_callback(current, total, current_path):
            nonlocal last_update_time
            
            # Throttle updates to avoid hitting rate limits (update every 2 seconds max)
            now = datetime.now()
            if (now - last_update_time).total_seconds() < 2:
                return
                
            last_update_time = now
            
            try:
                if total > 0:
                    progress_pct = min(100, int((current / total) * 100))
                else:
                    progress_pct = 0
                
                # Create progress bar
                filled = int(progress_pct / 10)
                bar = "█" * filled + "░" * (10 - filled)
                
                # Truncate path if too long
                display_path = current_path if len(current_path) <= 30 else f"...{current_path[-27:]}"
                
                progress_text = (
                    f"🔄 Refreshing file index...\n\n"
                    f"📊 Progress: {progress_pct}% {bar}\n"
                    f"📁 Current: {display_path}\n"
                    f"📈 Processed: {current}/{total} folders"
                )
                
                # Also send keep-alive ping to prevent Render shutdown
                if hasattr(self, 'send_keepalive_ping'):
                    asyncio.create_task(self.send_keepalive_ping())
                
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=progress_text
                )
            except Exception as e:
                logger.warning(f"Error updating progress message: {e}")
        
        try:
            # Start async indexing with progress updates
            success = await self.indexer.build_index_async(force_rebuild=True, progress_callback=progress_callback)
            
            if success:
                stats = self.indexer.get_stats()
                final_text = (
                    "✅ File index refreshed successfully!\n\n"
                    f"� **Index Statistics:**\n"
                    f"• Folders: {stats.get('total_folders', 0):,}\n"
                    f"• Files: {stats.get('total_files', 0):,}\n"
                    f"• Total size: {stats.get('total_size', 0) / (1024*1024*1024):.2f} GB\n\n"
                    f"�📝 Note: Index will be rebuilt automatically on next service restart."
                )
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=final_text
                )
                await asyncio.sleep(3)
                await self.show_folder_contents(query, "root")
            else:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ Error refreshing file index. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error during async index refresh: {e}")
            try:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ Error refreshing file index: {str(e)}"
                )
            except:
                pass

    async def handle_admin_action(self, query, action: str):
        """Handle admin actions with async indexing support"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        if action == "rebuild":
            # Check if indexing is already in progress
            if hasattr(self.indexer, 'is_indexing') and self.indexer.is_indexing:
                await query.answer("⏳ Indexing already in progress. Please wait...", show_alert=True)
                return
                
            initial_message = await query.edit_message_text("🔄 Starting index rebuild...\n\n📊 Progress: 0%\n📁 Initializing...")
            
            # Keep track of message for updates
            chat_id = query.message.chat_id
            message_id = initial_message.message_id
            
            # Progress callback to update the message
            last_update_time = datetime.now()
            
            async def progress_callback(current, total, current_path):
                nonlocal last_update_time
                
                # Throttle updates to avoid hitting rate limits
                now = datetime.now()
                if (now - last_update_time).total_seconds() < 2:
                    return
                    
                last_update_time = now
                
                try:
                    if total > 0:
                        progress_pct = min(100, int((current / total) * 100))
                    else:
                        progress_pct = 0
                    
                    # Create progress bar
                    filled = int(progress_pct / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    
                    # Truncate path if too long
                    display_path = current_path if len(current_path) <= 30 else f"...{current_path[-27:]}"
                    
                    progress_text = (
                        f"🔄 Rebuilding file index...\n\n"
                        f"📊 Progress: {progress_pct}% {bar}\n"
                        f"📁 Current: {display_path}\n"
                        f"📈 Processed: {current}/{total} folders"
                    )
                    
                    # Send keep-alive ping to prevent Render shutdown
                    if hasattr(self, 'send_keepalive_ping'):
                        asyncio.create_task(self.send_keepalive_ping())
                    
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=progress_text
                    )
                except Exception as e:
                    logger.warning(f"Error updating rebuild progress message: {e}")
            
            try:
                # Start async indexing with progress updates
                success = await self.indexer.build_index_async(force_rebuild=True, progress_callback=progress_callback)
                
                keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if success:
                    stats = self.indexer.get_stats()
                    final_text = (
                        "✅ File index rebuilt successfully!\n\n"
                        f"📊 **Index Statistics:**\n"
                        f"• Folders: {stats.get('total_folders', 0):,}\n"
                        f"• Files: {stats.get('total_files', 0):,}\n"
                        f"• Total size: {stats.get('total_size', 0) / (1024*1024*1024):.2f} GB\n\n"
                        f"📝 Note: Changes are temporary and will reset on service restart."
                    )
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=final_text,
                        reply_markup=reply_markup
                    )
                else:
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="❌ Error rebuilding file index.",
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Error during async index rebuild: {e}")
                keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"❌ Error rebuilding file index: {str(e)}",
                        reply_markup=reply_markup
                    )
                except:
                    pass
                
        elif action == "users":
            # Enhanced user management with view and add options
            await self.show_user_management(query)
            
        elif action == "view_users":
            user_count = len(self.unlimited_users)
            if user_count == 0:
                user_list_text = "👥 No users registered yet."
            else:
                # Get user details from database if available
                users_info = []
                if db_manager.enabled:
                    all_users = db_manager.get_all_users_data()
                    for user_data in all_users:
                        users_info.append(f"• {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', 'none')}) - ID: {user_data.get('user_id')}")
                else:
                    # Fallback to just showing user IDs
                    for user_id in self.unlimited_users:
                        users_info.append(f"• User ID: {user_id}")
                
                user_list_text = f"👥 Total users: {user_count}\n\n" + "\n".join(users_info[:20])
                if len(users_info) > 20:
                    user_list_text += f"\n\n... and {len(users_info) - 20} more users"
            
            keyboard = [
                [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(user_list_text, reply_markup=reply_markup)
            
        elif action == "add_user":
            await self.start_add_user_collection(query)
            
        elif action == "mass_message":
            await self.start_mass_message_collection(query)
            
        elif action == "feedback":
            await self.show_admin_feedback(query)
            
        elif action == "stats":
            try:
                stats = self.indexer.get_stats()
                timestamp_age = "Never"
                if stats['last_updated']:
                    age_minutes = (datetime.now() - stats['last_updated']).total_seconds() / 60
                    if age_minutes < 60:
                        timestamp_age = f"{age_minutes:.1f} minutes ago"
                    else:
                        timestamp_age = f"{age_minutes/60:.1f} hours ago"
                
                stats_text = (
                    f"📊 Bot Statistics\n\n"
                    f"👥 Unlimited users: {len(self.unlimited_users)}\n"
                    f"📁 Total folders: {stats['total_folders']}\n"
                    f"📄 Total files: {stats['total_files']}\n"
                    f"💾 Total size: {stats['total_size'] / (1024*1024*1024):.2f} GB\n"
                    f"🗂️ Indexed paths: {stats['total_paths']}\n"
                    f"🕐 Last index update: {timestamp_age}"
                )
            except Exception as e:
                stats_text = f"📊 Bot Statistics\n\n❌ Error loading stats: {e}"
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                       [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(stats_text, reply_markup=reply_markup)
            
        elif action == "shutdown":
            await query.edit_message_text("🛑 Shutting down bot...")
            await self.notify_subscribers("🔴 Bot Ended Operations")
            # Stop the application - this will trigger the shutdown process
            await self.application.stop()
            await self.application.shutdown()
            import os
            os._exit(0)  # Force exit since we're in a callback

    async def show_main_menu(self, query):
        """Show the main menu"""
        keyboard = [
            [InlineKeyboardButton("📁 Browse Files", callback_data="browse_root")]
        ]
        
        # Add refresh index button only for admin
        if query.from_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("🔄 Refresh Index", callback_data="refresh_index")])
            
        # Add information and admin buttons
        keyboard.extend([
            [InlineKeyboardButton("❓ Help", callback_data="show_help"),
             InlineKeyboardButton("ℹ️ About", callback_data="show_about")],
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy"),
             InlineKeyboardButton("📝 Feedback", callback_data="show_feedback")]
        ])
        
        if query.from_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🎓 OneDrive Sharing Bot\n\n"
            "📂 Browse and download sharing files\n"
        )
        
        if query.from_user.id == self.admin_id:
            welcome_text += "⚙️ Admin controls available\n"
            
        welcome_text += "\nSelect an option below:"
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - show bot menu"""
        keyboard = [
            [InlineKeyboardButton("📁 Browse Files", callback_data="browse_root")]
        ]
        
        # Add refresh index button only for admin
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("🔄 Refresh Index", callback_data="refresh_index")])
            
        # Add additional menu options
        keyboard.extend([
            [InlineKeyboardButton("❓ Help", callback_data="show_help"),
             InlineKeyboardButton("ℹ️ About", callback_data="show_about")],
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy"),
             InlineKeyboardButton("📝 Feedback", callback_data="show_feedback")]
        ])
        
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = (
            "📋 OneDrive Sharing Bot Menu\n\n"
            "Choose an option below:"
        )
        
        await update.message.reply_text(menu_text, reply_markup=reply_markup)

    async def show_help_inline(self, query):
        """Show help as inline message"""
        help_text = (
            "🤖 OneDrive Sharing Bot Help\n\n"
            "📋 Available Commands:\n"
            "• /start - Start the bot and show main menu\n"
            "• /menu - Show bot menu with options\n"
            "• /help - Show this help message\n"
            "• /about - About this bot\n"
            "• /privacy - Privacy policy\n"
            "• /feedback - Submit feedback or report issues\n"
            "• /admin - Admin panel (admin only)\n\n"
            "🗂️ Navigation & Usage:\n"
            "• 📁 Browse Files - Explore sharing folders\n"
            "• ⬅️ Back - Navigate to parent folder\n"
            "• 🏠 Main Menu - Return to start screen\n"
            "• 🔄 Refresh - Update file index (admin only)\n\n"
            "⚡ Performance: Files are cached for speed"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup)

    async def show_about_inline(self, query):
        """Show about as inline message"""
        about_text = (
            "📖 About OneDrive Sharing Bot\n\n"
            "🎯 Purpose: Easy access to Sharing files\n"
            "🔧 Technology: Python + Telegram + MS Graph + AI\n\n"
            "📊 Features:\n"
            "• Fast file browsing with local indexing\n"
            "• AI-powered natural language search\n"
            "• Direct file downloads to chat\n"
            "• Smart navigation with back buttons\n"
            "• Admin management tools\n"
            "• Secure read-only access\n\n"
            "🔗 Powered by Microsoft Graph API & Phi AI"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(about_text, reply_markup=reply_markup)

    async def show_privacy_inline(self, query):
        """Show privacy as inline message"""
        privacy_text = (
            "🔒 Privacy Policy\n\n"
            "📊 Data Collection:\n"
            "• User ID for bot functionality only\n"
            "• File access logs for admin purposes\n"
            "• No personal messages stored\n\n"
            "🛡️ Data Protection:\n"
            "• Read-only OneDrive access\n"
            "• No files stored on bot servers\n"
            "• Secure authentication\n\n"
            "🔄 Data Usage:\n"
            "• Only for providing bot services\n"
            "• No third-party data sharing\n"
            "• Data deletion available on request"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(privacy_text, reply_markup=reply_markup)

    async def show_admin_inline(self, query):
        """Show admin panel as inline message"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
            
        keyboard = [
            [InlineKeyboardButton("🔄 Rebuild Index", callback_data="admin_rebuild")],
            [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Send Mass Message", callback_data="admin_mass_message")],
            [InlineKeyboardButton("📝 View Feedback", callback_data="admin_feedback")],
            [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🛑 Shutdown Bot", callback_data="admin_shutdown")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 Admin Panel\n\nSelect an option:",
            reply_markup=reply_markup
        )

    async def show_feedback_inline(self, query):
        """Show feedback options as inline message"""
        feedback_text = (
            "📝 Feedback & Support\n\n"
            "Your feedback helps improve this bot!\n\n"
            "🐛 Found a bug?\n"
            "💡 Have a suggestion?\n"
            "❓ Need help with something?\n\n"
            "Click the button below to submit your feedback."
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Submit Feedback", callback_data="submit_feedback")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(feedback_text, reply_markup=reply_markup)

    async def start_feedback_collection(self, query):
        """Start feedback collection process"""
        user_id = query.from_user.id
        self.awaiting_feedback.add(user_id)
        
        feedback_text = (
            "📝 Submit Your Feedback\n\n"
            "Please type your feedback message and send it.\n"
            "You can report bugs, suggest improvements, or ask questions.\n\n"
            "⚠️ Note: Your next message will be recorded as feedback."
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="show_feedback")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(feedback_text, reply_markup=reply_markup)

    async def start_mass_message_collection(self, query):
        """Start mass message collection process"""
        user_id = query.from_user.id
        if user_id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
            
        self.awaiting_mass_message.add(user_id)
        
        mass_message_text = (
            "📢 Send Mass Message\n\n"
            f"This will send a message to all {len(self.unlimited_users)} bot users.\n\n"
            "Please type the message you want to send to all users.\n\n"
            "⚠️ Note: Your next message will be sent to all users."
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="show_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(mass_message_text, reply_markup=reply_markup)

    async def send_mass_message(self, message_text: str, admin_id: int):
        """Send mass message to all users"""
        total_users = len(self.unlimited_users)
        success_count = 0
        failed_count = 0
        
        logger.info(f"Starting mass message send to {total_users} users")
        
        for user_id in self.unlimited_users.copy():  # Use copy to avoid modification during iteration
            try:
                await self.application.bot.send_message(
                    chat_id=user_id, 
                    text=f"📢 Message from Admin:\n\n{message_text}"
                )
                success_count += 1
                logger.debug(f"Mass message sent successfully to user {user_id}")
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send mass message to user {user_id}: {e}")
                
                # Remove user if they blocked the bot or account was deleted
                if "bot was blocked" in str(e).lower() or "user is deactivated" in str(e).lower():
                    logger.info(f"Removing inactive user {user_id} from user list")
                    self.unlimited_users.discard(user_id)
                    
                    # Remove from database if available
                    if db_manager.enabled:
                        db_manager.remove_user(user_id)
                    else:
                        self.save_data()  # Fallback to file
        
        # Send summary to admin
        summary_text = (
            f"📊 Mass Message Results\n\n"
            f"✅ Successfully sent: {success_count}\n"
            f"❌ Failed to send: {failed_count}\n"
            f"📨 Total users: {total_users}\n\n"
            f"💬 Message sent:\n{message_text}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=admin_id,
                text=summary_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to send mass message summary to admin: {e}")

    async def show_user_management(self, query):
        """Show user management options"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
            
        user_count = len(self.unlimited_users)
        management_text = (
            f"👥 User Management\n\n"
            f"Current registered users: {user_count}\n\n"
            "Choose an action:"
        )
        
        keyboard = [
            [InlineKeyboardButton("👀 View All Users", callback_data="admin_view_users")],
            [InlineKeyboardButton("➕ Add User Manually", callback_data="admin_add_user")],
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(management_text, reply_markup=reply_markup)

    async def start_add_user_collection(self, query):
        """Start the process of manually adding a user"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
            
        user_id = query.from_user.id
        self.awaiting_add_user.add(user_id)
        
        add_user_text = (
            "➕ Add User Manually\n\n"
            "Please send the Telegram User ID of the user you want to add.\n\n"
            "💡 How to get User ID:\n"
            "• Ask the user to send any message to this bot\n"
            "• Use @userinfobot to get their ID\n"
            "• Check the logs when they interact with the bot\n\n"
            "Send the numeric User ID now:"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_users")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(add_user_text, reply_markup=reply_markup)

    async def add_user_manually(self, user_id_to_add: int, admin_id: int):
        """Manually add a user to the bot"""
        try:
            # Check if user is already registered
            if user_id_to_add in self.unlimited_users:
                return f"❌ User {user_id_to_add} is already registered."
            
            # Add user to the set
            self.unlimited_users.add(user_id_to_add)
            
            # Try to get user info from Telegram
            try:
                user_info = await self.application.bot.get_chat(user_id_to_add)
                first_name = user_info.first_name or "Unknown"
                username = user_info.username or None
                
                # Add to database if available
                if db_manager.enabled:
                    if db_manager.add_user(
                        user_id=user_id_to_add,
                        username=username,
                        first_name=first_name,
                        last_name=user_info.last_name
                    ):
                        logger.info(f"User {user_id_to_add} manually added to database by admin {admin_id}")
                    else:
                        logger.warning(f"Failed to add user {user_id_to_add} to database")
                else:
                    # Save to file as fallback
                    self.save_unlimited_users()
                
                # Try to send welcome message to the new user
                try:
                    welcome_text = (
                        f"🎉 Welcome to the OneDrive Bot!\n\n"
                        f"You have been manually added by an administrator.\n"
                        f"Use /start to begin exploring files."
                    )
                    await self.application.bot.send_message(
                        chat_id=user_id_to_add, 
                        text=welcome_text
                    )
                    welcome_sent = True
                except Exception as e:
                    logger.warning(f"Could not send welcome message to user {user_id_to_add}: {e}")
                    welcome_sent = False
                
                success_msg = (
                    f"✅ User successfully added!\n\n"
                    f"👤 Name: {first_name}\n"
                    f"🆔 User ID: {user_id_to_add}\n"
                    f"👤 Username: @{username if username else 'none'}\n"
                    f"📧 Welcome message: {'✅ Sent' if welcome_sent else '❌ Failed'}"
                )
                
            except Exception as e:
                # User info not accessible, but still add them
                if db_manager.enabled:
                    if db_manager.add_user(
                        user_id=user_id_to_add,
                        username=None,
                        first_name="Unknown",
                        last_name=None
                    ):
                        logger.info(f"User {user_id_to_add} manually added to database (minimal info) by admin {admin_id}")
                else:
                    # Save to file as fallback
                    self.save_unlimited_users()
                
                success_msg = (
                    f"✅ User added with ID: {user_id_to_add}\n\n"
                    f"⚠️ Could not retrieve user details.\n"
                    f"The user can still use the bot."
                )
            
            logger.info(f"Admin {admin_id} manually added user {user_id_to_add}")
            return success_msg
            
        except Exception as e:
            logger.error(f"Error manually adding user {user_id_to_add}: {e}")
            return f"❌ Error adding user: {str(e)}"

    async def handle_feedback_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feedback messages and mass messages from users"""
        user_id = update.effective_user.id
        
        # Check if this is a mass message from admin
        if user_id in self.awaiting_mass_message:
            # Remove admin from waiting list
            self.awaiting_mass_message.discard(user_id)
            
            # Get the message text
            message_text = update.message.text
            
            # Send confirmation and start mass message sending
            await update.message.reply_text(
                f"📢 Sending mass message to {len(self.unlimited_users)} users...\n\n"
                "Please wait for the completion summary."
            )
            
            # Send mass message (this will run in background)
            await self.send_mass_message(message_text, user_id)
            return
        
        # Check if admin is adding a user manually
        if user_id in self.awaiting_add_user:
            # Remove admin from waiting list
            self.awaiting_add_user.discard(user_id)
            
            # Get the user ID text
            user_id_text = update.message.text.strip()
            
            # Validate that it's a numeric user ID
            try:
                user_id_to_add = int(user_id_text)
                
                # Add the user
                result_message = await self.add_user_manually(user_id_to_add, user_id)
                
                # Send result with back button
                keyboard = [
                    [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                    [InlineKeyboardButton("🔙 Admin Panel", callback_data="show_admin")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    result_message,
                    reply_markup=reply_markup
                )
                
            except ValueError:
                # Invalid user ID format
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data="admin_add_user")],
                    [InlineKeyboardButton("👥 User Management", callback_data="admin_users")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"❌ Invalid User ID format: '{user_id_text}'\n\n"
                    "Please send a valid numeric Telegram User ID.\n"
                    "Example: 123456789",
                    reply_markup=reply_markup
                )
            return
        
        # Handle regular feedback
        if user_id not in self.awaiting_feedback:
            return  # Not waiting for feedback from this user
        
        # Remove user from waiting list
        self.awaiting_feedback.discard(user_id)
        
        # Get feedback text
        feedback_text = update.message.text
        user_info = update.effective_user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save feedback to database or file
        try:
            if db_manager.enabled:
                # Save to database
                if db_manager.add_feedback(user_id, feedback_text):
                    logger.info(f"Feedback saved to database from user {user_id}: {feedback_text[:100]}...")
                else:
                    logger.error("Failed to save feedback to database")
                    raise Exception("Database save failed")
            else:
                # Fallback to file
                feedback_entry = (
                    f"[{timestamp}] User: {user_info.first_name} "
                    f"({user_info.username or 'No username'}) ID: {user_id}\n"
                    f"Feedback: {feedback_text}\n"
                    f"{'='*50}\n\n"
                )
                
                with open('feedback_log.txt', 'a', encoding='utf-8') as f:
                    f.write(feedback_entry)
                    
                logger.info(f"Feedback saved to file from user {user_id}: {feedback_text[:100]}...")
            
            # Send confirmation to user
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Thank you for your feedback!\n\n"
                "Your message has been recorded and will be reviewed by the admin.\n"
                "We appreciate your input to help improve the bot!",
                reply_markup=reply_markup
            )
            
            # Notify admin about new feedback (if admin is different from user)
            if user_id != self.admin_id and self.admin_id:
                try:
                    admin_notification = (
                        f"📝 New Feedback Received\n\n"
                        f"👤 From: {user_info.first_name} ({user_info.username or 'No username'})\n"
                        f"🆔 User ID: {user_id}\n"
                        f"🕐 Time: {timestamp}\n\n"
                        f"💬 Message: {feedback_text}"
                    )
                    await context.bot.send_message(chat_id=self.admin_id, text=admin_notification)
                except Exception as e:
                    logger.error(f"Error notifying admin about feedback: {e}")
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            
            # Send error message to user
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ Error saving your feedback. Please try again later.\n"
                "You can also contact the admin directly.",
                reply_markup=reply_markup
            )

    async def show_admin_feedback(self, query):
        """Show recent feedback to admin"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
            
        try:
            feedback_text = "📝 Recent Feedback\n\n"
            
            if db_manager.enabled:
                # Get feedback from database
                feedback_list = db_manager.get_recent_feedback(limit=10)
                if feedback_list:
                    for i, feedback in enumerate(feedback_list, 1):
                        user_id = feedback.get('user_id', 'Unknown')
                        message = feedback.get('message', 'No message')
                        timestamp = feedback.get('timestamp', 'Unknown time')
                        
                        # Truncate long messages
                        if len(message) > 100:
                            message = message[:100] + "..."
                        
                        feedback_text += f"{i}. ID: {user_id}\n📅 {timestamp}\n💬 {message}\n\n"
                else:
                    feedback_text += "No feedback found in database."
            else:
                # Fallback to reading from file
                import os
                if os.path.exists('feedback_log.txt'):
                    with open('feedback_log.txt', 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            # Get last 1000 characters to show recent feedback
                            recent_content = content[-1000:] if len(content) > 1000 else content
                            feedback_text += f"Recent entries:\n\n{recent_content}"
                        else:
                            feedback_text += "No feedback found in file."
                else:
                    feedback_text += "No feedback file found."
            
            # Limit message length for Telegram
            if len(feedback_text) > 4000:
                feedback_text = feedback_text[:4000] + "\n\n... (truncated)"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(feedback_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing admin feedback: {e}")
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Error loading feedback. Please try again later.",
                reply_markup=reply_markup
            )

    # ...existing code...

    def run(self):
        """Run the bot"""
        # Initialize file index (load cached or build if necessary)
        logger.info("Initializing file index...")
        try:
            if not self.indexer.initialize_index():
                logger.error("Failed to initialize file index")
                return
                
            stats = self.indexer.get_stats()
            logger.info(f"Index ready: {stats['total_folders']} folders, {stats['total_files']} files")
        except Exception as e:
            logger.error(f"Error initializing file index: {e}")
            return
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        self.application.add_handler(CommandHandler("privacy", self.privacy_command))
        self.application.add_handler(CommandHandler("feedback", self.feedback_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_feedback_message))
        
        # Start polling
        logger.info("Starting bot...")
        
        # Run bot with proper python-telegram-bot 20.x API
        try:
            # Set startup time for pending message detection
            from datetime import datetime, timezone
            self.startup_time = datetime.now(timezone.utc)
            
            # Send startup notification on first run
            async def post_init(application):
                """Post initialization hook to send startup notification"""
                try:
                    await self.notify_subscribers("🟢 Bot Started Operations")
                except Exception as e:
                    logger.error(f"Error sending startup notification: {e}")
            
            # Add post init hook
            self.application.post_init = post_init
            
            # Run polling - this handles all the async setup and cleanup automatically
            self.application.run_polling(
                drop_pending_updates=False,
                allowed_updates=['message', 'callback_query'],
                close_loop=False
            )
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by KeyboardInterrupt")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            logger.info("Bot shutdown complete")

if __name__ == "__main__":
    bot = OneDriveBot()
    bot.run()
