#!/usr/bin/env python3
"""
Quick diagnostic script to help choose the best authentication approach
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if environment variables are properly set"""
    print("🔍 Checking environment setup...")
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4)}{value[-4:]}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All environment variables are set")
    return True

async def test_application_permissions():
    """Test the current application permissions approach"""
    print("\n🧪 Testing Application Permissions (Current Method)...")
    
    try:
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient
        
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        tenant_id = os.getenv('AZURE_TENANT_ID')
        
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=['https://graph.microsoft.com/.default']
        )
        
        # Test API call
        users = await graph_client.users.get()
        print("✅ Application permissions working!")
        print(f"📊 Found {len(users.value) if users.value else 0} users in organization")
        return True
        
    except Exception as e:
        print(f"❌ Application permissions failed: {e}")
        return False

async def test_delegated_permissions():
    """Test delegated permissions approach"""
    print("\n🧪 Testing Delegated Permissions (Alternative Method)...")
    
    try:
        from azure.identity import DeviceCodeCredential
        from msgraph import GraphServiceClient
        
        client_id = os.getenv('AZURE_CLIENT_ID')
        tenant_id = os.getenv('AZURE_TENANT_ID')
        
        # This will prompt user to authenticate
        credential = DeviceCodeCredential(
            client_id=client_id,
            tenant_id=tenant_id
        )
        
        scopes = [
            'https://graph.microsoft.com/Files.Read',
            'https://graph.microsoft.com/User.Read'
        ]
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=scopes
        )
        
        # Test API call
        me = await graph_client.me.get()
        print(f"✅ Delegated permissions working!")
        print(f"👤 Authenticated as: {me.display_name} ({me.user_principal_name})")
        
        # Test OneDrive access
        drive = await graph_client.me.drive.get()
        print(f"📁 OneDrive accessible: {drive.name}")
        return True
        
    except Exception as e:
        print(f"❌ Delegated permissions failed: {e}")
        return False

async def main():
    """Run diagnostic tests"""
    print("🔧 OneDrive Telegram Bot - Authentication Diagnostic")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        print("\n❌ Please fix environment variables first")
        return
    
    # Test both approaches
    app_permissions_work = await test_application_permissions()
    delegated_permissions_work = await test_delegated_permissions()
    
    print("\n" + "=" * 60)
    print("📋 RESULTS & RECOMMENDATIONS")
    print("=" * 60)
    
    if app_permissions_work:
        print("✅ Application permissions are working!")
        print("💡 Recommendation: Use the original bot.py")
        print("🚀 Command: python bot.py")
        
    elif delegated_permissions_work:
        print("✅ Delegated permissions are working!")
        print("💡 Recommendation: Use the new bot_delegated.py")
        print("🚀 Command: python bot_delegated.py")
        print("⚠️  Note: You'll need to authenticate via browser each time")
        
    else:
        print("❌ Both authentication methods failed")
        print("🔧 Next steps:")
        print("   1. Check Azure app registration permissions")
        print("   2. Verify admin consent is granted")
        print("   3. Review PERMISSIONS_GUIDE_SIMPLE.md")
        print("   4. Contact your IT administrator if needed")
    
    print("\n📖 For detailed setup instructions:")
    print("   - PERMISSIONS_GUIDE_SIMPLE.md (quick fix)")
    print("   - PERMISSIONS_GUIDE.md (detailed guide)")

if __name__ == "__main__":
    asyncio.run(main())
