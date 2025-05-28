#!/usr/bin/env python3
"""
OneDrive Bot with working Microsoft Graph API calls using HTTP requests
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

class OneDriveTelegramBotWorking:
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
        
        # Default starting path
        self.default_path = "/University"
        
    async def initialize_authentication(self):
        """Initialize authentication and get access token"""
        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Get access token
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
            logger.warning("Not authenticated, using mock data")
            return self._get_mock_data(path)
        
        if not user_id:
            user_id = self.default_user_id
            
        if not user_id:
            return self._get_mock_data(path)
        
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
                        return self._get_mock_data(path)
                        
        except Exception as e:
            logger.error(f"Error accessing OneDrive path {path}: {e}")
            return self._get_mock_data(path)

    def _get_mock_data(self, path: str) -> List[Dict[str, Any]]:
        """Generate mock data when OneDrive is not accessible"""
        mock_data = {
            "/": [
                {'id': 'mock_1', 'name': 'University', 'is_folder': True, 'size': 0},
                {'id': 'mock_2', 'name': 'Personal', 'is_folder': True, 'size': 0},
                {'id': 'mock_3', 'name': 'Work', 'is_folder': True, 'size': 0},
                {'id': 'mock_4', 'name': 'Documents', 'is_folder': True, 'size': 0}
            ],
            "/University": [
                {'id': 'mock_u1', 'name': 'Computer Science', 'is_folder': True, 'size': 0},
                {'id': 'mock_u2', 'name': 'Mathematics', 'is_folder': True, 'size': 0},
                {'id': 'mock_u3', 'name': 'Physics', 'is_folder': True, 'size': 0},
                {'id': 'mock_u4', 'name': 'Research Paper.pdf', 'is_folder': False, 'size': 2048000}
            ]
        }
        return mock_data.get(path, [])

    async def get_folder_path_by_id(self, item_id: str, user_id: str = None) -> str:
        """Get folder path by item ID using HTTP requests"""
        if not self.authenticated or item_id.startswith('mock_'):
            mock_paths = {
                'mock_1': '/University',
                'mock_2': '/Personal', 
                'mock_3': '/Work',
                'mock_4': '/Documents',
                'mock_u1': '/University/Computer Science',
                'mock_u2': '/University/Mathematics',
                'mock_u3': '/University/Physics'
            }
            return mock_paths.get(item_id, '/')
        
        if not user_id:
            user_id = self.default_user_id
            
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{item_id}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        parent_ref = data.get('parentReference', {})
                        parent_path = parent_ref.get('path', '').replace('/drive/root:', '') or "/"
                        return f"{parent_path}/{data['name']}".replace('//', '/')
                    else:
                        return "/"
                        
        except Exception as e:
            logger.error(f"Error getting folder path for ID {item_id}: {e}")
            return "/"

    async def share_file(self, item_id: str, user_id: str = None) -> Optional[str]:
        """Generate sharing link for file using HTTP requests"""
        if not self.authenticated or item_id.startswith('mock_'):
            return f"https://onedrive.live.com/mock-share-{item_id}"
        
        if not user_id:
            user_id = self.default_user_id
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            url = f'https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{item_id}/createLink'
            payload = {
                "type": "view",
                "scope": "anonymous"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 201:
                        data = await response.json()
                        return data.get('link', {}).get('webUrl')
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Error creating share link for {item_id}: {e}")
            return None

    def create_file_keyboard(self, items: List[Dict[str, Any]], current_path: str) -> InlineKeyboardMarkup:
        """Create inline keyboard with files and folders in 2-column layout"""
        keyboard = []
        
        # Add items in pairs (2-column layout)
        for i in range(0, len(items), 2):
            row = []
            
            # First item in row
            item1 = items[i]
            emoji1 = "📁" if item1['is_folder'] else "📄"
            name1 = item1['name'][:20] + "..." if len(item1['name']) > 20 else item1['name']
            
            if item1['is_folder']:
                callback1 = f"nav:{item1['id']}"
            else:
                callback1 = f"file:{item1['id']}"
            
            row.append(InlineKeyboardButton(f"{emoji1} {name1}", callback_data=callback1))
            
            # Second item in row (if exists)
            if i + 1 < len(items):
                item2 = items[i + 1]
                emoji2 = "📁" if item2['is_folder'] else "📄"
                name2 = item2['name'][:20] + "..." if len(item2['name']) > 20 else item2['name']
                
                if item2['is_folder']:
                    callback2 = f"nav:{item2['id']}"
                else:
                    callback2 = f"file:{item2['id']}"
                
                row.append(InlineKeyboardButton(f"{emoji2} {name2}", callback_data=callback2))
            
            keyboard.append(row)
        
        # Navigation buttons
        nav_row = []
        
        # Back button (if not at root)
        if current_path != "/" and current_path != self.default_path:
            nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data="nav:back"))
        
        # University button (if not already there)
        if current_path != self.default_path:
            nav_row.append(InlineKeyboardButton("🎓 University", callback_data="nav:university"))
        
        # Home button
        nav_row.append(InlineKeyboardButton("🏠 Home", callback_data="nav:/home"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        return InlineKeyboardMarkup(keyboard)

    async def show_files_in_path(self, update: Update, path: str, edit_message: bool = True):
        """Display files and folders for a given path"""
        try:
            items = await self.get_onedrive_items(path)
            
            if not items:
                text = f"📂 **{path}**\n\n📭 This folder is empty"
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Home", callback_data="nav:/home")
                ]])
            else:
                auth_status = "🔗 Live OneDrive" if self.authenticated else "⚠️ Demo Mode"
                user_info = ""
                if self.authenticated and self.default_user_id in self.users_cache:
                    user_info = f" ({self.users_cache[self.default_user_id]['name']})"
                    
                text = f"📂 **{path}**\n{auth_status}{user_info}\n\n📄 **{len(items)} items:**"
                keyboard = self.create_file_keyboard(items, path)
            
            if edit_message and update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                message = update.callback_query.message if update.callback_query else update.message
                await message.reply_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing files in path {path}: {e}")
            error_text = f"❌ Error accessing folder: {path}\n\n{str(e)}"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Home", callback_data="nav:/home")
            ]])
            
            if edit_message and update.callback_query:
                await update.callback_query.edit_message_text(
                    text=error_text,
                    reply_markup=keyboard
                )
            else:
                message = update.callback_query.message if update.callback_query else update.message
                await message.reply_text(text=error_text, reply_markup=keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        status_emoji = "🔗" if self.authenticated else "⚠️"
        status_text = "Connected to OneDrive" if self.authenticated else "Demo Mode - Check setup"
        
        welcome_text = f"""
