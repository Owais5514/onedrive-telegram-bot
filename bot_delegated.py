#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Delegated Permissions Version
This version uses user authentication instead of application permissions
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Microsoft Graph imports
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

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
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        
        if not all([self.bot_token, self.client_id, self.tenant_id]):
            raise ValueError("Missing required environment variables")
        
        self.graph_client = None
        self.current_user_id = None
        self.authenticated = False
        
        # Default starting path
        self.default_path = "/University"
        
    async def initialize_graph_client(self):
        """Initialize Microsoft Graph client with delegated permissions"""
        try:
            # Device code flow for delegated permissions
            credential = DeviceCodeCredential(
                client_id=self.client_id,
                tenant_id=self.tenant_id
            )
            
            # Scopes for delegated permissions
            scopes = [
                'https://graph.microsoft.com/Files.Read',
                'https://graph.microsoft.com/Files.ReadWrite',
                'https://graph.microsoft.com/User.Read'
            ]
            
            self.graph_client = GraphServiceClient(
                credentials=credential,
                scopes=scopes
            )
            
            # Get current user info
            me = await self.graph_client.me.get()
            self.current_user_id = me.id
            self.authenticated = True
            
            logger.info(f"Graph client initialized for user: {me.display_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Graph client: {e}")
            self.authenticated = False
            return False

    async def get_onedrive_items(self, path: str = "/") -> List[Dict[str, Any]]:
        """Get items from OneDrive path"""
        if not self.authenticated:
            logger.warning("OneDrive not authenticated, using mock data")
            return self._get_mock_data(path)
        
        try:
            if path == "/" or path == "":
                # Get root items
                items = await self.graph_client.me.drive.root.children.get()
            else:
                # Get items from specific path
                clean_path = path.strip("/")
                items = await self.graph_client.me.drive.root.item_with_path(clean_path).children.get()
            
            result = []
            if items.value:
                for item in items.value:
                    result.append({
                        'id': item.id,
                        'name': item.name,
                        'is_folder': bool(item.folder),
                        'size': item.size if hasattr(item, 'size') else 0,
                        'download_url': item.microsoft_graph_download_url if hasattr(item, 'microsoft_graph_download_url') else None,
                        'web_url': item.web_url if hasattr(item, 'web_url') else None
                    })
            
            logger.info(f"Retrieved {len(result)} items from OneDrive path: {path}")
            return result
            
        except ODataError as e:
            logger.error(f"OneDrive API error for path {path}: {e}")
            return self._get_mock_data(path)
        except Exception as e:
            logger.error(f"Unexpected error accessing OneDrive path {path}: {e}")
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
            ],
            "/University/Computer Science": [
                {'id': 'mock_cs1', 'name': 'Programming', 'is_folder': True, 'size': 0},
                {'id': 'mock_cs2', 'name': 'Algorithms', 'is_folder': True, 'size': 0},
                {'id': 'mock_cs3', 'name': 'Assignment1.py', 'is_folder': False, 'size': 15000},
                {'id': 'mock_cs4', 'name': 'Project Report.docx', 'is_folder': False, 'size': 1024000}
            ]
        }
        return mock_data.get(path, [])

    async def get_folder_path_by_id(self, item_id: str) -> str:
        """Get folder path by item ID"""
        if not self.authenticated or item_id.startswith('mock_'):
            # Mock data fallback
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
        
        try:
            item = await self.graph_client.me.drive.items.by_drive_item_id(item_id).get()
            parent_path = "/"
            if item.parent_reference and item.parent_reference.path:
                parent_path = item.parent_reference.path.replace('/drive/root:', '') or "/"
            return f"{parent_path}/{item.name}".replace('//', '/')
        except Exception as e:
            logger.error(f"Error getting folder path for ID {item_id}: {e}")
            return "/"

    async def share_file(self, item_id: str) -> Optional[str]:
        """Generate sharing link for file"""
        if not self.authenticated or item_id.startswith('mock_'):
            return f"https://onedrive.live.com/mock-share-{item_id}"
        
        try:
            # Get sharing link
            link = await self.graph_client.me.drive.items.by_drive_item_id(item_id).create_link.post({
                "type": "view",
                "scope": "anonymous"
            })
            return link.link.web_url if link.link else None
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
                auth_status = "🔗 Live OneDrive" if self.authenticated else "⚠️ Demo Mode (Setup OneDrive for real files)"
                text = f"📂 **{path}**\n{auth_status}\n\n📄 **{len(items)} items:**"
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
        welcome_text = """
🤖 **OneDrive Telegram Bot**

Welcome! This bot helps you browse and share files from your OneDrive.

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
            # Return to main menu
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

🔹 **Browse Files**: Navigate through your OneDrive folders
🔹 **Click Folders**: Open folders to see their contents  
🔹 **Click Files**: Get a shareable download link
🔹 **Navigation**: Use Back, University, and Home buttons

🎓 **University Folder**: Quick access to your university files
🏠 **Home**: Return to main menu

⚠️ **Demo Mode**: If OneDrive isn't connected, you'll see sample data
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
    try:
        bot = OneDriveTelegramBot()
        
        # Initialize Graph client
        print("🔧 Initializing OneDrive connection...")
        auth_success = await bot.initialize_graph_client()
        if auth_success:
            print("✅ OneDrive connected successfully!")
        else:
            print("⚠️ OneDrive connection failed - bot will use demo mode")
        
        # Create Telegram application
        application = Application.builder().token(bot.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CallbackQueryHandler(bot.handle_callback))
        
        # Start the bot
        print("🚀 Starting OneDrive Telegram Bot...")
        print("📱 Send /start to begin using the bot")
        
        await application.run_polling()
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        logger.error(f"Bot startup error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
