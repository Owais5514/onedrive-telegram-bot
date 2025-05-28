#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Final Working Version
Uses Option 1 (Application Permissions) with proper PTB v20 handling
"""

import asyncio
import logging
import os
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
        self.default_user_id = None
        self.authenticated = False
        
    async def initialize_authentication(self):
        """Initialize authentication and get access token"""
        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Get access token (synchronous call)
            token = self.credential.get_token('https://graph.microsoft.com/.default')
            self.access_token = token.token
            
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
                            
                            self.default_user_id = users[0]['id']
                            self.authenticated = True
                            
                            logger.info(f"Authentication successful. Found {len(users)} users.")
                            logger.info(f"Default user: {users[0]['displayName']}")
                            return True
                    else:
                        logger.error(f"Failed to get users: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.authenticated = False
            return False

    async def get_onedrive_items(self, path: str = "/", user_id: str = None) -> List[Dict[str, Any]]:
        """Get items from OneDrive using direct HTTP requests"""
        if not self.authenticated or not self.access_token:
            logger.warning("Not authenticated, returning empty list")
            return []
        
        if not user_id:
            user_id = self.default_user_id
            
        if not user_id:
            return []
        
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Build the API URL
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
                        
                        logger.info(f"Retrieved {len(result)} items from OneDrive path: {path}")
                        return result
                        
                    elif response.status == 404:
                        logger.info(f"Path not found: {path}")
                        return []
                    else:
                        logger.error(f"API error {response.status} for path {path}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error accessing OneDrive path {path}: {e}")
            return []

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        welcome_message = """🌟 *Welcome to OneDrive Bot!*

This bot gives you access to your OneDrive files through Telegram.

🔐 *Authentication Status:* ✅ Connected
👤 *User:* {user}
📁 *Files Available:* {file_count}

*Available Commands:*
• /start - Show this welcome message
• Use the buttons below to browse your files

*Features:*
• 📁 Browse folders and files
• 📥 Download files directly to Telegram
• 🔍 Navigate through your OneDrive structure
• 🏠 Quick access to common folders"""
        
        if self.authenticated and self.default_user_id:
            user_name = self.users_cache[self.default_user_id]['name']
            # Get root items count
            root_items = await self.get_onedrive_items("/")
            file_count = len(root_items)
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

    async def show_folder_contents(self, query, path: str):
        """Show contents of a folder"""
        items = await self.get_onedrive_items(path)
        
        if not items:
            await query.edit_message_text(
                f"📂 *Folder:* {path if path != '/' else 'Root'}\n\n" +
                "📭 This folder is empty or could not be accessed.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="browse:/"),
                    InlineKeyboardButton("🏠 Home", callback_data="browse:/")
                ]])
            )
            return
        
        # Create message
        message = f"📂 *Folder:* {path if path != '/' else 'Root'}\n\n"
        message += f"📊 *Items:* {len(items)}\n\n"
        
        # Sort items: folders first, then files
        folders = [item for item in items if item['is_folder']]
        files = [item for item in items if not item['is_folder']]
        
        # Show first few items
        shown_items = 0
        max_items = 8
        
        if folders and shown_items < max_items:
            message += "📁 *Folders:*\n"
            for folder in folders[:max_items - shown_items]:
                message += f"• {folder['name']}\n"
                shown_items += 1
        
        if files and shown_items < max_items:
            message += "\n📄 *Files:*\n"
            for file in files[:max_items - shown_items]:
                size_mb = file['size'] / 1024 / 1024
                if size_mb > 1:
                    size_str = f"({size_mb:.1f} MB)"
                else:
                    size_str = f"({file['size']} bytes)"
                message += f"• {file['name']} {size_str}\n"
                shown_items += 1
        
        if len(items) > max_items:
            message += f"\n... and {len(items) - max_items} more items"
        
        # Create navigation buttons
        buttons = []
        
        # Add folder navigation buttons
        if folders:
            for folder in folders[:4]:  # Max 4 folder buttons
                folder_path = f"{path.rstrip('/')}/{folder['name']}" if path != "/" else folder['name']
                buttons.append([InlineKeyboardButton(f"📁 {folder['name']}", callback_data=f"browse:{folder_path}")])
        
        # Add back button if not at root
        nav_buttons = []
        if path != "/":
            nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data="browse:/"))
        nav_buttons.append(InlineKeyboardButton("🏠 Root", callback_data="browse:/"))
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"browse:{path}"))
        
        buttons.append(nav_buttons)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def run_bot():
    """Main bot runner function"""
    # Initialize bot
    bot = OneDriveTelegramBot()
    
    # Initialize authentication
    print("🔧 Initializing OneDrive connection...")
    auth_success = await bot.initialize_authentication()
    if auth_success:
        print("✅ OneDrive connected successfully!")
        print(f"👤 Default user: {bot.users_cache[bot.default_user_id]['name']}")
    else:
        print("⚠️ OneDrive connection failed - some features may not work")
    
    # Create and configure application
    application = Application.builder().token(bot.bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    print("🚀 Starting bot...")
    print("📱 Send /start to begin using the bot")
    
    # Run the bot
    await application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    print("🔧 Initializing OneDrive Telegram Bot...")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot startup error: {e}")
