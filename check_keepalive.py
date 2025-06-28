#!/usr/bin/env python3
"""
Keep-Alive Configuration Checker
Verifies that the keep-alive system is properly configured for Render deployment
"""

import os
import sys
import json
import requests
from datetime import datetime
from urllib.parse import urlparse

def check_environment_variables():
    """Check required environment variables"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token from @BotFather',
        'ADMIN_USER_ID': 'Your Telegram user ID (from @userinfobot)',
        'AZURE_CLIENT_ID': 'Azure app registration client ID',
        'AZURE_CLIENT_SECRET': 'Azure app registration client secret',
        'AZURE_TENANT_ID': 'Azure tenant ID',
        'TARGET_USER_ID': 'Target OneDrive user ID'
    }
    
    optional_vars = {
        'WEBHOOK_URL': 'Your Render service URL (for self-ping)',
        'DATABASE_URL': 'PostgreSQL database URL (for persistent storage)',
        'UPTIME_MONITOR_URL': 'External uptime monitor URL (optional)',
        'PORT': 'Service port (Render sets this automatically)',
        'DEBUG': 'Enable debug logging (optional)'
    }
    
    missing_required = []
    found_optional = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'TOKEN' in var or 'SECRET' in var:
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: Not set - {description}")
            missing_required.append(var)
    
    print(f"\n📋 Optional Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            if 'URL' in var and len(value) > 50:
                display_value = f"{value[:30]}...{value[-10:]}"
            elif 'DATABASE_URL' in var:
                display_value = f"{value[:20]}..." if len(value) > 20 else value
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
            found_optional.append(var)
        else:
            print(f"  ⚠️  {var}: Not set - {description}")
    
    return len(missing_required) == 0, missing_required, found_optional

def check_webhook_url():
    """Validate webhook URL format"""
    print(f"\n🌐 Checking Webhook URL...")
    
    webhook_url = os.getenv('WEBHOOK_URL') or os.getenv('RENDER_EXTERNAL_URL')
    
    if not webhook_url:
        print("  ⚠️  No webhook URL configured")
        print("     Set WEBHOOK_URL environment variable to your Render service URL")
        print("     Example: https://your-service-name.onrender.com")
        return False, None
    
    try:
        parsed = urlparse(webhook_url)
        if not parsed.scheme or not parsed.netloc:
            print(f"  ❌ Invalid URL format: {webhook_url}")
            return False, webhook_url
        
        if parsed.scheme not in ['http', 'https']:
            print(f"  ❌ URL must be HTTP or HTTPS: {webhook_url}")
            return False, webhook_url
        
        print(f"  ✅ Webhook URL: {webhook_url}")
        return True, webhook_url
        
    except Exception as e:
        print(f"  ❌ Error parsing webhook URL: {e}")
        return False, webhook_url

def test_health_endpoints(webhook_url):
    """Test health and ping endpoints"""
    print(f"\n🏥 Testing Health Endpoints...")
    
    if not webhook_url:
        print("  ⚠️  Cannot test endpoints - no webhook URL configured")
        return False
    
    endpoints = {
        '/health': 'Health check endpoint',
        '/ping': 'Simple ping endpoint',
        '/metrics': 'Metrics endpoint'
    }
    
    success_count = 0
    
    for endpoint, description in endpoints.items():
        try:
            url = f"{webhook_url.rstrip('/')}{endpoint}"
            print(f"  🔍 Testing {endpoint}...")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"    ✅ {description}: OK")
                
                # Show sample response for health endpoint
                if endpoint == '/health' and len(response.text) < 200:
                    print(f"    📄 Response: {response.text[:100]}...")
                elif endpoint == '/ping':
                    print(f"    📄 Response: {response.text}")
                    
                success_count += 1
            else:
                print(f"    ❌ {description}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"    ⏰ {description}: Timeout (service may be sleeping)")
        except requests.exceptions.ConnectionError:
            print(f"    🔌 {description}: Connection failed (check URL)")
        except Exception as e:
            print(f"    ❌ {description}: Error - {e}")
    
    return success_count > 0

def check_github_actions():
    """Check if GitHub Actions workflow file exists"""
    print(f"\n⚙️  Checking GitHub Actions Configuration...")
    
    workflow_file = '.github/workflows/uptime-monitor.yml'
    
    if os.path.exists(workflow_file):
        print(f"  ✅ Uptime monitor workflow found: {workflow_file}")
        
        try:
            with open(workflow_file, 'r') as f:
                content = f.read()
                
            if 'cron:' in content and '*/10 * * * *' in content:
                print(f"  ✅ Scheduled to run every 10 minutes")
            else:
                print(f"  ⚠️  Schedule not found or incorrect")
                
            if 'uptime_monitor.py' in content:
                print(f"  ✅ References uptime monitor script")
            else:
                print(f"  ⚠️  Uptime monitor script not referenced")
                
        except Exception as e:
            print(f"  ❌ Error reading workflow file: {e}")
            
        return True
    else:
        print(f"  ❌ GitHub Actions workflow not found")
        print(f"     Create {workflow_file} to enable automatic uptime monitoring")
        return False

def check_uptime_monitor_script():
    """Check if uptime monitor script exists"""
    print(f"\n📊 Checking Uptime Monitor Script...")
    
    script_file = 'uptime_monitor.py'
    
    if os.path.exists(script_file):
        print(f"  ✅ Uptime monitor script found: {script_file}")
        
        try:
            with open(script_file, 'r') as f:
                content = f.read()
                
            if 'def ping_service' in content:
                print(f"  ✅ Contains ping_service function")
            if 'requests.get' in content:
                print(f"  ✅ Uses requests library for HTTP")
            if 'WEBHOOK_URL' in content:
                print(f"  ✅ Supports WEBHOOK_URL environment variable")
                
        except Exception as e:
            print(f"  ❌ Error reading script: {e}")
            
        return True
    else:
        print(f"  ❌ Uptime monitor script not found")
        print(f"     Create {script_file} for standalone monitoring")
        return False

def generate_recommendations(webhook_url_valid, endpoints_working, github_actions_exists, monitor_script_exists):
    """Generate recommendations based on check results"""
    print(f"\n📋 Recommendations:")
    
    if not webhook_url_valid:
        print(f"  🔧 Set WEBHOOK_URL environment variable to your Render service URL")
        print(f"     Example: WEBHOOK_URL=https://your-service-name.onrender.com")
    
    if webhook_url_valid and not endpoints_working:
        print(f"  🚀 Deploy your bot to Render first, then re-run this check")
        print(f"  🔄 If bot is deployed but endpoints fail, check Render logs for errors")
    
    if not github_actions_exists:
        print(f"  ⚙️  Enable GitHub Actions uptime monitoring:")
        print(f"     1. Ensure .github/workflows/uptime-monitor.yml exists")
        print(f"     2. Add WEBHOOK_URL to repository secrets")
        print(f"     3. Enable Actions in repository settings")
    
    if not monitor_script_exists:
        print(f"  📊 Add uptime_monitor.py for manual/external monitoring")
    
    if webhook_url_valid and endpoints_working:
        print(f"  🎉 Configuration looks good!")
        print(f"  💡 Monitor GitHub Actions tab to ensure uptime monitoring runs")
        print(f"  📈 Check /metrics endpoint for detailed monitoring data")

def main():
    """Main configuration check function"""
    print("🤖 OneDrive Telegram Bot - Keep-Alive Configuration Check")
    print("=" * 60)
    print(f"⏰ Check time: {datetime.utcnow().isoformat()} UTC\n")
    
    # Run all checks
    env_vars_ok, missing_vars, optional_vars = check_environment_variables()
    webhook_url_valid, webhook_url = check_webhook_url()
    endpoints_working = test_health_endpoints(webhook_url) if webhook_url_valid else False
    github_actions_exists = check_github_actions()
    monitor_script_exists = check_uptime_monitor_script()
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  Environment Variables: {'✅ OK' if env_vars_ok else '❌ Missing required vars'}")
    print(f"  Webhook URL: {'✅ Valid' if webhook_url_valid else '❌ Invalid/Missing'}")
    print(f"  Health Endpoints: {'✅ Working' if endpoints_working else '❌ Not responding'}")
    print(f"  GitHub Actions: {'✅ Configured' if github_actions_exists else '❌ Missing'}")
    print(f"  Monitor Script: {'✅ Available' if monitor_script_exists else '❌ Missing'}")
    
    # Generate recommendations
    generate_recommendations(webhook_url_valid, endpoints_working, github_actions_exists, monitor_script_exists)
    
    # Overall status
    overall_score = sum([env_vars_ok, webhook_url_valid, endpoints_working, github_actions_exists])
    
    print(f"\n🎯 Overall Status:")
    if overall_score >= 3:
        print(f"  🟢 GOOD - Keep-alive system should work well ({overall_score}/4)")
    elif overall_score >= 2:
        print(f"  🟡 FAIR - Some improvements needed ({overall_score}/4)")
    else:
        print(f"  🔴 NEEDS WORK - Multiple issues to resolve ({overall_score}/4)")
    
    print(f"\n💡 For detailed setup instructions, see:")
    print(f"   📖 docs/deployment/KEEP_ALIVE_SYSTEM.md")
    print(f"   🚀 docs/deployment/RENDER_DEPLOYMENT.md")
    
    return overall_score >= 2

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n🛑 Check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Check failed: {e}")
        sys.exit(1)
