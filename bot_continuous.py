#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Continuously Running Version
Fixed version that properly handles asyncio and runs continuously
"""

import logging
import os
import asyncio
import aiohttp
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        
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
        
        # New features
        self.user_query_limits = {}  # Track daily query limits per user
        self.unlimited_users = set()  # Users with unlimited access
        self.ephemeral_messages = {}  # Track messages for auto-deletion
        self.file_index = {}  # Index of all files with descriptions
        self.file_index_path = "file_index.json"  # Path to save file index
        self.index_timestamp_path = "index_timestamp.txt"  # Track when index was last built
        
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
        if self.authenticated:
            service_status = "✅ Online"
        else:
            service_status = "❌ Offline"
            
        welcome_message = f"""*Welcome to University OneDrive Bot!*

📊 *Service Status:* {service_status}

*Choose options from below:*"""
        
        # Check if it's a group chat
        is_group = update.message.chat.type in ['group', 'supergroup']
        
        if is_group:
            # Send ephemeral message in groups
            sent_message = await update.message.reply_text(
                welcome_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📁 Browse Files", callback_data="browse:/"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
                    InlineKeyboardButton("🤖 AI Search", callback_data="ai_search")
                ]]),
                parse_mode='Markdown'
            )
            
            # Schedule message for deletion
            await asyncio.create_task(
                self.schedule_message_deletion(
                    sent_message.chat.id, 
                    sent_message.message_id, 
                    update.message.from_user.id
                )
            )
        else:
            # Normal message in private chat
            await update.message.reply_text(
                welcome_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📁 Browse Files", callback_data="browse:/"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
                    InlineKeyboardButton("🤖 AI Search", callback_data="ai_search")
                ]]),
                parse_mode='Markdown'
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        # Update interaction time for ephemeral messages
        self.update_message_interaction(query.message.chat.id, query.message.message_id)
        
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
        elif data == "ai_search":
            await self.handle_ai_search(query, context)
        else:
            await query.edit_message_text("❓ Unknown command")

    async def handle_ai_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI search queries"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            
            # Check rate limit
            if not self.check_user_query_limit(user_id):
                await query.edit_message_text(
                    "❌ *Daily Limit Reached*\n\n"
                    "You have reached your daily limit of 1 AI search query.\n"
                    "Please try again tomorrow or contact an administrator for unlimited access.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="browse:/")
                    ]])
                )
                return
            
            await query.edit_message_text(
                "🤖 *AI Search*\n\n"
                "Ask me to search for files! I'll use AI to find the most relevant files in your University OneDrive.\n\n"
                "*Example queries:*\n"
                "• 'Find my calculus notes'\n"
                "• 'Show me Python programming files'\n"
                "• 'Look for semester 1 assignments'\n\n"
                "💡 *Please type your search query as a message:*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="browse:/")
                ]])
            )
            
            # Set user in AI search mode
            context.user_data['ai_search_mode'] = True
            context.user_data['ai_search_message_id'] = query.message.message_id
        else:
            # Handle text message for AI search
            if context.user_data.get('ai_search_mode'):
                user_id = update.message.from_user.id
                query_text = update.message.text
                
                # Check rate limit again
                if not self.check_user_query_limit(user_id):
                    await update.message.reply_text(
                        "❌ You have exceeded your daily limit. Please try again tomorrow."
                    )
                    return
                
                # Increment query count
                self.increment_user_query_count(user_id)
                
                # Send "searching" message
                search_msg = await update.message.reply_text(
                    "🔍 *Searching files...*\n\n"
                    f"Query: _{query_text}_\n\n"
                    "Please wait while I search through the University files and analyze the results with AI...",
                    parse_mode='Markdown'
                )
                
                try:
                    # Search files
                    file_results = self.search_files(query_text)
                    
                    if not file_results:
                        await search_msg.edit_text(
                            "❌ *No Files Found*\n\n"
                            f"Query: _{query_text}_\n\n"
                            "No files matched your search query. Try using different keywords or check if the files exist in the University folder.",
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Try Again", callback_data="ai_search"),
                                InlineKeyboardButton("📁 Browse Files", callback_data="browse:/")
                            ]])
                        )
                        return
                    
                    # Query Claude AI
                    ai_response = await self.query_claude_ai(query_text, file_results)
                    
                    # Create response with top files
                    response_text = f"🤖 *AI Search Results*\n\n"
                    response_text += f"*Query:* _{query_text}_\n\n"
                    response_text += f"*AI Analysis:*\n{ai_response}\n\n"
                    response_text += f"*Top {min(5, len(file_results))} Matching Files:*\n"
                    
                    buttons = []
                    for i, file_info in enumerate(file_results[:5], 1):
                        response_text += f"{i}. {file_info['name']}\n   📂 {file_info['path']}\n"
                        
                        # Create download button
                        file_hash = str(hash(f"{file_info['path']}_{file_info['name']}"))[-8:]
                        self.file_cache[file_hash] = {
                            'name': file_info['name'],
                            'size': file_info['size'],
                            'download_url': '',
                            'path': file_info['folder']
                        }
                        buttons.append([InlineKeyboardButton(
                            f"📄 {file_info['name'][:30]}...", 
                            callback_data=f"file:{file_hash}"
                        )])
                    
                    # Add navigation buttons
                    buttons.append([
                        InlineKeyboardButton("🔙 New Search", callback_data="ai_search"),
                        InlineKeyboardButton("📁 Browse Files", callback_data="browse:/")
                    ])
                    
                    await search_msg.edit_text(
                        response_text,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                    
                    # Schedule deletion if in group
                    if update.message.chat.type in ['group', 'supergroup']:
                        await asyncio.create_task(
                            self.schedule_message_deletion(
                                search_msg.chat.id, 
                                search_msg.message_id, 
                                user_id
                            )
                        )
                    
                except Exception as e:
                    logger.error(f"Error in AI search: {e}")
                    await search_msg.edit_text(
                        "❌ *Search Error*\n\n"
                        "Sorry, there was an error processing your search. Please try again later.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Try Again", callback_data="ai_search"),
                            InlineKeyboardButton("📁 Browse Files", callback_data="browse:/")
                        ]])
                    )
                
                # Clear AI search mode
                context.user_data['ai_search_mode'] = False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        # Check if user is in AI search mode
        if context.user_data.get('ai_search_mode'):
            await self.handle_ai_search(update, context)
        else:
            # Ignore other messages or provide help
            if update.message.text and not update.message.text.startswith('/'):
                help_msg = await update.message.reply_text(
                    "💡 *How to use this bot:*\n\n"
                    "• Use /start to see the main menu\n"
                    "• Click 'AI Search' to search files with AI\n"
                    "• Click 'Browse Files' to navigate folders\n\n"
                    "Type /start to begin!",
                    parse_mode='Markdown'
                )
                
                # Schedule deletion if in group
                if update.message.chat.type in ['group', 'supergroup']:
                    await asyncio.create_task(
                        self.schedule_message_deletion(
                            help_msg.chat.id, 
                            help_msg.message_id, 
                            update.message.from_user.id
                        )
                    )

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
        
        message += "\n*Use the buttons below to browse items*"
        
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

    async def schedule_message_deletion(self, chat_id: int, message_id: int, user_id: int):
        """Schedule a message for deletion after 5 minutes of no interaction"""
        message_key = f"{chat_id}_{message_id}"
        self.ephemeral_messages[message_key] = {
            'chat_id': chat_id,
            'message_id': message_id,
            'user_id': user_id,
            'last_interaction': datetime.now(),
            'scheduled': True
        }
        
        # Schedule deletion after 5 minutes
        await asyncio.sleep(300)  # 5 minutes
        
        # Check if message still needs deletion
        if message_key in self.ephemeral_messages:
            current_time = datetime.now()
            last_interaction = self.ephemeral_messages[message_key]['last_interaction']
            
            if (current_time - last_interaction).total_seconds() >= 300:
                try:
                    # Delete the message
                    await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    del self.ephemeral_messages[message_key]
                    logger.info(f"Deleted ephemeral message {message_id} in chat {chat_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete message {message_id}: {e}")
                    if message_key in self.ephemeral_messages:
                        del self.ephemeral_messages[message_key]
    
    def update_message_interaction(self, chat_id: int, message_id: int):
        """Update the last interaction time for a message"""
        message_key = f"{chat_id}_{message_id}"
        if message_key in self.ephemeral_messages:
            self.ephemeral_messages[message_key]['last_interaction'] = datetime.now()
    
    def check_user_query_limit(self, user_id: int) -> bool:
        """Check if user has exceeded daily query limit"""
        if user_id in self.unlimited_users:
            return True
            
        today = datetime.now().date()
        user_key = f"{user_id}_{today}"
        
        if user_key not in self.user_query_limits:
            self.user_query_limits[user_key] = 0
            
        return self.user_query_limits[user_key] < 1
    
    def increment_user_query_count(self, user_id: int):
        """Increment user's daily query count"""
        if user_id in self.unlimited_users:
            return
            
        today = datetime.now().date()
        user_key = f"{user_id}_{today}"
        
        if user_key not in self.user_query_limits:
            self.user_query_limits[user_key] = 0
            
        self.user_query_limits[user_key] += 1
    
    def add_unlimited_user(self, user_id: int):
        """Add user to unlimited access list"""
        self.unlimited_users.add(user_id)
        logger.info(f"Added user {user_id} to unlimited access list")
    
    def remove_unlimited_user(self, user_id: int):
        """Remove user from unlimited access list"""
        self.unlimited_users.discard(user_id)
        logger.info(f"Removed user {user_id} from unlimited access list")
    
    async def build_file_index(self, force_rebuild=False):
        """Build an index of all files with their paths and metadata"""
        # Check if we should use existing index
        if not force_rebuild and await self.load_file_index():
            logger.info(f"Loaded existing file index with {len(self.file_index)} files")
            return
        
        logger.info("Building file index...")
        self.file_index = {}
        
        async def index_folder(path: str = "/"):
            items = await self.get_onedrive_items(path)
            
            for item in items:
                if item['is_folder']:
                    # Recursively index subfolders
                    folder_path = f"{path.rstrip('/')}/{item['name']}" if path != "/" else item['name']
                    await index_folder(folder_path)
                else:
                    # Index file
                    file_path = f"{path.rstrip('/')}/{item['name']}" if path != "/" else item['name']
                    self.file_index[item['id']] = {
                        'name': item['name'],
                        'path': file_path,
                        'size': item['size'],
                        'folder': path,
                        'description': self.generate_file_description(item['name'], file_path)
                    }
        
        await index_folder("/")
        logger.info(f"File index built with {len(self.file_index)} files")
        
        # Save the index to file
        await self.save_file_index()
    
    async def save_file_index(self):
        """Save the file index to a JSON file"""
        try:
            with open(self.file_index_path, 'w', encoding='utf-8') as f:
                json.dump(self.file_index, f, ensure_ascii=False, indent=2)
            
            # Save timestamp
            with open(self.index_timestamp_path, 'w') as f:
                f.write(datetime.now().isoformat())
            
            logger.info(f"File index saved to {self.file_index_path}")
        except Exception as e:
            logger.error(f"Error saving file index: {e}")
    
    async def load_file_index(self):
        """Load the file index from JSON file if it exists and is recent"""
        try:
            # Check if index file exists
            if not os.path.exists(self.file_index_path):
                logger.info("No existing file index found")
                return False
            
            # Check if index is recent (less than 24 hours old)
            if os.path.exists(self.index_timestamp_path):
                with open(self.index_timestamp_path, 'r') as f:
                    timestamp_str = f.read().strip()
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age = datetime.now() - timestamp
                    
                    # If index is older than 24 hours, rebuild it
                    if age > timedelta(hours=24):
                        logger.info(f"File index is {age} old, rebuilding...")
                        return False
            
            # Load the index
            with open(self.file_index_path, 'r', encoding='utf-8') as f:
                self.file_index = json.load(f)
            
            logger.info(f"Loaded file index from {self.file_index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading file index: {e}")
            return False
    
    def generate_file_description(self, filename: str, filepath: str) -> str:
        """Generate a searchable description for a file based on its name and path"""
        # Extract file extension and folder context
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        folder_parts = filepath.split('/')
        
        description_parts = [filename.lower()]
        
        # Add folder context
        for part in folder_parts:
            if part and part.lower() not in description_parts:
                description_parts.append(part.lower())
        
        # Add file type context
        file_type_map = {
            'pdf': 'document pdf text book notes',
            'doc': 'document word text',
            'docx': 'document word text',
            'ppt': 'presentation slides powerpoint',
            'pptx': 'presentation slides powerpoint',
            'xls': 'spreadsheet excel data',
            'xlsx': 'spreadsheet excel data',
            'txt': 'text document notes',
            'py': 'python code programming script',
            'js': 'javascript code programming',
            'html': 'web html code programming',
            'css': 'stylesheet css web design',
            'jpg': 'image photo picture',
            'png': 'image picture graphic',
            'mp4': 'video movie recording',
            'mp3': 'audio music sound',
            'zip': 'archive compressed files'
        }
        
        if file_ext in file_type_map:
            description_parts.extend(file_type_map[file_ext].split())
        
        return ' '.join(description_parts)
    
    async def query_claude_ai(self, query: str, file_results: List[Dict]) -> str:
        """Query Claude AI with file search results"""
        if not self.claude_api_key:
            return "Claude AI is not configured. Please set CLAUDE_API_KEY in environment variables."
        
        try:
            from anthropic import AsyncAnthropic
            
            # Prepare context from file results
            files_context = ""
            for i, file_info in enumerate(file_results[:10], 1):  # Limit to top 10 results
                files_context += f"{i}. {file_info['name']} (Path: {file_info['path']})\n"
            
            prompt = f"""Based on the user's query: "{query}"

Here are the most relevant files found in the University OneDrive:

{files_context}

Please provide a helpful response about these files, explaining which ones are most relevant to the user's query and why. Keep the response concise and focused on the files found."""

            # Initialize Anthropic async client
            client = AsyncAnthropic(api_key=self.claude_api_key)
            
            # Create message using the official async SDK
            message = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text
                        
        except Exception as e:
            logger.error(f"Error querying Claude AI: {e}")
            return "Sorry, there was an error processing your query. Please try again later."
    
    def search_files(self, query: str, limit: int = 10) -> List[Dict]:
        """Search files using the indexed descriptions"""
        query_words = query.lower().split()
        results = []
        
        for file_id, file_info in self.file_index.items():
            score = 0
            description = file_info['description']
            
            # Calculate relevance score
            for word in query_words:
                if word in description:
                    score += description.count(word)
                    # Boost score if word appears in filename
                    if word in file_info['name'].lower():
                        score += 5
                    # Boost score if word appears in immediate folder
                    if word in file_info['folder'].lower():
                        score += 2
            
            if score > 0:
                results.append({
                    'score': score,
                    'file_id': file_id,
                    **file_info
                })
        
        # Sort by relevance score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to manage unlimited users"""
        # Simple admin check - you can enhance this with proper admin user IDs
        admin_users = [123456789]  # Replace with actual admin user IDs
        
        if update.message.from_user.id not in admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "*Admin Commands:*\n\n"
                "`/admin add_unlimited <user_id>` - Add unlimited access\n"
                "`/admin remove_unlimited <user_id>` - Remove unlimited access\n"
                "`/admin list_unlimited` - List unlimited users\n"
                "`/admin rebuild_index` - Rebuild file index",
                parse_mode='Markdown'
            )
            return
        
        command = context.args[0].lower()
        
        if command == "add_unlimited" and len(context.args) > 1:
            try:
                user_id = int(context.args[1])
                self.add_unlimited_user(user_id)
                await update.message.reply_text(f"✅ Added user {user_id} to unlimited access list.")
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID.")
                
        elif command == "remove_unlimited" and len(context.args) > 1:
            try:
                user_id = int(context.args[1])
                self.remove_unlimited_user(user_id)
                await update.message.reply_text(f"✅ Removed user {user_id} from unlimited access list.")
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID.")
                
        elif command == "list_unlimited":
            if self.unlimited_users:
                users_list = "\n".join([f"• {user_id}" for user_id in self.unlimited_users])
                await update.message.reply_text(f"*Unlimited Access Users:*\n\n{users_list}", parse_mode='Markdown')
            else:
                await update.message.reply_text("No users have unlimited access.")
                
        elif command == "rebuild_index":
            await update.message.reply_text("🔄 Rebuilding file index...")
            await self.build_file_index(force_rebuild=True)
            await update.message.reply_text(f"✅ File index rebuilt with {len(self.file_index)} files.")
            
        else:
            await update.message.reply_text("❌ Unknown admin command.")

# Global bot instance
bot_instance = None

async def post_init(application: Application) -> None:
    """Post initialization hook"""
    global bot_instance
    logger.info("Starting post-initialization...")
    
    # Store application reference for message deletion
    bot_instance.application = application
    
    # Test authentication and cache users
    success = await bot_instance.test_and_cache_users()
    if success:
        print("✅ OneDrive connected successfully!")
        print(f"👤 Default user: {bot_instance.users_cache[bot_instance.default_user_id]['name']}")
        
        # Build file index
        print("📂 Initializing file index...")
        await bot_instance.build_file_index()
        print("✅ File index ready!")
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
        application.add_handler(CommandHandler("admin", bot_instance.admin_command))
        application.add_handler(CallbackQueryHandler(bot_instance.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message))
        
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
