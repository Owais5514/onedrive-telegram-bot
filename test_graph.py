#!/usr/bin/env python3
"""
Test Microsoft Graph connection for OneDrive access
"""

import asyncio
import os
from dotenv import load_dotenv
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential

async def test_graph_connection():
    """Test if we can connect to Microsoft Graph and access OneDrive"""
    
    print("🔍 Testing Microsoft Graph Connection...")
    
    # Load environment variables
    load_dotenv()
    
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    tenant_id = os.getenv('TENANT_ID')
    
    try:
        # Initialize credentials
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Initialize Graph client
        scopes = ['https://graph.microsoft.com/.default']
        graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        
        print("✅ Graph client initialized successfully")
        
        # Test basic Graph API access
        test_user = None
        try:
            # For application permissions, we can't use /me endpoint
            # Instead, let's test by trying to access a user's drive
            # First, let's get users to find one to test with
            users = await graph_client.users.get()
            if users and users.value and len(users.value) > 0:
                test_user = users.value[0]
                print(f"✅ Successfully authenticated with application permissions")
                print(f"   Found {len(users.value)} users in the organization")
                print(f"   Test user: {test_user.display_name or test_user.user_principal_name}")
                
                # Test accessing that user's drive
                try:
                    user_drive = await graph_client.users.by_user_id(test_user.id).drive.get()
                    if user_drive:
                        print(f"✅ OneDrive access successful for user")
                        print(f"   Drive name: {user_drive.name or 'OneDrive'}")
                        print(f"   Drive type: {user_drive.drive_type or 'business'}")
                    else:
                        print("❌ Could not access user's OneDrive")
                        return False
                except Exception as e:
                    print(f"❌ Failed to access user's OneDrive: {e}")
                    print("💡 Check if your app has Files.Read.All permissions")
                    return False
            else:
                print("❌ Could not retrieve users from organization")
                print("💡 Check if your app has User.Read.All permissions")
                return False
        except Exception as e:
            print(f"❌ Failed to access organization users: {e}")
            print("💡 Check if your app has proper permissions and admin consent")
            return False
        
        # Test OneDrive access - removed since we tested it above
        
        # Test listing root files for the test user
        try:
            if test_user:
                root_items = await graph_client.users.by_user_id(test_user.id).drive.root.children.get()
                if root_items and root_items.value:
                    print(f"✅ Successfully listed {len(root_items.value)} items in user's OneDrive root")
                    print("   Sample items:")
                    for item in root_items.value[:3]:  # Show first 3 items
                        item_type = "📁" if item.folder else "📄"
                        print(f"   {item_type} {item.name}")
                    if len(root_items.value) > 3:
                        print(f"   ... and {len(root_items.value) - 3} more items")
                else:
                    print("✅ User's OneDrive root is empty or no items found")
        except Exception as e:
            print(f"❌ Failed to list OneDrive items: {e}")
            print("💡 Check if your app has proper OneDrive permissions")
            return False
        
        print("\n🎉 All Microsoft Graph tests passed!")
        print("Your OneDrive integration is ready to use.")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Graph client: {e}")
        print("💡 Check your Azure app credentials in .env file")
        return False

if __name__ == '__main__':
    success = asyncio.run(test_graph_connection())
    if success:
        print("\n🚀 Ready to start the Telegram bot!")
        print("Run: python bot.py")
    else:
        print("\n❌ Please fix the issues above before starting the bot.")
        print("📖 Check QUICKSTART.md for Azure setup instructions.")
