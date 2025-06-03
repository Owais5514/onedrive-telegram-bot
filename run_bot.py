#!/usr/bin/env python3
"""
OneDrive Telegram Bot with Model Server
Manages both the AI model server and the Telegram bot
"""

import sys
import os
import signal
import logging
import time
import subprocess
import threading
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.model_server_process = None
        self.bot_process = None
        self.shutdown_requested = False
        
    def wait_for_server(self, url: str, timeout: int = 60) -> bool:
        """Wait for the model server to be ready"""
        logger.info(f"⏳ Waiting for model server at {url}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('model_loaded', False):
                        logger.info("✅ Model server is ready!")
                        return True
                    else:
                        logger.info("🔄 Model server is loading...")
                        
            except Exception:
                pass
            
            time.sleep(2)
        
        logger.error("❌ Model server failed to start within timeout")
        return False
    
    def start_model_server(self):
        """Start the AI model server"""
        logger.info("🚀 Starting AI model server...")
        
        try:
            self.model_server_process = subprocess.Popen([
                sys.executable, "model_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"📍 Model server started with PID: {self.model_server_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start model server: {e}")
            return False
    
    def start_bot(self):
        """Start the Telegram bot"""
        logger.info("🤖 Starting Telegram bot...")
        
        try:
            from bot import OneDriveBot
            
            bot = OneDriveBot()
            bot.run()
            
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📥 Received signal {signum}, shutting down...")
        self.shutdown_requested = True
        self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of all services"""
        logger.info("🛑 Shutting down services...")
        
        # Terminate model server
        if self.model_server_process:
            try:
                logger.info("🔄 Stopping model server...")
                self.model_server_process.terminate()
                self.model_server_process.wait(timeout=10)
                logger.info("✅ Model server stopped")
            except Exception as e:
                logger.error(f"Error stopping model server: {e}")
                try:
                    self.model_server_process.kill()
                except:
                    pass
        
        logger.info("🔄 Services shut down successfully")
    
    def run(self):
        """Main execution method"""
        # Check if .env file exists
        if not os.path.exists('.env'):
            print("❌ Error: .env file not found!")
            print("📋 Please copy .env.example to .env and fill in your credentials.")
            return 1
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Start model server
            if not self.start_model_server():
                return 1
            
            # Wait for model server to be ready
            if not self.wait_for_server("http://localhost:8001"):
                self.shutdown()
                return 1
            
            # Start the bot
            logger.info("🚀 All services ready, starting bot...")
            self.start_bot()
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        finally:
            self.shutdown()
        
        return 0

def main():
    """Entry point"""
    manager = BotManager()
    return manager.run()

if __name__ == "__main__":
    sys.exit(main())
