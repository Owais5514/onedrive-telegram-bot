import os
import json
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from indexer import OneDriveIndexer

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
        
        # File paths
        self.users_file = 'unlimited_users.json'
        self.feedback_file = 'feedback_log.txt'
        
        # Cache
        self.unlimited_users = set()
        
        # Feedback collection state
        self.awaiting_feedback = set()  # Track users who are providing feedback
        
        # Git integration for feedback persistence
        self.git_enabled = GIT_AVAILABLE and git_manager is not None
        if self.git_enabled:
            logger.info("Git integration enabled for feedback persistence")
        else:
            logger.info("Git integration not available for feedback")
        
        # Shutdown flag
        self.shutdown_requested = False
        
        # Track bot startup time for pending message handling
        self.startup_time = None
        
        # Load data
        self.load_data()

    def load_data(self):
        """Load cached data from files"""
        try:
            # Load feedback from Git if available (GitHub Actions environment)
            if self.git_enabled and git_manager.is_github_actions:
                logger.info("GitHub Actions environment detected, checking for feedback from Git...")
                if git_manager.load_feedback_from_branch([self.feedback_file]):
                    logger.info("Feedback file loaded from Git branch")
            
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    self.unlimited_users = set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def save_data(self):
        """Save data to files"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(list(self.unlimited_users), f)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def get_folder_contents(self, path: str = 'root') -> List[Dict]:
        """Get folder contents from indexer"""
        return self.indexer.get_folder_contents(path)

    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from OneDrive using indexer's token"""
        token = self.indexer.get_access_token()
        if not token:
            return None
            
        try:
            import requests
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://graph.microsoft.com/v1.0/users/{self.indexer.target_user_id}/drive/items/{file_id}/content"
            response = requests.get(url, headers=headers)
            
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

    async def show_folder_contents(self, query, path: str):
        """Show folder contents with navigation buttons"""
        contents = self.get_folder_contents(path)
        
        if not contents:
            await query.edit_message_text("📁 Empty folder or error loading contents.")
            return
        
        keyboard = []
        
        # Add folder and file buttons first
        folders = [item for item in contents if item['type'] == 'folder']
        files = [item for item in contents if item['type'] == 'file']
        
        # Add folders first
        for folder in folders[:10]:  # Limit to prevent message too long
            folder_path = f"{path}/{folder['name']}" if path != "root" else folder['name']
            callback_data = self.create_callback_data("folder", folder_path)
            
            keyboard.append([InlineKeyboardButton(
                f"📁 {folder['name']}", 
                callback_data=callback_data
            )])
        
        # Add files
        for file in files[:10]:  # Limit to prevent message too long
            size_mb = file.get('size', 0) / (1024 * 1024) if file.get('size', 0) > 0 else 0
            # Use path or name as identifier, fallback to index if neither available
            file_id = file.get('id', file.get('path', file.get('name', f'file_{len(keyboard)}')))
            file_info = f"{file_id}_{file.get('name', 'unknown')}"
            callback_data = self.create_callback_data("file", file_info)
            
            keyboard.append([InlineKeyboardButton(
                f"📄 {file['name']} ({size_mb:.1f}MB)", 
                callback_data=callback_data
            )])
        
        # Add navigation buttons at the bottom in three columns
        bottom_row = []
        
        # Back button (left column)
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
        text = f"📁 Current folder: {folder_name}\n\n📊 {len(folders)} folders, {len(files)} files"
        
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
            await query.edit_message_text(f"⬇️ Downloading {file_name}...")
            
            # Download the file
            file_content = self.download_file(file_id)
            
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
        """Refresh file index (admin only)"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied. Admin only.", show_alert=True)
            return
            
        await query.edit_message_text("🔄 Refreshing file index, please wait...")
        
        if self.indexer.build_index(force_rebuild=True):
            await query.edit_message_text("✅ File index refreshed successfully!")
            await asyncio.sleep(2)
            await self.show_folder_contents(query, "root")
        else:
            await query.edit_message_text("❌ Error refreshing file index. Please try again later.")

    async def handle_admin_action(self, query, action: str):
        """Handle admin actions"""
        if query.from_user.id != self.admin_id:
            await query.answer("❌ Access denied.", show_alert=True)
            return
        
        if action == "rebuild":
            await query.edit_message_text("🔄 Rebuilding file index...")
            if self.indexer.build_index(force_rebuild=True):
                keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("✅ File index rebuilt successfully!", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Error rebuilding file index.", reply_markup=reply_markup)
                
        elif action == "users":
            user_count = len(self.unlimited_users)
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="show_admin")],
                       [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"👥 Unlimited users: {user_count}", reply_markup=reply_markup)
            
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
            # Set shutdown flag and stop application
            self.shutdown_requested = True
            await self.application.stop()
            await self.application.shutdown()

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

    async def handle_feedback_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feedback messages from users"""
        user_id = update.effective_user.id
        
        if user_id not in self.awaiting_feedback:
            return  # Not waiting for feedback from this user
        
        # Remove user from waiting list
        self.awaiting_feedback.discard(user_id)
        
        # Get feedback text
        feedback_text = update.message.text
        user_info = update.effective_user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save feedback to file
        try:
            feedback_entry = (
                f"[{timestamp}] User: {user_info.first_name} "
                f"({user_info.username or 'No username'}) ID: {user_id}\n"
                f"Feedback: {feedback_text}\n"
                f"{'='*50}\n\n"
            )
            
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(feedback_entry)
                
            logger.info(f"Feedback received from user {user_id}: {feedback_text[:100]}...")
            
            # Commit feedback to Git repository if in GitHub Actions
            if self.git_enabled and git_manager.is_github_actions:
                logger.info("Committing feedback to Git repository...")
                if await self._commit_feedback_to_git(user_info, feedback_text, timestamp):
                    logger.info("✅ Feedback committed to Git repository")
                else:
                    logger.warning("⚠️ Failed to commit feedback to Git repository")
            
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

    async def _commit_feedback_to_git(self, user_info, feedback_text, timestamp):
        """Commit feedback to Git repository in real-time"""
        try:
            if not self.git_enabled:
                return False
            
            # Configure Git for feedback commits
            if not git_manager.configure_git():
                logger.error("Failed to configure Git for feedback commit")
                return False
            
            # Create commit message with feedback summary
            sanitized_feedback = feedback_text.replace('\n', ' ').replace('\r', ' ')[:100]
            if len(feedback_text) > 100:
                sanitized_feedback += "..."
            
            commit_message = (
                f"Add user feedback - {timestamp}\n\n"
                f"From: {user_info.first_name} ({user_info.username or 'No username'})\n"
                f"User ID: {user_info.id}\n"
                f"Feedback: {sanitized_feedback}"
            )
            
            # Use Git integration to commit feedback files
            if git_manager.commit_feedback_files([self.feedback_file], commit_message):
                logger.info("Feedback successfully committed to Git")
                return True
            else:
                logger.warning("Git commit failed for feedback")
                return False
                
        except Exception as e:
            logger.error(f"Error committing feedback to Git: {e}")
            return False

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
        
        # Run bot with proper shutdown handling
        import signal
        import asyncio
        
        async def run_bot():
            """Run the bot with proper shutdown handling"""
            try:
                # Initialize application
                await self.application.initialize()
                await self.application.start()
                
                # Set startup time for pending message detection
                from datetime import datetime, timezone
                self.startup_time = datetime.now(timezone.utc)
                
                # Send startup notification
                await self.notify_subscribers("🟢 Bot Started Operations")
                
                # Start polling with pending updates handling
                # Process pending updates but limit to recent ones to avoid spam/flooding
                await self.application.updater.start_polling(
                    drop_pending_updates=False,
                    allowed_updates=['message', 'callback_query']
                )
                
                # Brief delay to allow pending messages to be processed
                await asyncio.sleep(2)
                
                # Keep running until shutdown is requested
                while not self.shutdown_requested:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error running bot: {e}")
            finally:
                # Clean shutdown
                try:
                    if hasattr(self.application, 'updater') and self.application.updater.running:
                        await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                    

                    
                    logger.info("Bot shut down successfully")
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
        
        # Run the bot
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            logger.info("Bot stopped by KeyboardInterrupt")
            self.shutdown_requested = True

if __name__ == "__main__":
    bot = OneDriveBot()
    bot.run()
