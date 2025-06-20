#!/usr/bin/env python3
"""
OneDrive Telegram Bot - Webhook Implementation
Alternative to polling method using webhooks for better performance
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bot import OneDriveBot
import ssl
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class OneDriveBotWebhook(OneDriveBot):
    """Extended OneDriveBot with webhook support"""
    
    def __init__(self, onedrive_folders=None, folder_config=None):
        super().__init__(onedrive_folders, folder_config)
        
        # Webhook configuration
        self.webhook_url = os.getenv('WEBHOOK_URL')  # e.g., https://yourdomain.com/webhook
        self.webhook_path = os.getenv('WEBHOOK_PATH', '/webhook')
        self.webhook_port = int(os.getenv('WEBHOOK_PORT', '8443'))
        self.webhook_host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        
        # SSL configuration for webhooks (required by Telegram)
        self.cert_file = os.getenv('SSL_CERT_FILE')  # Path to SSL certificate
        self.key_file = os.getenv('SSL_KEY_FILE')    # Path to SSL private key
        
        self.web_app = None
        
    async def webhook_handler(self, request: Request) -> Response:
        """Handle incoming webhook requests from Telegram"""
        try:
            data = await request.json()
            update = Update.de_json(data, self.application.bot)
            
            if update:
                # Process the update
                await self.application.process_update(update)
                
            return Response(text="OK")
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return Response(text="Error", status=500)
    
    async def setup_webhook(self):
        """Set up webhook with Telegram"""
        try:
            if not self.webhook_url:
                logger.error("WEBHOOK_URL not configured in environment variables")
                return False
                
            # Set webhook
            webhook_url = f"{self.webhook_url}{self.webhook_path}"
            
            if self.cert_file and os.path.exists(self.cert_file):
                # Use self-signed certificate
                with open(self.cert_file, 'rb') as cert:
                    await self.application.bot.set_webhook(
                        url=webhook_url,
                        certificate=cert,
                        allowed_updates=['message', 'callback_query']
                    )
            else:
                # Use domain with valid SSL certificate
                await self.application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=['message', 'callback_query']
                )
            
            logger.info(f"Webhook set to: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False
    
    async def remove_webhook(self):
        """Remove webhook (useful for switching back to polling)"""
        try:
            await self.application.bot.delete_webhook()
            logger.info("Webhook removed")
            return True
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            return False
    
    def create_web_app(self):
        """Create aiohttp web application for webhook"""
        app = web.Application()
        app.router.add_post(self.webhook_path, self.webhook_handler)
        
        # Health check endpoint
        async def health_check(request):
            return Response(text="Bot is running")
        
        app.router.add_get('/health', health_check)
        return app
    
    async def run_webhook(self):
        """Run bot with webhook method"""
        try:
            # Initialize application
            await self.application.initialize()
            
            # Start application
            await self.application.start()
            
            # Send startup notification
            async def post_init():
                try:
                    await self.notify_subscribers("🟢 Bot Started (Webhook Mode)")
                except Exception as e:
                    logger.error(f"Error sending startup notification: {e}")
            
            await post_init()
            
            # Set up webhook
            webhook_set = await self.setup_webhook()
            if not webhook_set:
                logger.error("Failed to set up webhook")
                return
            
            # Create web application
            self.web_app = self.create_web_app()
            
            # Set up SSL context if certificates are provided
            ssl_context = None
            if self.cert_file and self.key_file:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(self.cert_file, self.key_file)
            
            # Run web server
            logger.info(f"Starting webhook server on {self.webhook_host}:{self.webhook_port}")
            
            runner = web.AppRunner(self.web_app)
            await runner.setup()
            
            site = web.TCPSite(
                runner, 
                self.webhook_host, 
                self.webhook_port,
                ssl_context=ssl_context
            )
            
            await site.start()
            
            logger.info(f"Webhook server started successfully")
            logger.info(f"Webhook URL: {self.webhook_url}{self.webhook_path}")
            
            # Keep the server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down webhook server...")
            
        except Exception as e:
            logger.error(f"Error running webhook: {e}")
        finally:
            # Cleanup
            try:
                await self.remove_webhook()
                await self.application.stop()
                await self.application.shutdown()
                if self.web_app:
                    await self.web_app.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def run(self, method='polling'):
        """Run bot with specified method"""
        if method.lower() == 'webhook':
            asyncio.run(self.run_webhook())
        else:
            # Use original polling method
            super().run()


if __name__ == "__main__":
    import sys
    
    # Allow method selection via command line
    method = 'polling'  # default
    if len(sys.argv) > 1:
        method = sys.argv[1].lower()
    
    if method not in ['polling', 'webhook']:
        print("Usage: python bot_webhook.py [polling|webhook]")
        sys.exit(1)
    
    bot = OneDriveBotWebhook()
    print(f"Starting bot with {method} method...")
    bot.run(method)
