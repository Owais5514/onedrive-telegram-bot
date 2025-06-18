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
            
            # Set startup time
            from datetime import datetime, timezone
            self.startup_time = datetime.now(timezone.utc)
            
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
            update = Update.de_json(data, self.application.bot)
            
            if update:
                # Process the update
                await self.application.process_update(update)
                logger.debug(f"Processed update: {update.update_id}")
            else:
                logger.warning("Received invalid update data")
                
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
            
            # Send startup notification
            try:
                logger.info("Sending startup notification...")
                await self.notify_subscribers("🟢 Bot Started (Render Webhook Mode)")
            except Exception as e:
                logger.error(f"Error sending startup notification: {e}")
            
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
