#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Continuously Running Version
Fixed version that properly handles asyncio and runs continuously
"""

import logging
import os
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Microsoft Graph imports
from azure.identity import ClientSecretCredential

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneDriveTelegramBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        
        if not all([self.bot_token, self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError("Missing required environment variables")
        
        self.credential = None
        self.access_token = None
        self.users_cache = {}
        self.file_cache = {}  # Cache for file download info (to handle callback data length limits)
        self.default_user_id = None
        self.authenticated = False
        
        # University folder restriction
        self.base_folder = "University"
        self.restricted_mode = True
        
    def initialize_authentication(self):
        """Initialize authentication and get access token (synchronous)"""
        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Get access token (synchronous call)
            token = self.credential.get_token('https://graph.microsoft.com/.default')
            self.access_token = token.token
            
            logger.info("Authentication token obtained successfully")
            return True
                        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            return False

    async def test_and_cache_users(self):
        """Test authentication and cache users (asynchronous)"""
        if not self.access_token:
            return False
            
        try:
            # Test by getting users
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.access_token}'}
                async with session.get('https://graph.microsoft.com/v1.0/users', headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        users = data.get('value', [])
                        
                        if users:
                            # Cache users
                            for user in users:
                                self.users_cache[user['id']] = {
                                    'id': user['id'],
                                    'name': user['displayName'],
                                    'email': user['userPrincipalName']
                                }
                            
                            # Try to find "Owais Ahmed" as default user
                            owais_user = None
                            for user in users:
                                if 'owais ahmed' in user['displayName'].lower():
                                    owais_user = user
                                    break
                            
                            if owais_user:
                                self.default_user_id = owais_user['id']
                                default_user_name = owais_user['displayName']
                            else:
                                # Fallback to first user if Owais Ahmed not found
                                self.default_user_id = users[0]['id']
                                default_user_name = users[0]['displayName']
                                logger.warning("Owais Ahmed not found, using first user as default")
                            
                            self.authenticated = True
                            
                            logger.info(f"Authentication successful. Found {len(users)} users.")
                            logger.info(f"Default user: {default_user_name}")
                            return True
                    else:
                        logger.error(f"Failed to get users: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"User caching failed: {e}")
            return False

    async def get_onedrive_items(self, path: str = "/", user_id: str = None) -> List[Dict[str, Any]]:
        """Get items from OneDrive using direct HTTP requests - restricted to University folder"""
        if not self.authenticated or not self.access_token:
            logger.warning("Not authenticated, returning empty list")
            return []
        
        if not user_id:
            user_id = self.default_user_id
            
        if not user_id:
            return []
        
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Force all paths to be within University folder
            if self.restricted_mode:
                if path == "/" or path == "":
                    # Default to University folder
                    clean_path = self.base_folder
                else:
                    # Ensure path starts with University and remove any attempts to go outside
                    clean_path = path.strip("/")
                    if not clean_path.startswith(self.base_folder):
                        clean_path = f"{self.base_folder}/{clean_path}"
                    
                    # Remove any "../" attempts to escape the University folder
                    clean_path = clean_path.replace("../", "").replace("..\\", "")
                    
                    # Ensure we're still within University folder
                    if not clean_path.startswith(self.base_folder):
                        clean_path = self.base_folder
                
                url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/{clean_path}:/children'
            else:
                # Original unrestricted mode (not used when restricted_mode=True)
                if path == "/" or path == "":
                    url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root/children'
                else:
                    clean_path = path.strip("/")
                    url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/{clean_path}:/children'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('value', [])
                        
                        result = []
                        for item in items:
                            result.append({
                                'id': item['id'],
                                'name': item['name'],
                                'is_folder': 'folder' in item,
                                'size': item.get('size', 0),
                                'download_url': item.get('@microsoft.graph.downloadUrl'),
                                'web_url': item.get('webUrl'),
                                'user_id': user_id
                            })
                        
                        logger.info(f"Retrieved {len(result)} items from OneDrive path: {clean_path if self.restricted_mode else path}")
                        return result
                        
                    elif response.status == 404:
                        logger.info(f"Path not found: {clean_path if self.restricted_mode else path}")
                        return []
                    else:
                        logger.error(f"API error {response.status} for path {clean_path if self.restricted_mode else path}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error accessing OneDrive path {path}: {e}")
            return []

    async def download_and_send_file(self, query, file_info: dict, path: str):
        """Download and send file to Telegram chat"""
        try:
            file_name = file_info['name']
            download_url = file_info.get('download_url')
            file_size = file_info.get('size', 0)
            
            # Check file size (Telegram limit is 50MB for bots)
            max_size_mb = 50
            file_size_mb = file_size / 1024 / 1024
            
            if file_size_mb > max_size_mb:
                await query.edit_message_text(
                    f"📄 *File:* {file_name}\n\n" +
                    f"❌ *Error:* File too large ({file_size_mb:.1f} MB)\n" +
                    f"📊 *Telegram limit:* {max_size_mb} MB\n\n" +
                    "💡 Try accessing smaller files or use OneDrive web interface for large files.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                        InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                    ]])
                )
                return
            
            if not download_url:
                # Try to fetch download URL from OneDrive API
                try:
                    user_id = self.default_user_id
                    if user_id:
                        file_path_full = f"{path.rstrip('/')}/{file_name}" if path != "/" else file_name
                        
                        # Force path to be within University folder
                        if self.restricted_mode:
                            if not file_path_full.startswith(self.base_folder):
                                file_path_full = f"{self.base_folder}/{file_path_full}"
                        
                        headers = {'Authorization': f'Bearer {self.access_token}'}
                        url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/{file_path_full}'
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, headers=headers) as response:
                                if response.status == 200:
                                    file_data = await response.json()
                                    download_url = file_data.get('@microsoft.graph.downloadUrl')
                
                    if not download_url:
                        await query.edit_message_text(
                            f"📄 *File:* {file_name}\n\n" +
                            "❌ *Error:* Cannot get download URL\n" +
                            "This file cannot be downloaded directly.",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                                InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                            ]])
                        )
                        return
                except Exception as e:
                    logger.error(f"Error fetching download URL: {e}")
                    await query.edit_message_text(
                        f"📄 *File:* {file_name}\n\n" +
                        "❌ *Error:* Cannot access file\n" +
                        "Please try again later.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                            InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                        ]])
                    )
                    return
            
            # Send "downloading" message
            await query.edit_message_text(
                f"📄 *Downloading:* {file_name}\n\n" +
                f"📊 *Size:* {file_size_mb:.1f} MB\n" +
                "⏳ Please wait...",
                parse_mode='Markdown'
            )
            
            # Download file
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        file_data = await response.read()
                        
                        # Send file to chat
                        await query.message.reply_document(
                            document=file_data,
                            filename=file_name,
                            caption=f"📄 *{file_name}*\n📂 From: University{path if path != '/' else ''}"
                        )
                        
                        # Update message with success
                        await query.edit_message_text(
                            f"📄 *File:* {file_name}\n\n" +
                            f"✅ *Downloaded successfully!*\n" +
                            f"📊 *Size:* {file_size_mb:.1f} MB",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                                InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                            ]])
                        )
                    else:
                        await query.edit_message_text(
                            f"📄 *File:* {file_name}\n\n" +
                            f"❌ *Download failed*\n" +
                            f"Server returned status: {response.status}",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                                InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                            ]])
                        )
        
        except Exception as e:
            logger.error(f"Error downloading file {file_info.get('name', 'Unknown')}: {str(e)}")
            await query.edit_message_text(
                f"📄 *File:* {file_info.get('name', 'Unknown')}\n\n" +
                f"❌ *Error:* {str(e)[:100]}...\n\n" +
                "Please try again or contact administrator.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data=f"browse:{path}"),
                    InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                ]])
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        welcome_message = """*Welcome to University OneDrive Bot!*

