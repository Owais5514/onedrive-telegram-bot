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
        
        logger.info(f"Render Bot initialized - Port: {self.port}")
        logger.info(f"Webhook URL: {self.webhook_url}{self.webhook_path}")
    
    def setup_application(self):
        """Set up the Telegram application (separate from parent's setup_bot method)"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            return False
            
        try:
            # Initialize indexer first
            logger.info("Building OneDrive file index...")
            if not self.indexer.build_index():
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
            
            # Reset cold start flag after initialization period
            asyncio.create_task(self.reset_cold_start_flag())
            
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
        """Health check endpoint for Render"""
        try:
            # Check if bot is properly initialized
            if not self.application or not self.application.bot:
                return web.Response(text="Bot not initialized", status=503)
            
            # Check if indexer is working
            if not self.indexer:
                return web.Response(text="Indexer not available", status=503)
            
            # Return health status
            health_data = {
                "status": "healthy",
                "bot_username": getattr(self.application.bot, 'username', 'unknown'),
                "webhook_url": f"{self.webhook_url}{self.webhook_path}",
                "timestamp": self.startup_time.isoformat() if self.startup_time else None
            }
            
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
            if not self.setup_application():
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
                    await self.application.bot.send_message(
                        chat_id=self.admin_id,
                        text="🟢 Bot Started (Render Webhook Mode)"
                    )
            except Exception as e:
                logger.error(f"Error sending startup notification: {e}")
            
            # Process any pending updates from cold start
            await self.process_pending_updates()
            
            # Delete cold start messages now that bot is fully active
            await self.cleanup_cold_start_messages()
            
            # Mark cold start as complete
            self.is_cold_start = False
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
        await asyncio.sleep(300)  # Wait 5 minutes
        if self.is_cold_start:
            self.is_cold_start = False
            logger.info("Cold start detection period ended")

    async def handle_cold_start_message(self, user_id: int):
        """Send a message to user who triggered a cold start"""
        try:
            cold_start_message = (
                "🔄 Bot is starting up...\n\n"
                "The bot was sleeping due to inactivity and is now warming up. "
                "Please wait a moment and try your request again.\n\n"
                "⏱️ This usually takes 10-30 seconds."
            )
            
            # Send the message and store message info for later deletion
            sent_message = await self.application.bot.send_message(
                chat_id=user_id,
                text=cold_start_message
            )
            
            # Store message info for deletion later
            self.cold_start_messages[user_id] = {
                'message_id': sent_message.message_id,
                'chat_id': user_id
            }
            
            logger.info(f"Sent cold start message to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending cold start message to user {user_id}: {e}")

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
                    # Send cold start message immediately if not already sent to this user
                    if user_id not in self.cold_start_messages:
                        await self.handle_cold_start_message(user_id)
                    
                    # Queue the update for processing after startup
                    self.pending_updates.append(update_data)
                    logger.info(f"Queued update from user {user_id} during cold start")
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
                
            logger.info(f"Deleting {len(self.cold_start_messages)} cold start messages")
            
            for user_id, message_info in self.cold_start_messages.items():
                try:
                    await self.application.bot.delete_message(
                        chat_id=message_info['chat_id'],
                        message_id=message_info['message_id']
                    )
                    logger.debug(f"Deleted cold start message for user {user_id}")
                except Exception as e:
                    logger.warning(f"Could not delete cold start message for user {user_id}: {e}")
            
            # Clear the cold start messages tracking
            self.cold_start_messages.clear()
            logger.info("Finished cleaning up cold start messages")
            
        except Exception as e:
            logger.error(f"Error cleaning up cold start messages: {e}")
    

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
