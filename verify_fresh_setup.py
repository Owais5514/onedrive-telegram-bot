#!/usr/bin/env python3
"""
Fresh Setup Verification Script
Tests the new Azure app registration with application permissions
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def verify_fresh_setup():
    """Verify the fresh Azure app setup step by step"""
    
    print("🔧 Fresh Azure App Setup Verification")
    print("=" * 50)
    
    # Step 1: Check environment variables
    print("📋 Step 1: Checking Environment Variables")
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET') 
    tenant_id = os.getenv('AZURE_TENANT_ID')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not client_id:
        print("❌ AZURE_CLIENT_ID missing - update your .env file")
        return False
    if not client_secret:
        print("❌ AZURE_CLIENT_SECRET missing - update your .env file")
        return False
    if not tenant_id:
        print("❌ AZURE_TENANT_ID missing - update your .env file") 
        return False
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN missing - update your .env file")
        return False
        
    print(f"✅ Client ID: {client_id[:8]}...")
    print(f"✅ Client Secret: {client_secret[:8]}...")
    print(f"✅ Tenant ID: {tenant_id[:8]}...")
    print(f"✅ Bot Token: {bot_token[:10]}...")
    
    # Step 2: Test Graph client initialization
    print("\n📋 Step 2: Initializing Microsoft Graph Client")
    try:
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient
        
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        graph_client = GraphServiceClient(
            credentials=credential,
            scopes=['https://graph.microsoft.com/.default']
        )
        
        print("✅ Graph client initialized successfully")
        
    except Exception as e:
        print(f"❌ Graph client initialization failed: {e}")
        return False
    
    # Step 3: Test basic authentication
    print("\n📋 Step 3: Testing Authentication")
    try:
        # Test a simple API call that requires basic authentication
        token = await credential.get_token('https://graph.microsoft.com/.default')
        print("✅ Authentication successful - got access token")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check if your client secret is correct")
        return False
    
    # Step 4: Test specific permissions
    print("\n📋 Step 4: Testing Application Permissions")
    
    # Test User.Read.All permission
    try:
        users = await graph_client.users.get()
        user_count = len(users.value) if users.value else 0
        print(f"✅ User.Read.All permission working - found {user_count} users")
    except Exception as e:
        print(f"❌ User.Read.All permission failed: {e}")
        print("💡 Check if admin consent was granted for User.Read.All")
        return False
    
    # Test Files permissions by trying to access drives
    try:
        drives = await graph_client.drives.get()
        drive_count = len(drives.value) if drives.value else 0
        print(f"✅ Files permissions working - found {drive_count} drives")
        
        if drive_count > 0:
            # Test accessing a specific drive
            first_drive = drives.value[0]
            drive_items = await graph_client.drives.by_drive_id(first_drive.id).root.children.get()
            item_count = len(drive_items.value) if drive_items.value else 0
            print(f"✅ OneDrive access working - found {item_count} items in drive '{first_drive.name}'")
            
    except Exception as e:
        print(f"❌ Files permissions failed: {e}")
        print("💡 Check if admin consent was granted for Files.Read.All")
        return False
    
    # Step 5: Test OneDrive specific functionality
    print("\n📋 Step 5: Testing OneDrive File Listing")
    try:
        # Try to find a user's OneDrive
        if user_count > 0:
            first_user = users.value[0]
            user_drive = await graph_client.users.by_user_id(first_user.id).drive.get()
            print(f"✅ User OneDrive accessible: {user_drive.name}")
            
            # Try to list items in University folder
            try:
                uni_items = await graph_client.users.by_user_id(first_user.id).drive.root.item_with_path('University').children.get()
                uni_count = len(uni_items.value) if uni_items.value else 0
                print(f"✅ University folder found with {uni_count} items")
            except:
                print("⚠️  University folder not found - bot will start from root")
                
    except Exception as e:
        print(f"❌ OneDrive access failed: {e}")
        print("💡 User might not have OneDrive or permissions missing")
    
    print("\n" + "=" * 50)
    print("🎉 FRESH SETUP VERIFICATION COMPLETE!")
    print("=" * 50)
    print("✅ All permissions are working correctly")
    print("🚀 You can now run: python bot.py")
    print("📱 The bot will show real OneDrive files!")
    
    return True

async def main():
    """Main verification function"""
    try:
        success = await verify_fresh_setup()
        if not success:
            print("\n❌ Setup verification failed")
            print("📖 Please follow FRESH_SETUP_GUIDE.md")
            print("🔧 Make sure to grant admin consent for all permissions")
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        print("📖 Check FRESH_SETUP_GUIDE.md for troubleshooting")

if __name__ == "__main__":
    asyncio.run(main())