🤖 **OneDrive Telegram Bot**

{status_emoji} **Status**: {status_text}

🎯 **Features:**
• Browse folders and files
• Download and share files
• Navigate with buttons
• University folder quick access

🚀 **Get Started:**
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📁 Browse Files", callback_data="browse_start"),
                InlineKeyboardButton("📍 Current Location", callback_data="show_current")
            ],
            [
                InlineKeyboardButton("🎓 University Folder", callback_data="nav:university"),
                InlineKeyboardButton("❓ Help", callback_data="show_help")
            ]
        ])
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "browse_start":
            await self.show_files_in_path(update, self.default_path)
            
        elif data == "show_current":
            current_path = context.user_data.get('current_path', self.default_path)
            await self.show_files_in_path(update, current_path)
            
        elif data == "nav:/home":
            await self.start(update, context)
            
        elif data == "nav:university":
            context.user_data['current_path'] = self.default_path
            await self.show_files_in_path(update, self.default_path)
            
        elif data == "nav:back":
            current_path = context.user_data.get('current_path', self.default_path)
            parent_path = "/".join(current_path.split("/")[:-1]) or "/"
            context.user_data['current_path'] = parent_path
            await self.show_files_in_path(update, parent_path)
            
        elif data.startswith("nav:"):
            item_id = data[4:]  # Remove "nav:" prefix
            folder_path = await self.get_folder_path_by_id(item_id)
            context.user_data['current_path'] = folder_path
            await self.show_files_in_path(update, folder_path)
            
        elif data.startswith("file:"):
            item_id = data[5:]  # Remove "file:" prefix
            share_url = await self.share_file(item_id)
            
            if share_url:
                await query.edit_message_text(
                    f"📄 **File Shared Successfully!**\n\n🔗 **Share Link:**\n{share_url}\n\n💡 Click the link to download or view the file.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Files", callback_data="browse_start"),
                        InlineKeyboardButton("🏠 Home", callback_data="nav:/home")
                    ]]),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to generate share link for this file.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Files", callback_data="browse_start"),
                        InlineKeyboardButton("🏠 Home", callback_data="nav:/home")
                    ]])
                )
        
        elif data == "show_help":
            help_text = """
📖 **How to Use:**

🔹 **Browse Files**: Navigate through OneDrive folders
🔹 **Click Folders**: Open folders to see their contents  
🔹 **Click Files**: Get a shareable download link
🔹 **Navigation**: Use Back, University, and Home buttons

🎓 **University Folder**: Quick access to university files
🏠 **Home**: Return to main menu

🔗 **Live Mode**: Real OneDrive files and folders
⚠️ **Demo Mode**: Sample data (check Azure setup)
"""
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📁 Browse Files", callback_data="browse_start"),
                    InlineKeyboardButton("🏠 Home", callback_data="nav:/home")
                ]]),
                parse_mode='Markdown'
            )

async def main():
    """Main function to run the bot"""
    bot = None
    application = None
    
    try:
        bot = OneDriveTelegramBotWorking()
        
        # Initialize authentication
        print("🔧 Initializing OneDrive connection...")
        auth_success = await bot.initialize_authentication()
        if auth_success:
            print("✅ OneDrive connected successfully!")
            print(f"👤 Default user: {bot.users_cache[bot.default_user_id]['name']}")
        else:
            print("⚠️ OneDrive connection failed - bot will use demo mode")
        
        # Create Telegram application
        application = Application.builder().token(bot.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CallbackQueryHandler(bot.handle_callback))
        
        # Start the bot
        print("🚀 Starting OneDrive Telegram Bot (Working Version)...")
        print("📱 Send /start to begin using the bot")
        
        await application.run_polling()
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot startup error: {e}")
    finally:
        if application:
            try:
                await application.shutdown()
            except:
                pass

if __name__ == '__main__':
    asyncio.run(main())
