#!/usr/bin/env python3
"""
External Uptime Monitor for OneDrive Telegram Bot
This script can be used with external cron services or uptime monitors
to keep the Render service alive by pinging it regularly.

Usage:
- Deploy this on a different service (like GitHub Actions, Heroku scheduler, etc.)
- Set up a cron job to run this every 10 minutes
- Set WEBHOOK_URL environment variable to your Render service URL
"""

import os
import sys
import requests
import time
from datetime import datetime
from typing import Optional

def ping_service(base_url: str, timeout: int = 10) -> dict:
    """Ping the service health endpoint and return status"""
    result = {
        'timestamp': datetime.utcnow().isoformat(),
        'base_url': base_url,
        'success': False,
        'status_code': None,
        'response_time': None,
        'error': None
    }
    
    try:
        start_time = time.time()
        
        # Try health endpoint first
        health_url = f"{base_url}/health"
        response = requests.get(health_url, timeout=timeout)
        
        end_time = time.time()
        result['response_time'] = round((end_time - start_time) * 1000, 2)  # ms
        result['status_code'] = response.status_code
        
        if response.status_code == 200:
            result['success'] = True
            print(f"✅ Health check successful: {health_url}")
            print(f"   Response time: {result['response_time']}ms")
            
            # Also ping the simple ping endpoint for extra activity
            try:
                ping_url = f"{base_url}/ping"
                ping_response = requests.get(ping_url, timeout=5)
                if ping_response.status_code == 200:
                    print(f"✅ Ping successful: {ping_url}")
                else:
                    print(f"⚠️  Ping returned {ping_response.status_code}: {ping_url}")
            except Exception as ping_error:
                print(f"⚠️  Ping failed: {ping_error}")
                
        else:
            result['error'] = f"HTTP {response.status_code}"
            print(f"❌ Health check failed: {health_url}")
            print(f"   Status code: {response.status_code}")
            print(f"   Response time: {result['response_time']}ms")
            
    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
        print(f"⏰ Health check timeout: {base_url}")
        
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error"
        print(f"🔌 Connection failed: {base_url}")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ Unexpected error: {e}")
    
    return result

def ping_multiple_endpoints(base_url: str) -> bool:
    """Ping multiple endpoints to ensure service stays active"""
    endpoints = ['/health', '/ping', '/']
    success_count = 0
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                success_count += 1
                print(f"✅ {endpoint}: OK")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    return success_count > 0

def main():
    """Main uptime monitoring function"""
    print("🤖 OneDrive Telegram Bot - Uptime Monitor")
    print("=" * 50)
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()} UTC")
    
    # Get service URL from environment
    webhook_url = os.getenv('WEBHOOK_URL')
    service_url = os.getenv('SERVICE_URL')  # Alternative env var name
    render_url = os.getenv('RENDER_EXTERNAL_URL')  # Render-specific
    
    # Try multiple environment variable names
    base_url = webhook_url or service_url or render_url
    
    if not base_url:
        print("❌ Error: No service URL found!")
        print("   Set one of these environment variables:")
        print("   - WEBHOOK_URL")
        print("   - SERVICE_URL") 
        print("   - RENDER_EXTERNAL_URL")
        print("\n   Example: WEBHOOK_URL=https://your-service.onrender.com")
        return 1
    
    # Remove trailing slash if present
    base_url = base_url.rstrip('/')
    
    print(f"🎯 Target service: {base_url}")
    print()
    
    # Ping the service
    result = ping_service(base_url)
    
    # Also try multiple endpoints for better coverage
    print("\n📡 Pinging multiple endpoints...")
    multiple_success = ping_multiple_endpoints(base_url)
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Primary health check: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"   Multiple endpoints: {'✅ At least one succeeded' if multiple_success else '❌ All failed'}")
    
    if result['response_time']:
        print(f"   Response time: {result['response_time']}ms")
    
    # Return appropriate exit code
    if result['success'] or multiple_success:
        print(f"\n🎉 Service is alive and responding!")
        return 0
    else:
        print(f"\n💀 Service appears to be down or unresponsive!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Monitor crashed: {e}")
        sys.exit(1)
