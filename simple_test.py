#!/usr/bin/env python3
"""
Simple test to check both authentication methods
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_application_permissions():
    """Test application permissions (current failing method)"""
    print("🧪 Testing Application Permissions...")
    print("=" * 50)
    
    try:
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient
        
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        tenant_id = os.getenv('AZURE_TENANT_ID')
        
        print(f"📋 Client ID: {client_id}")
        print(f"📋 Tenant ID: {tenant_id}")
        
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=['https://graph.microsoft.com/.default']
        )
        
        print("✅ Graph client initialized")
        
        # Test API call that's been failing
        users = await graph_client.users.get()
        print(f"✅ SUCCESS: Found {len(users.value) if users.value else 0} users")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def test_device_code_auth():
    """Test device code authentication (user-friendly alternative)"""
    print("\n🧪 Testing Device Code Authentication...")
    print("=" * 50)
    
    try:
        from azure.identity import DeviceCodeCredential
        from msgraph import GraphServiceClient
        
        client_id = os.getenv('AZURE_CLIENT_ID')
        tenant_id = os.getenv('AZURE_TENANT_ID')
        
        print("💡 This method will ask you to visit a URL and enter a code")
        print("⏳ Initializing device code authentication...")
        
        # Device code credential - more user-friendly
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
        
        print("🔍 Testing user authentication...")
        me = await graph_client.me.get()
        print(f"✅ SUCCESS: Authenticated as {me.display_name}")
        
        print("🔍 Testing OneDrive access...")
        drive = await graph_client.me.drive.get()
        print(f"✅ SUCCESS: OneDrive '{drive.name}' accessible")
        
        print("🔍 Testing file listing...")
        items = await graph_client.me.drive.root.children.get()
        print(f"✅ SUCCESS: Found {len(items.value) if items.value else 0} items in OneDrive")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def main():
    print("🔧 OneDrive Authentication Test")
    print("=" * 60)
    
    # Test 1: Application permissions (current method)
    app_works = await test_application_permissions()
    
    # Test 2: Device code authentication 
    device_works = await test_device_code_auth()
    
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS")
    print("=" * 60)
    
    if app_works:
        print("✅ Application permissions: WORKING")
        print("🚀 Use: python bot.py")
    else:
        print("❌ Application permissions: FAILED")
        print("💡 Reason: Need admin consent or permission setup")
    
    if device_works:
        print("✅ Device code authentication: WORKING") 
        print("🚀 Use: python bot_delegated.py")
    else:
        print("❌ Device code authentication: FAILED")
        print("💡 Reason: May need Azure app configuration")
    
    print("\n🎯 RECOMMENDATION:")
    if device_works:
        print("✅ Use delegated permissions (bot_delegated.py)")
        print("   - Easier setup, no admin consent needed")
        print("   - You'll authenticate via browser once")
    elif app_works:
        print("✅ Use application permissions (bot.py)")
        print("   - More complex but works for organization")
    else:
        print("❌ Both methods failed - check Azure configuration")
        print("📖 See PERMISSIONS_GUIDE_SIMPLE.md for help")

if __name__ == "__main__":
    asyncio.run(main())
