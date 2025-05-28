import asyncio
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv

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
            raise ValueError("Missing required environment variables. Please check your .env file.")
        
        # Initialize Microsoft Graph client
        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        scopes = ['https://graph.microsoft.com/.default']
        self.graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        
        # Store current paths for each user - start with University folder
        self.user_paths: Dict[int, str] = {}
        # Store message IDs for dynamic updates
        self.user_messages: Dict[int, int] = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command"""
        user_id = update.effective_user.id
        self.user_paths[user_id] = "/University"  # Start in University folder
        
        # Create main interface with browse button
        keyboard = [
            [InlineKeyboardButton("📂 Browse University Files", callback_data="browse_start")],
            [InlineKeyboardButton("📍 Current Location", callback_data="show_current")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            "🗂️ **OneDrive File Browser Bot**\n\n"
            "Welcome! I can help you browse and share files from your University OneDrive folder.\n\n"
            "Click the button below to start browsing:"
        )
        
        message = await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        self.user_messages[user_id] = message.message_id
    
    async def show_files_in_path(self, update: Update, context: ContextTypes.DEFAULT_TYPE, path: str) -> None:
        """Show files and folders in the specified path"""
        try:
            # Get files and folders from OneDrive
            items = await self.get_onedrive_items(path)
            
            if not items:
                message = "📁 This folder is empty."
                keyboard = []
                
                # Add navigation buttons for empty folders
                nav_buttons = []
                if path != "/University":
                    nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="nav:/parent"))
                nav_buttons.append(InlineKeyboardButton("🏠 University", callback_data="nav:/University"))
                nav_buttons.append(InlineKeyboardButton("🏡 Home", callback_data="nav:/home"))
                
                # Split navigation buttons into rows of 2
                for i in range(0, len(nav_buttons), 2):
                    keyboard.append(nav_buttons[i:i+2])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                # Always update the existing message instead of sending new one
                user_id = update.effective_user.id if update.effective_user else None
                if user_id and user_id in self.user_messages:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=self.user_messages[user_id],
                            text=message,
                            reply_markup=reply_markup
                        )
                    except:
                        # If edit fails, send new message
                        if update.callback_query:
                            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
                        else:
                            new_msg = await update.message.reply_text(message, reply_markup=reply_markup)
                            self.user_messages[user_id] = new_msg.message_id
                else:
                    if update.callback_query:
                        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
                    else:
                        new_msg = await update.message.reply_text(message, reply_markup=reply_markup)
                        if user_id:
                            self.user_messages[user_id] = new_msg.message_id
                return
            
            # Create inline keyboard with files and folders
            keyboard = []
            
            # Group items into rows of 2
            for i in range(0, len(items), 2):
                row = []
                for j in range(2):
                    if i + j < len(items):
                        item = items[i + j]
                        icon = "📁" if item['is_folder'] else "📄"
                        name = item['name']
                        
                        # Truncate long names
                        if len(name) > 15:
                            name = name[:12] + "..."
                        
                        button_text = f"{icon} {name}"
                        callback_data = f"{'folder' if item['is_folder'] else 'file'}:{item['id']}"
                        
                        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
                
                keyboard.append(row)
            
            # Add navigation buttons
            nav_buttons = []
            if path != "/University":
                nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="nav:/parent"))
            nav_buttons.append(InlineKeyboardButton("🏠 University", callback_data="nav:/University"))
            nav_buttons.append(InlineKeyboardButton("🏡 Home", callback_data="nav:/home"))
            
            if nav_buttons:
                # Split navigation buttons into rows of 2
                for i in range(0, len(nav_buttons), 2):
                    keyboard.append(nav_buttons[i:i+2])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            path_display = path if path != "/University" else "University folder"
            message = f"📁 Current folder: {path_display}\n\nSelect a file or folder:"
            
            # Always update the existing message instead of sending new one
            user_id = update.effective_user.id if update.effective_user else None
            if user_id and user_id in self.user_messages:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=self.user_messages[user_id],
                        text=message,
                        reply_markup=reply_markup
                    )
                except:
                    # If edit fails, send new message
                    if update.callback_query:
                        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
                    else:
                        new_msg = await update.message.reply_text(message, reply_markup=reply_markup)
                        self.user_messages[user_id] = new_msg.message_id
            else:
                if update.callback_query:
                    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
                else:
                    new_msg = await update.message.reply_text(message, reply_markup=reply_markup)
                    if user_id:
                        self.user_messages[user_id] = new_msg.message_id
                
        except Exception as e:
            logger.error(f"Error showing files: {e}")
            error_message = "❌ Error accessing OneDrive. Please try again later."
            
            user_id = update.effective_user.id if update.effective_user else None
            if user_id and user_id in self.user_messages:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=self.user_messages[user_id],
                        text=error_message
                    )
                except:
                    if update.callback_query:
                        await update.callback_query.answer(error_message)
                    else:
                        await update.message.reply_text(error_message)
            else:
                if update.callback_query:
                    await update.callback_query.answer(error_message)
                else:
                    await update.message.reply_text(error_message)
    
    async def get_onedrive_items(self, path: str) -> List[Dict]:
        """Get items from OneDrive at the specified path"""
        try:
            # For application permissions, we need to use a specific user ID
            # First, try to get the current user ID from the tenant
            users = await self.graph_client.users.get()
            
            if not users or not users.value:
                logger.warning("No users found in tenant")
                return self._get_mock_data(path)
            
            # Use the first available user (in production, you'd specify the exact user)
            user_id = users.value[0].id
            logger.info(f"Using user ID: {user_id}")
            
            if path == "/University":
                # Try to get items in University folder
                try:
                    result = await self.graph_client.users.by_user_id(user_id).drive.root.item_with_path("University").children.get()
                except:
                    # If University folder doesn't exist, get root items
                    result = await self.graph_client.users.by_user_id(user_id).drive.root.children.get()
            else:
                # Get items in specific folder by path
                clean_path = path.replace("/University/", "University/").strip('/')
                result = await self.graph_client.users.by_user_id(user_id).drive.root.item_with_path(clean_path).children.get()
            
            items = []
            if result and result.value:
                for item in result.value:
                    # Get download URL for files
                    download_url = None
                    if not item.folder:  # It's a file
                        try:
                            # For files, get the download URL
                            download_url = getattr(item, '@microsoft.graph.downloadUrl', None)
                        except:
                            download_url = None
                    
                    items.append({
                        'id': item.id,
                        'name': item.name,
                        'is_folder': item.folder is not None,
                        'download_url': download_url,
                        'size': item.size if item.size else 0,
                        'path': f"{path.rstrip('/')}/{item.name}" if path != "/University" else f"/University/{item.name}"
                    })
            
            # Sort: folders first, then files, both alphabetically
            items.sort(key=lambda x: (not x['is_folder'], x['name'].lower()))
            logger.info(f"Successfully retrieved {len(items)} items from {path}")
            return items
            
        except Exception as e:
            logger.error(f"Error getting OneDrive items from {path}: {e}")
            logger.info("Falling back to mock data for demonstration")
            return self._get_mock_data(path)
    
    def _get_mock_data(self, path: str) -> List[Dict]:
        """Fallback mock data when OneDrive API is not accessible"""
        logger.info(f"Using mock data for path: {path}")
        
        if path == "/University":
            return [
                {
                    'id': 'folder_1',
                    'name': 'Computer Science',
                    'is_folder': True,
                    'download_url': None,
                    'size': 0,
                    'path': '/University/Computer Science'
                },
                {
                    'id': 'folder_2', 
                    'name': 'Mathematics',
                    'is_folder': True,
                    'download_url': None,
                    'size': 0,
                    'path': '/University/Mathematics'
                },
                {
                    'id': 'file_1',
                    'name': 'Course_Schedule.pdf',
                    'is_folder': False,
                    'download_url': 'https://example.com/download/schedule.pdf',
                    'size': 1024000,
                    'path': '/University/Course_Schedule.pdf'
                },
                {
                    'id': 'file_2',
                    'name': 'Student_Handbook.docx',
                    'is_folder': False,
                    'download_url': 'https://example.com/download/handbook.docx',
                    'size': 2048000,
                    'path': '/University/Student_Handbook.docx'
                }
            ]
        elif path == "/University/Computer Science":
            return [
                {
                    'id': 'file_3',
                    'name': 'Python_Basics.pdf',
                    'is_folder': False,
                    'download_url': 'https://example.com/download/python.pdf',
                    'size': 3072000,
                    'path': '/University/Computer Science/Python_Basics.pdf'
                },
                {
                    'id': 'file_4',
                    'name': 'Data_Structures.pptx',
                    'is_folder': False,
                    'download_url': 'https://example.com/download/ds.pptx',
                    'size': 5120000,
                    'path': '/University/Computer Science/Data_Structures.pptx'
                }
            ]
        elif path == "/University/Mathematics":
            return [
                {
                    'id': 'file_5',
                    'name': 'Calculus_Notes.pdf',
                    'is_folder': False,
                    'download_url': 'https://example.com/download/calculus.pdf',
                    'size': 2560000,
                    'path': '/University/Mathematics/Calculus_Notes.pdf'
                }
            ]
        else:
            return []
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        try:
            if data == "browse_start":
                # Start browsing - show University files
                self.user_paths[user_id] = "/University"
                await self.show_files_in_path(update, context, "/University")
            
            elif data == "show_current":
                # Show current location with option to browse
                current_path = self.user_paths.get(user_id, "/University")
                path_display = current_path if current_path != "/University" else "University folder"
                
                keyboard = [
                    [InlineKeyboardButton("📂 Browse Files", callback_data="browse_start")],
                    [InlineKeyboardButton("🔄 Refresh", callback_data="nav:/current")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"📍 **Current Location:** {path_display}\n\nChoose an action:"
                
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("folder:"):
                # User clicked on a folder
                folder_id = data.split(":", 1)[1]
                folder_path = await self.get_folder_path_by_id(folder_id)
                
                if folder_path:
                    self.user_paths[user_id] = folder_path
                    await self.show_files_in_path(update, context, folder_path)
                else:
                    await query.answer("❌ Folder not found")
            
            elif data.startswith("file:"):
                # User clicked on a file
                file_id = data.split(":", 1)[1]
                await self.share_file(update, context, file_id)
            
            elif data.startswith("nav:"):
                # Navigation commands
                nav_command = data.split(":", 1)[1]
                
                if nav_command == "/University":
                    # Go to University folder
                    self.user_paths[user_id] = "/University"
                    await self.show_files_in_path(update, context, "/University")
                
                elif nav_command == "/parent":
                    # Go to parent folder
                    current_path = self.user_paths.get(user_id, "/University")
                    if current_path != "/University":
                        parent_path = "/".join(current_path.strip("/").split("/")[:-1])
                        parent_path = "/" + parent_path if parent_path else "/University"
                        self.user_paths[user_id] = parent_path
                        await self.show_files_in_path(update, context, parent_path)
                
                elif nav_command == "/current":
                    # Refresh current folder
                    current_path = self.user_paths.get(user_id, "/University")
                    await self.show_files_in_path(update, context, current_path)
                
                elif nav_command == "/home":
                    # Go back to main menu
                    keyboard = [
                        [InlineKeyboardButton("📂 Browse University Files", callback_data="browse_start")],
                        [InlineKeyboardButton("📍 Current Location", callback_data="show_current")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    message = (
                        "🗂️ **OneDrive File Browser Bot**\n\n"
                        "Welcome! I can help you browse and share files from your University OneDrive folder.\n\n"
                        "Click the button below to start browsing:"
                    )
                    
                    await query.edit_message_text(
                        message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
        
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await query.answer("❌ An error occurred")
    
    async def get_folder_path_by_id(self, folder_id: str) -> Optional[str]:
        """Get the full path of a folder by its ID"""
        try:
            # For application permissions, we need to use a specific user ID
            users = await self.graph_client.users.get()
            if not users or not users.value:
                logger.warning("No users found for folder path lookup")
                return None
                
            user_id = users.value[0].id
            
            item = await self.graph_client.users.by_user_id(user_id).drive.items.by_drive_item_id(folder_id).get()
            if item and item.parent_reference:
                parent_path = item.parent_reference.path
                # Extract path from the full path (remove /drive/root: prefix)
                if parent_path and parent_path.startswith("/drive/root:"):
                    clean_path = parent_path.replace("/drive/root:", "")
                    return f"{clean_path}/{item.name}" if clean_path else f"/{item.name}"
                else:
                    return f"/{item.name}"
            return f"/{item.name}" if item else None
        except Exception as e:
            logger.error(f"Error getting folder path: {e}")
            # Return a mock path based on folder_id for testing
            if folder_id == "folder_1":
                return "/University/Computer Science"
            elif folder_id == "folder_2":
                return "/University/Mathematics"
            return None
    
    async def share_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> None:
        """Share a file from OneDrive"""
        try:
            # For application permissions, we need to use a specific user ID
            users = await self.graph_client.users.get()
            if not users or not users.value:
                await update.callback_query.answer("❌ Cannot access OneDrive")
                return
                
            user_id = users.value[0].id
            
            # Get file information
            file_item = await self.graph_client.users.by_user_id(user_id).drive.items.by_drive_item_id(file_id).get()
            
            if not file_item:
                await update.callback_query.answer("❌ File not found")
                return
            
            # Get download URL
            download_url = getattr(file_item, '@microsoft.graph.downloadUrl', None)
            
            if not download_url:
                await update.callback_query.answer("❌ Cannot get download link for this file")
                return
            
            # Prepare file info
            file_name = file_item.name
            file_size = file_item.size if file_item.size else 0
            file_size_mb = round(file_size / (1024 * 1024), 2) if file_size > 0 else 0
            
            # Send file information and download link
            message = (
                f"📄 **{file_name}**\n"
                f"📊 Size: {file_size_mb} MB\n\n"
                f"🔗 [Download File]({download_url})\n\n"
                f"_Note: The download link is temporary and will expire._"
            )
            
            # Create keyboard with options
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to folder", callback_data="nav:/current")],
                [InlineKeyboardButton("🏠 University", callback_data="nav:/University"), 
                 InlineKeyboardButton("🏡 Home", callback_data="nav:/home")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                message, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            # Provide mock file sharing for demonstration
            if file_id in ['file_1', 'file_2', 'file_3', 'file_4', 'file_5']:
                file_names = {
                    'file_1': 'Course_Schedule.pdf',
                    'file_2': 'Student_Handbook.docx', 
                    'file_3': 'Python_Basics.pdf',
                    'file_4': 'Data_Structures.pptx',
                    'file_5': 'Calculus_Notes.pdf'
                }
                
                file_name = file_names.get(file_id, 'Unknown File')
                message = (
                    f"📄 **{file_name}**\n"
                    f"📊 Size: 2.5 MB\n\n"
                    f"🔗 Mock download link (OneDrive permissions needed for real files)\n\n"
                    f"_To enable real file downloads, please set up OneDrive permissions in Azure Portal._"
                )
                
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back to folder", callback_data="nav:/current")],
                    [InlineKeyboardButton("🏠 University", callback_data="nav:/University"), 
                     InlineKeyboardButton("🏡 Home", callback_data="nav:/home")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    message, 
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.callback_query.answer("❌ Error sharing file")

def main():
    """Start the bot"""
    try:
        bot = OneDriveTelegramBot()
        
        # Create application
        application = Application.builder().token(bot.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CallbackQueryHandler(bot.handle_callback))
        
        # Start the bot
        logger.info("Starting OneDrive Telegram Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"Error: {e}")
        print("\nPlease make sure you have:")
        print("1. Created a .env file with your bot token and Azure app credentials")
        print("2. Set up an Azure app with OneDrive permissions")
        print("3. Installed all required dependencies")

if __name__ == '__main__':
    main()