This bot gives you access to University files through Telegram.

🔐 *Authentication Status:* ✅ Connected
👤 *User:* {user}
📁 *University Files:* {file_count}

*Available Commands:*
• /start - Show this welcome message
• Use the buttons below to browse University files

*Features:*
• 📁 Browse University folders and files
• 📥 Download files directly to Telegram
• 🔍 Navigate through University structure
• 📚 Access to semester materials and resources

*Note:* This bot is restricted to University folder only."""
        
        if self.authenticated and self.default_user_id:
            user_name = self.users_cache[self.default_user_id]['name']
            # Get University folder items count
            university_items = await self.get_onedrive_items("/")  # This will default to University folder
            file_count = len(university_items)
        else:
            user_name = "Not connected"
            file_count = 0
            
        formatted_message = welcome_message.format(
            user=user_name,
            file_count=file_count
        )
        
        await update.message.reply_text(
            formatted_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📁 Browse Files", callback_data="browse:/"),
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
            ]]),
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("browse:"):
            path = data[7:]  # Remove "browse:" prefix
            await self.show_folder_contents(query, path)
        elif data.startswith("page:"):
            # Handle pagination: format is "page:path:page_number"
            page_data = data[5:]  # Remove "page:" prefix
            parts = page_data.rsplit(":", 1)  # Split from the right to handle paths with colons
            if len(parts) == 2:
                path, page_str = parts
                try:
                    page = int(page_str)
                    await self.show_folder_contents(query, path, page)
                except ValueError:
                    await query.edit_message_text("❌ Invalid page number")
            else:
                await query.edit_message_text("❌ Invalid page data")
        elif data.startswith("file:"):
            # Handle file download using cached file info
            file_hash = data[5:]  # Remove "file:" prefix
            
            if file_hash in self.file_cache:
                file_info = self.file_cache[file_hash]
                await self.download_and_send_file(query, file_info, file_info['path'])
            else:
                await query.edit_message_text(
                    "❌ File information not found. Please navigate back and try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="browse:/"),
                        InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                    ]])
                )
        elif data == "refresh":
            # Create a fake update for the start command
            fake_update = Update.de_json({
                'update_id': update.update_id,
                'message': {
                    'message_id': query.message.message_id,
                    'from': query.from_user.to_dict(),
                    'chat': query.message.chat.to_dict(),
                    'date': query.message.date.timestamp(),
                    'text': '/start'
                }
            }, context.bot)
            fake_update.message = query.message
            await self.start(fake_update, context)
        else:
            await query.edit_message_text("❓ Unknown command")

    async def show_folder_contents(self, query, path: str, page: int = 0):
        """Show contents of a folder with pagination"""
        items = await self.get_onedrive_items(path)
        
        if not items:
            await query.edit_message_text(
                f"📂 *Folder:* {path if path != '/' else 'University'}\n\n" +
                "📭 This folder is empty or could not be accessed.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="browse:/"),
                    InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                ]])
            )
            return
        
        # Sort items: folders first, then files
        folders = [item for item in items if item['is_folder']]
        files = [item for item in items if not item['is_folder']]
        all_items = folders + files
        
        # Pagination settings
        items_per_page = 8
        total_pages = (len(all_items) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = all_items[start_idx:end_idx]
        
        # Create message
        folder_name = path if path != '/' else 'University'
        message = f"📂 *Folder:* {folder_name}\n\n"
        message += f"📊 *Total Items:* {len(all_items)} ({len(folders)} folders, {len(files)} files)\n"
        
        if total_pages > 1:
            message += f"📄 *Page:* {page + 1}/{total_pages}\n"
        
        message += "\n"
        
        # Show items on current page
        if page_items:
            message += "*� Contents:*\n"
            for item in page_items:
                if item['is_folder']:
                    message += f"📁 {item['name']}\n"
                else:
                    size_mb = item['size'] / 1024 / 1024
                    if size_mb > 1:
                        size_str = f"({size_mb:.1f} MB)"
                    else:
                        size_str = f"({item['size']} bytes)"
                    message += f"📄 {item['name']} {size_str}\n"
        
        # Create buttons for all items on current page
        buttons = []
        
        for item in page_items:
            if item['is_folder']:
                # Folder button
                folder_path = f"{path.rstrip('/')}/{item['name']}" if path != "/" else item['name']
                buttons.append([InlineKeyboardButton(
                    f"📁 {item['name']}", 
                    callback_data=f"browse:{folder_path}"
                )])
            else:
                # File button - use cache to store file info and use shorter callback
                file_id = f"{path}_{item['name']}"
                file_hash = str(hash(file_id))[-8:]  # Use last 8 chars of hash as short ID
                
                # Store file info in cache
                self.file_cache[file_hash] = {
                    'name': item['name'],
                    'size': item['size'],
                    'download_url': item.get('download_url', ''),
                    'path': path
                }
                
                buttons.append([InlineKeyboardButton(
                    f"📄 {item['name']}", 
                    callback_data=f"file:{file_hash}"
                )])
        
        # Add pagination buttons if needed
        if total_pages > 1:
            pagination_buttons = []
            if page > 0:
                pagination_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{path}:{page-1}"))
            if page < total_pages - 1:
                pagination_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{path}:{page+1}"))
            
            if pagination_buttons:
                buttons.append(pagination_buttons)
        
        # Add navigation buttons
        nav_buttons = []
        if path != "/":
            # Calculate parent path
            parent_path = "/".join(path.strip("/").split("/")[:-1])
            if not parent_path:
                parent_path = "/"
            nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data=f"browse:{parent_path}"))
        
        nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="browse:/"))
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"browse:{path}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        try:
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            # Handle message too long error
            if "message is too long" in str(e).lower():
                # Truncate message and try again
                short_message = f"📂 *Folder:* {folder_name}\n\n"
                short_message += f"📊 *Items:* {len(all_items)}\n"
                if total_pages > 1:
                    short_message += f"📄 *Page:* {page + 1}/{total_pages}\n"
                short_message += "\n*Click buttons below to browse items*"
                
                await query.edit_message_text(
                    short_message,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                raise e

# Global bot instance
bot_instance = None

async def post_init(application: Application) -> None:
    """Post initialization hook"""
    global bot_instance
    logger.info("Starting post-initialization...")
    
    # Test authentication and cache users
    success = await bot_instance.test_and_cache_users()
    if success:
        print("✅ OneDrive connected successfully!")
        print(f"👤 Default user: {bot_instance.users_cache[bot_instance.default_user_id]['name']}")
    else:
        print("⚠️ OneDrive connection failed - some features may not work")

def main():
    """Main function to run the bot"""
    global bot_instance
    
    print("🔧 Initializing OneDrive Telegram Bot...")
    
    try:
        # Create bot instance
        bot_instance = OneDriveTelegramBot()
        
        # Initialize authentication (synchronous)
        print("🔐 Getting authentication token...")
        auth_success = bot_instance.initialize_authentication()
        if not auth_success:
            print("❌ Failed to get authentication token")
            return
            
        print("✅ Authentication token obtained")
        
        # Create Telegram application
        print("🤖 Setting up Telegram bot...")
        application = Application.builder().token(bot_instance.bot_token).post_init(post_init).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot_instance.start))
        application.add_handler(CallbackQueryHandler(bot_instance.handle_callback))
        
        print("🚀 Starting bot...")
        print("📱 Send /start to begin using the bot")
        print("🔄 Bot is now running continuously...")
        print("⏹️  Press Ctrl+C to stop")
        
        # Run the bot
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot startup error: {e}")

if __name__ == '__main__':
    main()
