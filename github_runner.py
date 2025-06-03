#!/usr/bin/env python3
"""
Startup script for GitHub Actions with graceful shutdown
"""

import os
import sys
import signal
import time
import asyncio
from datetime import datetime, timedelta

# Import the bot
from bot import OneDriveBot

class GracefulBot:
    def __init__(self, max_runtime_minutes=60):
        self.bot = OneDriveBot()
        self.max_runtime = timedelta(minutes=max_runtime_minutes)
        self.start_time = datetime.now()
        self.shutdown_requested = False
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n📝 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def run_with_timeout(self):
        """Run bot with automatic timeout"""
        print(f"🤖 Starting bot with {self.max_runtime.total_seconds()/60:.1f} minute timeout...")
        print(f"⏰ Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        try:
            # Start the bot in the background
            bot_task = asyncio.create_task(self._run_bot())
            
            # Monitor for timeout or shutdown signal
            while not self.shutdown_requested:
                current_time = datetime.now()
                runtime = current_time - self.start_time
                
                if runtime >= self.max_runtime:
                    print(f"⏰ Maximum runtime ({self.max_runtime.total_seconds()/60:.1f} minutes) reached")
                    break
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
                # Print status update every 10 minutes
                if runtime.total_seconds() % 600 < 30:  # Every 10 minutes
                    remaining = self.max_runtime - runtime
                    print(f"📊 Bot running... {remaining.total_seconds()/60:.1f} minutes remaining")
            
            # Cancel the bot task
            print("🛑 Stopping bot...")
            bot_task.cancel()
            
            try:
                await bot_task
            except asyncio.CancelledError:
                print("✅ Bot stopped successfully")
            
        except Exception as e:
            print(f"❌ Error running bot: {e}")
            return 1
        
        total_runtime = datetime.now() - self.start_time
        print(f"📈 Total runtime: {total_runtime.total_seconds()/60:.1f} minutes")
        return 0
    
    async def _run_bot(self):
        """Run the actual bot"""
        try:
            await self.bot.run()
        except asyncio.CancelledError:
            # Graceful shutdown
            if hasattr(self.bot, 'application') and self.bot.application:
                await self.bot.application.stop()
            raise
        except Exception as e:
            print(f"❌ Bot error: {e}")
            raise

def main():
    """Main entry point for GitHub Actions"""
    # Get runtime from environment or default to 60 minutes
    max_runtime = int(os.getenv('BOT_RUNTIME_MINUTES', '60'))
    
    print("🚀 OneDrive Telegram Bot - GitHub Actions Runner")
    print(f"📊 Configuration:")
    print(f"   Max Runtime: {max_runtime} minutes")
    print(f"   Python: {sys.version}")
    print(f"   Working Directory: {os.getcwd()}")
    print()
    
    # Create and run the bot
    graceful_bot = GracefulBot(max_runtime_minutes=max_runtime)
    
    try:
        exit_code = asyncio.run(graceful_bot.run_with_timeout())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
