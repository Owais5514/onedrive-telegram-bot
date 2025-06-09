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
from query_logger import log_user_query, query_logger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Try to import AI handler (optional)
try:
    from ai_handler_client import AIHandlerClient
    AI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI features not available: {e}")
    AI_AVAILABLE = False
    AIHandler = None

class OneDriveBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_USER_ID', '0'))
        
        # Initialize query logger - uses global instance
        logger.info("Query logger initialized")
        
        # Initialize OneDrive indexer
        self.indexer = OneDriveIndexer()
        
        # Initialize AI handler (optional)
        self.ai_handler = None
        if AI_AVAILABLE:
            try:
                self.ai_handler = AIHandlerClient(server_url="http://localhost:8001")
                # Start loading model in background
                # AI handler client doesn't need background loading - server handles it
                logger.info("AI handler initialized - using external model server")
            except Exception as e:
                logger.warning(f"Failed to initialize AI handler: {e}")
                self.ai_handler = None
        
        # Callback data mapping to handle long file names (max 64 bytes for Telegram)
        self.callback_map = {}
        self.callback_counter = 0
        
        # File paths
        self.users_file = 'unlimited_users.json'
        
        # Cache
        self.unlimited_users = set()
        
        # Shutdown flag
        self.shutdown_requested = False
        
        # Track bot startup time for pending message handling
        self.startup_time = None
        
        # AI search state
        self.waiting_for_ai_query = set()  # Track users waiting to input AI search query
        
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
        
        # Add AI search button if available
        if self.ai_handler:
            keyboard.append([InlineKeyboardButton("🤖 AI Search", callback_data="ai_search")])
        
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
            # Log root browsing activity
            try:
                user_id = query.from_user.id
                username = query.from_user.username or f"user_{user_id}"
                await log_user_query(user_id, username, "Started browsing files from root", "browse_start")
            except Exception as e:
                logger.warning(f"Failed to log browse start activity: {e}")
            await self.show_folder_contents(query, "root")
        elif data == "ai_search":
            # Log AI search start
            try:
                user_id = query.from_user.id
                username = query.from_user.username or f"user_{user_id}"
                await log_user_query(user_id, username, "Started AI search session", "ai_search_start")
            except Exception as e:
                logger.warning(f"Failed to log AI search start activity: {e}")
            await self.handle_ai_search_button(query)
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

    async def handle_ai_search_button(self, query):
        """Handle AI search button click"""
        if not self.ai_handler:
            await query.edit_message_text(
                "❌ AI search is not available.\n"
                "Please contact admin to enable AI features."
            )
            return
        
        # Add user to waiting list
        user_id = query.from_user.id
        self.waiting_for_ai_query.add(user_id)
        
        # Check model status for user feedback
        status_text = ""
        if await self.ai_handler.is_server_ready():
            status_text = "🤖 AI model is ready for advanced search!\n\n"
        else:
            status_text = "🔄 AI model server is starting up...\n(Search will use smart fallback for now)\n\n"
        
        await query.edit_message_text(
            f"{status_text}"
            "Please type your search query in natural language.\n\n"
            "Examples:\n"
            "• \"Find math lectures from week 3\"\n"
            "• \"EEE2203 assignment solutions\"\n"
            "• \"CE1201 lab reports\"\n"
            "• \"Physics quiz questions\"\n\n"
            "Type your search query now:"
        )

    async def handle_ai_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI search text messages"""
        user_id = update.effective_user.id
        
        # Check if user is waiting for AI query
        if user_id not in self.waiting_for_ai_query:
            return  # Not waiting for AI query, let other handlers process
        
        # Remove user from waiting list
        self.waiting_for_ai_query.discard(user_id)
        
        if not self.ai_handler:
            await update.message.reply_text(
                "❌ AI search is not available.\n"
                "Please contact admin to enable AI features."
            )
            return
        
        user_query = update.message.text.strip()
        username = update.effective_user.username or f"user_{user_id}"
        
        # Log the AI search query
        await log_user_query(user_id, username, user_query, "ai_search")
        
        # Send processing message
        processing_msg = await update.message.reply_text("🤖 Processing your query with AI...")
        
        try:
            # Get all file paths for search
            all_file_paths = []
            for path, items in self.indexer.file_index.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and item.get('type') == 'file':
                            file_path = item.get('path', f"{path}/{item.get('name', '')}")
                            all_file_paths.append(file_path)
            
            # Process with enhanced AI search
            explanation, search_results = await self.ai_handler.enhanced_search(user_query, all_file_paths)
            
            # Enrich search results with file details from indexer
            enriched_results = []
            for result in search_results:
                result_path = result.get('path', '')
                
                # Find file details from indexer
                file_details = None
                for folder_path, folder_data in self.indexer.file_index.items():
                    if isinstance(folder_data, list):
                        for item in folder_data:
                            if isinstance(item, dict) and item.get('path') == result_path:
                                file_details = item
                                break
                    if file_details:
                        break
                
                # Enrich result with file details
                enriched_result = result.copy()
                if file_details:
                    enriched_result.update({
                        'name': file_details.get('name', os.path.basename(result_path) or 'Unknown'),
                        'size': file_details.get('size', 0),
                        'type': file_details.get('type', 'file'),
                        'relevance_score': result.get('score', 0)
                    })
                else:
                    # Fallback values
                    enriched_result.update({
                        'name': os.path.basename(result_path) or 'Unknown',
                        'size': 0,
                        'type': 'file' if result.get('type') != 'folder' else 'folder',
                        'relevance_score': result.get('score', 0)
                    })
                
                enriched_results.append(enriched_result)
            
            # Separate files and folders from enriched results
            file_results = [r for r in enriched_results if r.get('type') != 'folder']
            folder_results = [r for r in enriched_results if r.get('type') == 'folder']
            
            # Format results
            if file_results or folder_results:
                results_text = f"🤖 **AI Search Results**\n{explanation}\n\n"
                
                # Log the AI search results for tracking
                result_summary = f"AI search '{user_query}' returned {len(file_results)} files and {len(folder_results)} folders"
                await log_user_query(user_id, username, result_summary, "ai_search_result")
                
                # Show folder recommendations first
                if folder_results:
                    results_text += f"📁 **Recommended Folders** ({len(folder_results)}):\n"
                    for i, folder in enumerate(folder_results[:5], 1):
                        results_text += f"{i}. 📂 {folder.get('name', os.path.basename(folder.get('path', '')) or 'Unknown')}\n"
                        results_text += f"   📂 Path: {folder.get('path', 'Unknown')}\n"
                        results_text += f"   🎯 Score: {folder.get('score', 0):.2f}\n\n"
                
                # Show file results
                if file_results:
                    results_text += f"📄 **File Results** ({len(file_results)} found):\n"
                    for i, result in enumerate(file_results[:8], 1):  # Show top 8 files
                        size_mb = result.get('size', 0) / (1024 * 1024) if result.get('size', 0) > 0 else 0
                        results_text += f"{i}. 📄 {result.get('name', 'Unknown')}\n"
                        results_text += f"   📂 Path: {result.get('path', 'Unknown')}\n"
                        results_text += f"   💾 Size: {size_mb:.1f}MB | 🎯 Score: {result.get('relevance_score', 0):.2f}\n\n"
                    
                    if len(file_results) > 8:
                        results_text += f"... and {len(file_results) - 8} more results"
                
                # Create buttons for top results
                keyboard = []
                
                # Add folder buttons
                for i, folder in enumerate(folder_results[:3]):
                    folder_path = folder.get('path', '')
                    folder_name = os.path.basename(folder_path) or folder_path
                    callback_data = self.create_callback_data("folder", folder_path)
                    keyboard.append([InlineKeyboardButton(
                        f"📂 Open: {folder_name[:25]}...", 
                        callback_data=callback_data
                    )])
                
                # Add file download buttons
                for i, result in enumerate(search_results[:3]):
                    # Use path as identifier and try to find the actual file details
                    result_path = result.get('path', f'result_{i}')
                    result_name = os.path.basename(result_path) if result_path else f"File {i+1}"
                    
                    # Try to find the actual file in the index to get proper id
                    file_id = f"ai_search_{i}"  # Fallback id
                    for path, items in self.indexer.file_index.items():
                        if isinstance(items, list):
                            for item in items:
                                if item.get('path') == result_path or (path + '/' + item.get('name', '')) == result_path:
                                    file_id = item.get('id', f"ai_search_{i}")
                                    break
                    
                    file_info = f"{file_id}_{result_name}"
                    callback_data = self.create_callback_data("file", file_info)
                    keyboard.append([InlineKeyboardButton(
                        f"📥 Download: {result_name[:20]}...", 
                        callback_data=callback_data
                    )])
                
                keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(results_text, reply_markup=reply_markup)
            else:
                await processing_msg.edit_text(
                    f"{explanation}\n\n"
                    "❌ No files found matching your query.\n\n"
                    "Try:\n"
                    "• Using different keywords\n"
                    "• Being more specific about course codes\n"
                    "• Checking file types (lecture, quiz, assignment)\n\n"
                    "🏠 Return to main menu",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                    ]])
                )
                
        except Exception as e:
            logger.error(f"Error in AI search: {e}")
            await processing_msg.edit_text(
                f"❌ Error processing AI search: {e}\n\n"
                "Please try again with a different query.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]])
            )

    def search_files_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search files using keywords generated by AI"""
        if not keywords:
            return []
        
        results = []
        
        # Get all files from index
        all_files = self.indexer.search_files("*")  # Get all files
        
        # Score and filter files based on keywords
        for file_info in all_files:
            score = 0
            file_name_lower = file_info['name'].lower()
            file_path_lower = file_info['path'].lower()
            
            # Calculate relevance score
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                # Exact match in filename gets highest score
                if keyword_lower in file_name_lower:
                    score += 10
                
                # Partial match in filename
                elif any(keyword_lower in word for word in file_name_lower.split()):
                    score += 5
                
                # Match in path
                if keyword_lower in file_path_lower:
                    score += 3
            
            # Only include files with some relevance
            if score > 0:
                file_info['relevance_score'] = score
                results.append(file_info)
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return results

    def enhanced_search_files_by_keywords(self, keywords: List[str], user_query: str) -> List[Dict]:
        """Hybrid search: semantic, keyword, and fuzzy matching for files with better scoring"""
        if not keywords:
            return []
        results = []
        all_files = self.indexer.search_files("*")
        user_query_lower = user_query.lower()
        for file_info in all_files:
            score = 0
            file_name_lower = file_info['name'].lower()
            file_path_lower = file_info['path'].lower()
            # Keyword and partial matches
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in file_name_lower:
                    score += 12
                elif any(keyword_lower in word for word in file_name_lower.split()):
                    score += 6
                if keyword_lower in file_path_lower:
                    score += 4
            # Fuzzy match (sequence similarity)
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, user_query_lower, file_name_lower).ratio()
            if similarity > 0.5:
                score += int(similarity * 10)
            # Bonus for subject or course code in path
            for keyword in keywords:
                if len(keyword) > 3 and keyword.lower() in file_path_lower:
                    score += 2
            if score > 0:
                file_info['relevance_score'] = score
                results.append(file_info)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results
    
    def calculate_file_relevance_score(self, file_info: Dict, keywords: List[str], user_query: str) -> int:
        """Calculate enhanced relevance score for a file"""
        score = 0
        file_name_lower = file_info['name'].lower()
        file_path_lower = file_info['path'].lower()
        query_lower = user_query.lower()
        
        # 1. Exact query phrase match (highest score)
        if query_lower in file_name_lower:
            score += 50
        elif query_lower in file_path_lower:
            score += 30
        
        # 2. Individual word matches in query
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 2:  # Skip short words
                if word in file_name_lower:
                    score += 15
                elif word in file_path_lower:
                    score += 8
        
        # 3. Keyword matches with different weights
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Exact match in filename gets highest score
            if keyword_lower == file_name_lower or keyword_lower in file_name_lower.split():
                score += 20
            # Partial match in filename
            elif keyword_lower in file_name_lower:
                score += 12
            # Match in path
            elif keyword_lower in file_path_lower:
                score += 6
            
            # Fuzzy matching for typos and variations
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, keyword_lower, file_name_lower).ratio()
            if similarity > 0.7:  # 70% similarity
                score += int(similarity * 10)
        
        # 4. File type boost
        file_extension = file_info['name'].split('.')[-1].lower() if '.' in file_info['name'] else ''
        if file_extension in ['pdf', 'doc', 'docx', 'ppt', 'pptx']:
            score += 5
        
        # 5. Course code detection bonus
        import re
        course_patterns = [r'[A-Z]{2,4}\d{4}', r'[A-Z]{3}\d{3}', r'[A-Z]{4}\d{3}']
        for pattern in course_patterns:
            if re.search(pattern, file_name_lower.upper()) or re.search(pattern, query_lower.upper()):
                score += 15
        
        # 6. Recent files bonus (based on modification date)
        try:
            from datetime import datetime, timedelta
            if 'modified' in file_info:
                modified_date = datetime.fromisoformat(file_info['modified'].replace('Z', '+00:00'))
                days_old = (datetime.now(modified_date.tzinfo) - modified_date).days
                if days_old < 30:  # Recent files get bonus
                    score += max(5 - (days_old // 7), 1)  # 5 points for this week, decreasing
        except:
            pass  # Ignore date parsing errors
        
        return score

    async def show_folder_contents(self, query, path: str):
        """Show folder contents with navigation buttons"""
        contents = self.get_folder_contents(path)
        
        # Log folder browsing activity
        try:
            user_id = query.from_user.id
            username = query.from_user.username or f"user_{user_id}"
            folder_name = path.split("/")[-1] if path != "root" else "Sharing"
            browse_action = f"Browsed folder: {folder_name} (path: {path})"
            await log_user_query(user_id, username, browse_action, "browse_folder")
        except Exception as e:
            logger.warning(f"Failed to log folder browse activity: {e}")
        
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
        
        # Log file interaction
        try:
            user_id = query.from_user.id
            username = query.from_user.username or f"user_{user_id}"
            file_action = f"Viewed file details: {file_name} (ID: {file_id})"
            await log_user_query(user_id, username, file_action, "file_view")
        except Exception as e:
            logger.warning(f"Failed to log file view activity: {e}")
        
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
            
            # Log download attempt
            try:
                user_id = query.from_user.id
                username = query.from_user.username or f"user_{user_id}"
                download_action = f"Download attempt: {file_name} ({file_size_mb:.1f}MB) from {current_folder_path}"
                await log_user_query(user_id, username, download_action, "download_attempt")
            except Exception as e:
                logger.warning(f"Failed to log download attempt: {e}")
            
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
                
                # Log successful download
                try:
                    success_action = f"Successfully downloaded: {file_name} ({file_size_mb:.1f}MB) from {current_folder_path}"
                    await log_user_query(user_id, username, success_action, "download_success")
                except Exception as e:
                    logger.warning(f"Failed to log download success: {e}")
                    
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
                
                # Log download failure
                try:
                    failure_action = f"Download failed: {file_name} ({file_size_mb:.1f}MB) from {current_folder_path}"
                    await log_user_query(user_id, username, failure_action, "download_failure")
                except Exception as e:
                    logger.warning(f"Failed to log download failure: {e}")
                    
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
                
                # Log large file access
                try:
                    user_id = query.from_user.id
                    username = query.from_user.username or f"user_{user_id}"
                    download_action = f"Accessed large file link: {file_name} ({file_size_mb:.1f}MB) from {current_folder_path}"
                    await log_user_query(user_id, username, download_action, "large_file_link")
                except Exception as e:
                    logger.warning(f"Failed to log large file access: {e}")
                    
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
            # Set shutdown flag and stop application
            self.shutdown_requested = True
            await self.application.stop()
            await self.application.shutdown()

    async def show_main_menu(self, query):
        """Show the main menu"""
        keyboard = [
            [InlineKeyboardButton("📁 Browse Files", callback_data="browse_root")]
        ]
        
        # Add AI search button if available
        if self.ai_handler:
            keyboard.append([InlineKeyboardButton("🤖 AI Search", callback_data="ai_search")])
        
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
            "🎓 OneDrive Sharing Bot\n\n"
            "📂 Browse and download sharing files\n"
        )
        
        if self.ai_handler:
            welcome_text += "🤖 AI-powered search available\n"
        
        if query.from_user.id == self.admin_id:
            welcome_text += "⚙️ Admin controls available\n"
            
        welcome_text += "\nSelect an option below:"
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - show bot menu"""
        keyboard = [
            [InlineKeyboardButton("📁 Browse Files", callback_data="browse_root")]
        ]
        
        # Add AI search button if available
        if self.ai_handler:
            keyboard.append([InlineKeyboardButton("🤖 AI Search", callback_data="ai_search")])
        
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
            "• /ai_search - AI-powered file search\n"
            "• /help - Show this help message\n"
            "• /about - About this bot\n"
            "• /privacy - Privacy policy\n"
            "• /admin - Admin panel (admin only)\n\n"
            "🗂️ Navigation & Usage:\n"
            "• 📁 Browse Files - Explore sharing folders\n"
            "• 🤖 AI Search - Natural language file search\n"
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

    async def ai_search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai_search command"""
        if not self.ai_handler:
            await update.message.reply_text(
                "❌ AI search is not available.\n"
                "Please contact admin to enable AI features."
            )
            return
        
        # Add user to waiting list
        user_id = update.effective_user.id
        self.waiting_for_ai_query.add(user_id)
        
        await update.message.reply_text(
            "🤖 AI Search Ready!\n\n"
            "Please type your search query in natural language.\n\n"
            "Examples:\n"
            "• \"Find math lectures from week 3\"\n"
            "• \"EEE2203 assignment solutions\"\n"
            "• \"CE1201 lab reports\"\n"
            "• \"Physics quiz questions\"\n\n"
            "Type your search query now:"
        )

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
        self.application.add_handler(CommandHandler("ai_search", self.ai_search_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        self.application.add_handler(CommandHandler("privacy", self.privacy_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add message handler for AI search queries (must be after command handlers)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_ai_search_query
        ))
        
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
                    
                    # Clean up AI resources
                    if self.ai_handler:
                        self.ai_handler.cleanup()
                    
                    # Stop periodic query logging commits and do final commit
                    query_logger.stop_periodic_commits()
                    query_logger.final_commit_and_push()
                    
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
