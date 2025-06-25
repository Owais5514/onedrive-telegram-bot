#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Render Web Service
Optimized for Render.com deployment with webhook support
"""

import os
import sys
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bot import OneDriveBot
from database import db_manager
from aiohttp import web
from aiohttp.web_request import Request

# Load environment variables
load_dotenv()

# Configure logging for Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for Render
    ]
)
logger = logging.getLogger(__name__)


class OneDriveBotRender(OneDriveBot):
    """OneDrive Bot optimized for Render deployment"""
    
    def __init__(self, onedrive_folders=None, folder_config=None):
        super().__init__(onedrive_folders, folder_config)
        
        # Render-specific configuration
        self.port = int(os.getenv('PORT', '10000'))  # Render assigns PORT env var
        self.host = '0.0.0.0'  # Required for Render
        
        # Webhook configuration - Render provides HTTPS automatically
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        custom_webhook_url = os.getenv('WEBHOOK_URL')
        
        if custom_webhook_url:
            self.webhook_url = custom_webhook_url
        elif render_url:
            self.webhook_url = render_url
        else:
            # Fallback - this will be set by Render automatically
            service_name = os.getenv('RENDER_SERVICE_NAME', 'onedrive-telegram-bot')
            self.webhook_url = f"https://{service_name}.onrender.com"
        
        self.webhook_path = os.getenv('WEBHOOK_PATH', '/webhook')
        
        # No SSL configuration needed - Render handles HTTPS automatically
        self.web_app = None
        self.application = None  # Initialize to None, will be set up later
        
        # Keep-alive mechanism for long-running operations
        self.keepalive_enabled = True
        self.last_activity = datetime.now(timezone.utc)
        
        logger.info(f"Render Bot initialized - Port: {self.port}")
        logger.info(f"Webhook URL: {self.webhook_url}{self.webhook_path}")
    
    async def setup_application(self):
        """Set up the Telegram application (separate from parent's setup_bot method)"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            return False
            
        try:
            # Initialize indexer first (use async version for better performance)
            logger.info("Building OneDrive file index (async)...")
            
            # Use async indexing if available, otherwise fall back to sync
            if hasattr(self.indexer, 'build_index_async'):
                # Create a simple progress callback for startup
                async def startup_progress_callback(current, total, current_path):
                    if total > 0:
                        progress_pct = int((current / total) * 100)
                        logger.info(f"Index building progress: {progress_pct}% - {current_path}")
                
                success = await self.indexer.build_index_async(progress_callback=startup_progress_callback)
            else:
                # Fall back to synchronous indexing
                success = self.indexer.build_index()
                
            if not success:
                logger.error("Failed to build initial index")
                return False
                
            stats = self.indexer.get_stats()
            logger.info(f"Index ready: {stats['total_folders']} folders, {stats['total_files']} files")
            
            # Create application for webhook mode
            logger.info("Creating Telegram application for webhook mode...")
            
            # For webhook mode, we need to create the application without an updater
            # This bypasses the problematic Updater creation that's causing the error
            from telegram import Bot
            from telegram.ext import Application
            
            # Create bot instance
            bot = Bot(token=self.token)
            
            # Create application without updater (webhook mode)
            self.application = Application.builder().bot(bot).updater(None).build()
            logger.info("Telegram application created successfully for webhook mode")
            
            # Add handlers
            logger.info("Adding command handlers...")
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("menu", self.menu_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("about", self.about_command))
            self.application.add_handler(CommandHandler("privacy", self.privacy_command))
            self.application.add_handler(CommandHandler("feedback", self.feedback_command))
            self.application.add_handler(CommandHandler("admin", self.admin_command))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_feedback_message))
            logger.info("All handlers added successfully")
            
            # Set startup time and cold start detection
            from datetime import datetime, timezone
            self.startup_time = datetime.now(timezone.utc)
            self.is_cold_start = True  # Flag to detect first interaction after startup
            self.pending_updates = []  # Queue for updates received during cold start
            self.cold_start_messages = {}  # Track cold start messages to delete later
            self.cold_start_stats = {  # Analytics for cold start events
                'startup_time': self.startup_time,
                'first_user_contact': None,
                'total_users_contacted': 0,
                'total_updates_queued': 0,
                'startup_duration': None
            }
            
            # Reset cold start flag after initialization period
            asyncio.create_task(self.reset_cold_start_flag())
            
            # Start keep-alive task to prevent Render shutdown during long operations
            self.start_keepalive_task()
            
            logger.info("Application setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up application: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    async def webhook_handler(self, request: Request) -> web.Response:
        """Handle incoming webhook requests from Telegram"""
        try:
            # Check if application is ready
            if not self.application:
                logger.error("Application not initialized")
                return web.Response(text="Application not ready", status=503)

            # Log the request for debugging
            client_ip = getattr(request, 'remote', 'unknown')
            logger.debug(f"Webhook request from {client_ip}")

            data = await request.json()
            
            # Process with cold start detection
            await self.process_webhook_update(data)
                
            return web.Response(text="OK", status=200)
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return web.Response(text="Error", status=500)
    
    async def health_check(self, request: Request) -> web.Response:
        """Health check endpoint for Render with activity tracking"""
        try:
            # Check if bot is properly initialized
            if not self.application or not self.application.bot:
                return web.Response(text="Bot not initialized", status=503)
            
            # Check if indexer is working
            if not self.indexer:
                return web.Response(text="Indexer not available", status=503)
            
            # Calculate time since last activity
            now = datetime.now(timezone.utc)
            time_since_activity = (now - self.last_activity).total_seconds()
            
            # Check indexing status
            indexing_status = "idle"
            indexing_progress = 0
            if hasattr(self.indexer, 'is_indexing') and self.indexer.is_indexing:
                indexing_status = "active"
                if hasattr(self.indexer, 'indexing_progress') and hasattr(self.indexer, 'indexing_total'):
                    if self.indexer.indexing_total > 0:
                        indexing_progress = int((self.indexer.indexing_progress / self.indexer.indexing_total) * 100)
            
            # Return health status
            health_data = {
                "status": "healthy",
                "bot_username": getattr(self.application.bot, 'username', 'unknown'),
                "webhook_url": f"{self.webhook_url}{self.webhook_path}",
                "timestamp": self.startup_time.isoformat() if self.startup_time else None,
                "uptime_seconds": (now - self.startup_time).total_seconds() if self.startup_time else 0,
                "indexing_status": indexing_status,
                "indexing_progress": indexing_progress,
                "last_activity_seconds_ago": time_since_activity,
                "current_path": getattr(self.indexer, 'indexing_current_path', '') if indexing_status == "active" else ""
            }
            
            # Update activity timestamp for this health check
            self.last_activity = now
            
            return web.Response(
                text=f"OneDrive Telegram Bot is running\n{health_data}",
                status=200,
                content_type='text/plain'
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.Response(text=f"Health check failed: {str(e)}", status=503)
    
    async def root_handler(self, request: Request) -> web.Response:
        """Root endpoint handler"""
        return web.Response(
            text="OneDrive Telegram Bot is running! Visit /health for status.",
            status=200,
            content_type='text/plain'
        )
    
    def create_web_app(self):
        """Create aiohttp web application for Render"""
        app = web.Application()
        
        # Add webhook endpoint
        app.router.add_post(self.webhook_path, self.webhook_handler)
        
        # Add health check endpoint (required by Render)
        app.router.add_get('/health', self.health_check)
        
        # Add root endpoint
        app.router.add_get('/', self.root_handler)
        
        # Add CORS headers for web requests
        @web.middleware
        async def cors_handler(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        app.middlewares.append(cors_handler)
        
        return app
    
    async def setup_webhook(self):
        """Set up webhook with Telegram"""
        try:
            if not self.application:
                logger.error("Application not initialized")
                return False
                
            if not self.webhook_url:
                logger.error("Webhook URL not configured")
                return False
                
            # Complete webhook URL
            full_webhook_url = f"{self.webhook_url}{self.webhook_path}"
            
            # Set webhook with Telegram
            await self.application.bot.set_webhook(
                url=full_webhook_url,
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True  # Clear any pending updates
            )
            
            logger.info(f"Webhook set successfully: {full_webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    async def remove_webhook(self):
        """Remove webhook"""
        try:
            if not self.application:
                logger.warning("Application not initialized, cannot remove webhook")
                return True
                
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook removed")
            return True
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            return False
    
    async def run_webhook(self):
        """Run bot with webhook method on Render"""
        runner = None
        try:
            logger.info("Starting OneDrive Telegram Bot on Render...")
            
            # Set up application first
            if not await self.setup_application():
                logger.error("Failed to set up application")
                return
            
            # Initialize and start application
            logger.info("Initializing Telegram application...")
            await self.application.initialize()
            
            logger.info("Starting Telegram application...")
            await self.application.start()
            
            # Send startup notification to admin only
            try:
                logger.info("Sending startup notification to admin...")
                if self.admin_id:
                    # Include cold start statistics in admin message
                    users_count = len(self.cold_start_messages) - 1  # Exclude admin message
                    pending_count = len(self.pending_updates)
                    startup_duration = self.cold_start_stats.get('startup_duration')
                    duration_text = f"{startup_duration.total_seconds():.1f}s" if startup_duration else "calculating..."
                    
                    admin_message = (
                        "🟢 **Bot Started (Render Webhook Mode)**\n\n"
                        f"📊 **Cold Start Analytics:**\n"
                        f"• Users contacted during startup: {users_count}\n"
                        f"• Pending updates queued: {pending_count}\n"
                        f"• Startup duration: {duration_text}\n"
                        f"• Startup completed: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n\n"
                        "✅ Processing queued user requests now..."
                    )
                    
                    sent_message = await self.application.bot.send_message(
                        chat_id=self.admin_id,
                        text=admin_message,
                        parse_mode='Markdown'
                    )
                    # Track admin message for deletion too
                    self.cold_start_messages[f"admin_{self.admin_id}"] = {
                        'message_id': sent_message.message_id,
                        'chat_id': self.admin_id,
                        'timestamp': asyncio.get_event_loop().time()
                    }
            except Exception as e:
                logger.error(f"Error sending startup notification: {e}")
            
            # Process any pending updates from cold start
            await self.process_pending_updates()
            
            # Delete cold start messages now that bot is fully active
            await self.cleanup_cold_start_messages()
            
            # Mark cold start as complete
            self.is_cold_start = False
            
            # Calculate startup duration
            if hasattr(self, 'cold_start_stats'):
                self.cold_start_stats['startup_duration'] = datetime.now(timezone.utc) - self.startup_time
            
            logger.info("Bot fully initialized - cold start complete")
            
            # Set up webhook
            logger.info("Setting up webhook...")
            if not await self.setup_webhook():
                logger.error("Failed to set up webhook")
                return
            
            # Create web application
            logger.info("Creating web application...")
            self.web_app = self.create_web_app()
            
            # Start web server
            logger.info(f"Starting webhook server on {self.host}:{self.port}")
            
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            
            logger.info(f"✅ Webhook server started successfully!")
            logger.info(f"🌐 Webhook URL: {self.webhook_url}{self.webhook_path}")
            logger.info(f"💚 Health check: {self.webhook_url}/health")
            logger.info("🚀 Bot is ready to receive requests!")
            
            # Keep the server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down webhook server...")
            
        except Exception as e:
            logger.error(f"Error running webhook: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Cleanup
            logger.info("Starting cleanup...")
            try:
                if hasattr(self, 'application') and self.application:
                    logger.info("Removing webhook...")
                    await self.remove_webhook()
                    logger.info("Stopping application...")
                    await self.application.stop()
                    logger.info("Shutting down application...")
                    await self.application.shutdown()
                if runner:
                    logger.info("Cleaning up web runner...")
                    await runner.cleanup()
                logger.info("Cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def run(self):
        """Run bot (webhook mode only for Render)"""
        try:
            asyncio.run(self.run_webhook())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise

    async def reset_cold_start_flag(self):
        """Reset cold start flag after initialization period"""
        # More intelligent timeout based on typical Render startup times
        await asyncio.sleep(120)  # Wait 2 minutes (more realistic for Render)
        if self.is_cold_start:
            self.is_cold_start = False
            logger.warning("Cold start detection period ended (timeout reached)")
            
            # Notify any remaining users that startup completed via timeout
            await self.notify_remaining_cold_start_users("timeout")

    async def handle_cold_start_message(self, user_id: int):
        """Send a message to user who triggered a cold start"""
        try:
            # Get user info if possible for personalized message
            try:
                user_info = await self.application.bot.get_chat(user_id)
                user_name = user_info.first_name if user_info.first_name else "there"
            except:
                user_name = "there"
            
            cold_start_message = (
                f"👋 Hi {user_name}!\n\n"
                "🔄 **OneDrive Bot is waking up...**\n\n"
                "The bot was sleeping due to inactivity and is now starting up. "
                "Your request has been received and will be processed automatically once ready.\n\n"
                "⏱️ **Expected startup time:** 10-30 seconds\n"
                "📁 **What this bot does:** Browse and download OneDrive files\n"
                "🎯 **Your request:** Will be processed automatically - no need to resend!\n\n"
                "🔔 This message will disappear once the bot is ready."
            )
            
            # Send the message and store message info for later deletion
            sent_message = await self.application.bot.send_message(
                chat_id=user_id,
                text=cold_start_message,
                parse_mode='Markdown'
            )
            
            # Store message info for deletion later
            self.cold_start_messages[user_id] = {
                'message_id': sent_message.message_id,
                'chat_id': user_id,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Sent enhanced cold start message to user {user_id} ({user_name})")
            
            # Schedule a progress update message after 15 seconds if still in cold start
            asyncio.create_task(self.send_progress_update(user_id, 15))
            
        except Exception as e:
            logger.error(f"Error sending cold start message to user {user_id}: {e}")

    async def send_progress_update(self, user_id: int, delay_seconds: int):
        """Send a progress update if cold start is taking longer than expected"""
        await asyncio.sleep(delay_seconds)
        
        # Only send if still in cold start and user had a cold start message
        if self.is_cold_start and user_id in self.cold_start_messages:
            try:
                progress_message = (
                    "⏳ **Still starting up...**\n\n"
                    "The bot is taking a bit longer than usual to start. "
                    "This sometimes happens when:\n"
                    "• Building the OneDrive file index\n"
                    "• Establishing secure connections\n"
                    "• Loading recent file updates\n\n"
                    "🔄 Almost ready! Your request is still queued."
                )
                
                # Edit the existing cold start message instead of sending a new one
                await self.application.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=self.cold_start_messages[user_id]['message_id'],
                    text=progress_message,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Sent progress update to user {user_id}")
                
            except Exception as e:
                logger.debug(f"Could not send progress update to user {user_id}: {e}")

    async def send_ready_notification(self, user_id: int):
        """Send a brief 'ready' message before processing queued updates"""
        try:
            if user_id in self.cold_start_messages:
                ready_message = (
                    "✅ **Bot is now ready!**\n\n"
                    "Processing your request now..."
                )
                
                # Edit the cold start message one final time
                await self.application.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=self.cold_start_messages[user_id]['message_id'],
                    text=ready_message,
                    parse_mode='Markdown'
                )
                
                # Schedule deletion of this message after 3 seconds
                asyncio.create_task(self.delayed_message_cleanup(user_id, 3))
                
        except Exception as e:
            logger.debug(f"Could not send ready notification to user {user_id}: {e}")

    async def delayed_message_cleanup(self, user_id: int, delay_seconds: int):
        """Delete the cold start message after a delay"""
        await asyncio.sleep(delay_seconds)
        try:
            if user_id in self.cold_start_messages:
                await self.application.bot.delete_message(
                    chat_id=self.cold_start_messages[user_id]['chat_id'],
                    message_id=self.cold_start_messages[user_id]['message_id']
                )
                logger.debug(f"Deleted cold start message for user {user_id}")
        except Exception as e:
            logger.debug(f"Could not delete cold start message for user {user_id}: {e}")
        
        # Remove from tracking
        self.cold_start_messages.pop(user_id, None)

    async def notify_remaining_cold_start_users(self, reason: str):
        """Notify users who are still waiting about startup completion"""
        for user_id in list(self.cold_start_messages.keys()):
            try:
                if reason == "timeout":
                    message = (
                        "⚠️ **Startup Complete (Extended)**\n\n"
                        "The bot took longer than expected to start but is now ready. "
                        "Your request will be processed now."
                    )
                else:
                    message = (
                        "✅ **Bot Ready!**\n\n"
                        "Processing your request..."
                    )
                
                await self.application.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=self.cold_start_messages[user_id]['message_id'],
                    text=message,
                    parse_mode='Markdown'
                )
                
                # Schedule cleanup
                asyncio.create_task(self.delayed_message_cleanup(user_id, 2))
                
            except Exception as e:
                logger.debug(f"Could not notify user {user_id} about startup completion: {e}")

    async def process_webhook_update(self, update_data: dict):
        """Process webhook update with cold start detection"""
        try:
            # Check if this is a cold start and someone is trying to interact
            if self.is_cold_start:
                user_id = None
                
                # Extract user ID from different types of updates
                if update_data.get('message'):
                    user_id = update_data['message']['from']['id']
                elif update_data.get('callback_query'):
                    user_id = update_data['callback_query']['from']['id']
                
                if user_id:
                    # Update analytics
                    if self.cold_start_stats['first_user_contact'] is None:
                        self.cold_start_stats['first_user_contact'] = datetime.now(timezone.utc)
                    
                    # Send cold start message immediately if not already sent to this user
                    if user_id not in self.cold_start_messages:
                        await self.handle_cold_start_message(user_id)
                        self.cold_start_stats['total_users_contacted'] += 1
                    
                    # Queue the update for processing after startup
                    self.pending_updates.append(update_data)
                    self.cold_start_stats['total_updates_queued'] += 1
                    logger.info(f"Queued update from user {user_id} during cold start (Total queued: {len(self.pending_updates)})")
                    return
            
            # Process the update normally if not in cold start
            update = Update.de_json(update_data, self.application.bot)
            if update:
                await self.application.process_update(update)
                logger.debug(f"Processed update: {update.update_id}")
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            import traceback
            traceback.print_exc()

    async def process_pending_updates(self):
        """Process all queued updates from cold start period"""
        try:
            if not self.pending_updates:
                return
                
            logger.info(f"Processing {len(self.pending_updates)} pending updates from cold start")
            
            # Send ready notifications to users before processing their requests
            notified_users = set()
            for update_data in self.pending_updates:
                user_id = None
                if update_data.get('message'):
                    user_id = update_data['message']['from']['id']
                elif update_data.get('callback_query'):
                    user_id = update_data['callback_query']['from']['id']
                
                if user_id and user_id not in notified_users:
                    await self.send_ready_notification(user_id)
                    notified_users.add(user_id)
            
            # Small delay to let users see the ready message
            await asyncio.sleep(1)
            
            # Process the queued updates
            for update_data in self.pending_updates:
                try:
                    update = Update.de_json(update_data, self.application.bot)
                    if update:
                        await self.application.process_update(update)
                        logger.debug(f"Processed pending update: {update.update_id}")
                except Exception as e:
                    logger.error(f"Error processing pending update: {e}")
            
            # Clear the pending updates
            self.pending_updates.clear()
            logger.info("Finished processing pending updates")
            
        except Exception as e:
            logger.error(f"Error processing pending updates: {e}")

    async def cleanup_cold_start_messages(self):
        """Delete all cold start messages now that bot is active"""
        try:
            if not self.cold_start_messages:
                return
                
            logger.info(f"Scheduling cleanup for {len(self.cold_start_messages)} cold start messages")
            
            # Use the delayed cleanup for all remaining messages
            for user_id in list(self.cold_start_messages.keys()):
                asyncio.create_task(self.delayed_message_cleanup(user_id, 1))
            
            logger.info("Scheduled cleanup for all cold start messages")
            
        except Exception as e:
            logger.error(f"Error scheduling cleanup of cold start messages: {e}")
    
    async def send_keepalive_ping(self):
        """Send a keep-alive ping to maintain service activity during long operations"""
        try:
            self.last_activity = datetime.now(timezone.utc)
            # This just updates our internal activity tracker
            # The health endpoint will show recent activity
            logger.debug("Keep-alive ping sent")
        except Exception as e:
            logger.warning(f"Error sending keep-alive ping: {e}")

    def start_keepalive_task(self):
        """Start background task to send periodic keep-alive signals during indexing"""
        async def keepalive_loop():
            while self.keepalive_enabled:
                try:
                    # Check if indexing is in progress
                    if hasattr(self.indexer, 'is_indexing') and self.indexer.is_indexing:
                        await self.send_keepalive_ping()
                        # Sleep for 30 seconds during active indexing
                        await asyncio.sleep(30)
                    else:
                        # Sleep for 5 minutes when not indexing
                        await asyncio.sleep(300)
                except Exception as e:
                    logger.warning(f"Error in keep-alive loop: {e}")
                    await asyncio.sleep(60)  # Wait a minute before retrying
        
        # Start the keep-alive task
        asyncio.create_task(keepalive_loop())
        logger.info("Keep-alive task started")
    

# =============================================================================
# CONFIGURATION SECTION - MODIFY THESE FOR YOUR SETUP
# =============================================================================

# OneDrive folder locations to index
ONEDRIVE_FOLDERS = [
    "Sharing",  # Primary folder name to look for
    # Add more folders as needed:
    # "AUST Resources",
    # "Public",
    # "Archive",
]

# Configuration for folder search behavior
FOLDER_CONFIG = {
    "case_sensitive": False,
    "search_subfolders": False,
    "require_all_folders": False,
}

# =============================================================================
# END CONFIGURATION SECTION
# =============================================================================


def main():
    """Main function for Render deployment"""
    logger.info("🚀 Starting OneDrive Telegram Bot for Render deployment")
    
    # Log versions for debugging
    try:
        import telegram
        logger.info(f"Using python-telegram-bot version: {telegram.__version__}")
    except Exception as e:
        logger.warning(f"Could not determine telegram library version: {e}")
    
    # Check required environment variables
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'ADMIN_USER_ID',
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET',
        'AZURE_TENANT_ID',
        'TARGET_USER_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these in your Render service environment variables")
        return 1
    
    try:
        # Create and run bot
        bot = OneDriveBotRender(
            onedrive_folders=ONEDRIVE_FOLDERS,
            folder_config=FOLDER_CONFIG
        )
        
        logger.info("Bot initialized successfully")
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
