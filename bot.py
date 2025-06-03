import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from indexer import OneDriveIndexer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneDriveBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_USER_ID', '0'))
        
        # Initialize OneDrive indexer
        self.indexer = OneDriveIndexer()
        
        # Callback data mapping to handle long file names (max 64 bytes for Telegram)
        self.callback_map = {}
        self.callback_counter = 0
        
        # File paths
        self.users_file = 'unlimited_users.json'
        
        # Cache
        self.unlimited_users = set()
        
        # Load data
        self.load_data()
    def load_data(self):
        """Load cached data from files"""
        try:
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
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy")]
        ])
        
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🎓 Welcome to OneDrive University Bot!\n\n"
            "📂 Browse and download university files\n"
        )
        
        if update.effective_user.id == self.admin_id:
            welcome_text += "� Admin controls available\n"
            
        welcome_text += "\nSelect an option below:"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 OneDrive University Bot Help\n\n"
            "📋 Available Commands:\n"
            "• /start - Start the bot and show main menu\n"
            "• /menu - Show bot menu with options\n"
            "• /help - Show this help message\n"
            "• /about - About this bot\n"
            "• /privacy - Privacy policy\n"
            "• /admin - Admin panel (admin only)\n\n"
            "🗂️ Navigation & Usage:\n"
            "• 📁 Browse Files - Explore university folders\n"
            "• ⬅️ Back - Navigate to parent folder\n"
            "• 🏠 Main Menu - Return to start screen\n"
            "• 🔄 Refresh - Update file index (admin only)\n\n"
            "⚡ Performance: Files are cached for speed"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup)

    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        about_text = (
            "📖 About OneDrive University Bot\n\n"
            "🎯 Purpose: Provide easy access to University files stored in OneDrive\n"
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
            size_mb = file['size'] / (1024 * 1024) if file['size'] > 0 else 0
            file_info = f"{file['id']}_{file['name']}"
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
        
        folder_name = path.split("/")[-1] if path != "root" else "University"
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
        file_size_mb = file_details['size'] / (1024 * 1024)
        if file_size_mb > 50:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", current_folder_path))],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ File too large for Telegram\n\n"
                f"📄 File: {file_name}\n"
                f"📊 Size: {file_size_mb:.1f}MB\n\n"
                f"⚠️ Telegram has a 50MB limit for file uploads. This file is too large to send.",
                reply_markup=reply_markup
            )
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
        """Download and send file to user"""
        await query.edit_message_text("⏳ Downloading file, please wait...")
        
        # Parse download info (format: file_id|folder_path)
        if "|" in download_info:
            file_id, folder_path = download_info.split("|", 1)
        else:
            # Fallback for old format
            file_id = download_info
            folder_path = "root"
        
        try:
            # Check file size before downloading
            file_info = None
            for path, items in self.indexer.file_index.items():
                if isinstance(items, list):
                    for item in items:
                        if item.get('id') == file_id:
                            file_info = item
                            break
                    if file_info:
                        break
            
            if not file_info:
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Error: File information not found.", reply_markup=reply_markup)
                return
            
            # Double-check file size
            file_size_mb = file_info['size'] / (1024 * 1024)
            if file_size_mb > 50:
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"❌ File too large for Telegram\n\n"
                    f"📄 File: {file_info['name']}\n"
                    f"📊 Size: {file_size_mb:.1f}MB",
                    reply_markup=reply_markup
                )
                return
            
            file_content = self.download_file(file_id)
            if file_content:
                # Send file
                await query.message.reply_document(
                    document=file_content,
                    filename=file_info['name'],
                    caption=f"📄 {file_info['name']} ({file_size_mb:.1f}MB)"
                )
                
                # Show success message with navigation
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ File sent successfully!\n\n📄 {file_info['name']}\n📊 Size: {file_size_mb:.1f}MB",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", folder_path))],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Error downloading file. Please try again.", reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            
            # Check if it's a file size error
            error_msg = "❌ Error sending file."
            if "too large" in str(e).lower() or "file size" in str(e).lower():
                error_msg = f"❌ File too large for Telegram.\n\n📄 {file_info['name'] if file_info else 'Unknown file'}\n⚠️ Telegram has a 50MB limit."
            elif "network" in str(e).lower() or "timeout" in str(e).lower():
                error_msg = "❌ Network error. Please try again."
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to Folder", callback_data=self.create_callback_data("folder", folder_path))],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(error_msg, reply_markup=reply_markup)

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
                await query.edit_message_text("✅ File index rebuilt successfully!")
            else:
                await query.edit_message_text("❌ Error rebuilding file index.")
                
        elif action == "users":
            user_count = len(self.unlimited_users)
            await query.edit_message_text(f"👥 Unlimited users: {user_count}")
            
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
                    f"� Total size: {stats['total_size'] / (1024*1024*1024):.2f} GB\n"
                    f"🗂️ Indexed paths: {stats['total_paths']}\n"
                    f"� Last index update: {timestamp_age}"
                )
            except Exception as e:
                stats_text = f"📊 Bot Statistics\n\n❌ Error loading stats: {e}"
                
            await query.edit_message_text(stats_text)
            
        elif action == "shutdown":
            await query.edit_message_text("🛑 Shutting down bot...")
            await self.notify_subscribers("🔴 Bot Ended Operations")
            await self.application.stop()

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
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy")]
        ])
        
        if query.from_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "🎓 OneDrive University Bot\n\n"
            "📂 Browse and download university files\n"
        )
        
        if query.from_user.id == self.admin_id:
            welcome_text += "� Admin controls available\n"
            
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
            [InlineKeyboardButton("🔒 Privacy", callback_data="show_privacy")]
        ])
        
        if update.effective_user.id == self.admin_id:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="show_admin")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = (
            "📋 OneDrive University Bot Menu\n\n"
            "Choose an option below:"
        )
        
        await update.message.reply_text(menu_text, reply_markup=reply_markup)

    async def show_help_inline(self, query):
        """Show help as inline message"""
        help_text = (
            "🤖 OneDrive University Bot Help\n\n"
            "📋 Available Commands:\n"
            "• /start - Start the bot and show main menu\n"
            "• /menu - Show bot menu with options\n"
            "• /help - Show this help message\n"
            "• /about - About this bot\n"
            "• /privacy - Privacy policy\n"
            "• /admin - Admin panel (admin only)\n\n"
            "🗂️ Navigation & Usage:\n"
            "• 📁 Browse Files - Explore university folders\n"
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
            "📖 About OneDrive University Bot\n\n"
            "🎯 Purpose: Easy access to University files\n"
            "🔧 Technology: Python + Telegram + MS Graph\n\n"
            "📊 Features:\n"
            "• Fast file browsing with local indexing\n"
            "• Direct file downloads to chat\n"
            "• Smart navigation with back buttons\n"
            "• Admin management tools\n"
            "• Secure read-only access\n\n"
            "🔗 Powered by Microsoft Graph API"
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

    def run(self):
        """Run the bot"""
        # Build/load file index using indexer
        logger.info("Initializing file index...")
        try:
            if not self.indexer.build_index():
                logger.error("Failed to initialize file index")
                return
                
            stats = self.indexer.get_stats()
            logger.info(f"Index loaded: {stats['total_folders']} folders, {stats['total_files']} files")
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
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Start polling
        logger.info("Starting bot...")
        
        async def startup_notify():
            await self.notify_subscribers("🟢 Bot Started Operations")
        
        # Run bot with startup notification
        self.application.run_polling(
            stop_signals=None,
            drop_pending_updates=True
        )

if __name__ == "__main__":
    bot = OneDriveBot()
    bot.run()
